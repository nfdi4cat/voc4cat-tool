"""
Selection and reporting logic of the vocabulary assistant.

This module holds everything that does not need a scoring backend: reading a
vocabulary, deciding which concept pairs are similar enough to report, setting
reviewed pairs aside, and rendering the markdown report. It imports only core
dependencies, so it is available and testable without the optional
``assistant`` extra. The scoring backends and the command line interface live
in :mod:`voc4cat.assistant`.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from curies import Converter
from rdflib import RDF, SKOS, Graph

logger = logging.getLogger(__name__)

# A label of a concept, identified by the concept IRI and the role the label
# plays for it: "pref_label", or "altLabel-<n>" for the n-th alternate label.
LabelKey = tuple[str, str]


@dataclass
class Concept:
    """Class to hold concept information."""

    uri: str
    curie: str
    pref_label: str = ""
    alt_labels: list[str] = field(default_factory=list)
    definition: str = ""
    parents: list[str] = field(default_factory=list)


def _curie_for(uri: str, converter: Converter | None) -> str:
    """Return the CURIE of an IRI, falling back to deriving it from the IRI."""
    if converter is not None:
        curie = converter.compress(uri)
        if curie is not None:
            return curie
    # Without a prefix map the last IRI segment is the best available label.
    # voc4cat-style IRIs end in "<prefix>_<id>", which reads as a CURIE.
    return uri.rsplit("/", maxsplit=1)[-1].replace("_", ":")


def load_vocab(
    ttl_file: Path, converter: Converter | None = None
) -> dict[str, Concept]:
    """Return the concepts of a vocabulary file, keyed by concept IRI."""
    vocab_graph = Graph().parse(str(ttl_file), format="turtle")
    concepts: dict[str, Concept] = {}
    for subject in vocab_graph.subjects(RDF.type, SKOS.Concept):
        uri = str(subject)
        concept = Concept(uri=uri, curie=_curie_for(uri, converter))
        for predicate, obj in vocab_graph.predicate_objects(subject):
            if predicate == SKOS.prefLabel:
                concept.pref_label = str(obj)
            elif predicate == SKOS.altLabel:
                concept.alt_labels.append(str(obj))
            elif predicate == SKOS.definition:
                concept.definition = str(obj)
            elif predicate == SKOS.broader:
                concept.parents.append(str(obj))
        # rdflib guarantees no order for predicate_objects, so sort to keep the
        # positional altLabel-<n> keys stable across parses of the same data.
        concept.alt_labels.sort()
        concept.parents.sort()
        concepts[uri] = concept
    # Sorted by IRI so that the index order of the score matrix, and with it
    # every report built from it, does not depend on the order rdflib hands
    # out subjects.
    return {uri: concepts[uri] for uri in sorted(concepts)}


def build_label_sentences(
    concepts: dict[str, Concept], include_alt_labels: bool
) -> dict[LabelKey, str]:
    """Return every label to compare, keyed by concept IRI and label role.

    Preferred labels come first so that the order is stable and independent of
    whether alternate labels are included.
    """
    labels: dict[LabelKey, str] = {
        (uri, "pref_label"): concept.pref_label.strip()
        for uri, concept in concepts.items()
    }
    if include_alt_labels:
        for uri, concept in concepts.items():
            for position, alt_label in enumerate(concept.alt_labels):
                labels[(uri, f"altLabel-{position}")] = alt_label.strip()
    return labels


def keys_of_concepts(
    labels: dict[LabelKey, str], concept_ids: set[str]
) -> set[LabelKey]:
    """Return the label keys belonging to the given concepts.

    Every label of a concept is included, alternate labels among them.
    """
    return {key for key in labels if key[0] in concept_ids}


@dataclass(frozen=True)
class Thresholds:
    """The score thresholds that decide whether a pair is reported."""

    labels: float
    definitions: float
    labels_certain: float

    def __post_init__(self) -> None:
        if self.labels_certain < self.labels:
            msg = (
                f"--threshold-labels-certain ({self.labels_certain}) must not be "
                f"below --threshold-labels ({self.labels}); it would never be "
                "reached."
            )
            raise ValueError(msg)


@dataclass(frozen=True)
class CandidatePair:
    """Two concepts whose labels are similar enough to look at."""

    concept_id: str
    sentence_key: LabelKey
    similar_concept_id: str
    similar_sentence_key: LabelKey
    similarity_score: float


def pair_key(concept_id: str, other_concept_id: str) -> frozenset[str]:
    """Return the order-independent identity of a pair of concepts."""
    return frozenset({concept_id, other_concept_id})


def select_candidates(
    labels: dict[LabelKey, str],
    scores: Sequence[Sequence[float]],
    thresholds: Thresholds,
    keys_to_screen: set[LabelKey] | None = None,
) -> list[CandidatePair]:
    """Return the concept pairs whose labels reach the label threshold.

    Each pair of concepts appears once, represented by its highest-scoring
    combination of labels. ``keys_to_screen`` restricts the search to pairs
    involving one of those labels; passing ``None`` screens the whole
    vocabulary.

    Only the upper triangle of ``scores`` is read, which is the half the
    Levenshtein backend fills.
    """
    keys = list(labels)
    best: dict[frozenset[str], CandidatePair] = {}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            key_i, key_j = keys[i], keys[j]
            if key_i[0] == key_j[0]:
                # A concept's own labels always resemble each other.
                continue
            if keys_to_screen is not None and not (
                key_i in keys_to_screen or key_j in keys_to_screen
            ):
                continue
            score = float(scores[i][j])
            if score < thresholds.labels:
                continue
            first, second = _orient(key_i, key_j, keys_to_screen)
            identity = pair_key(first[0], second[0])
            candidate = CandidatePair(
                concept_id=first[0],
                sentence_key=first,
                similar_concept_id=second[0],
                similar_sentence_key=second,
                similarity_score=score,
            )
            previous = best.get(identity)
            if previous is None or _outranks(candidate, previous):
                best[identity] = candidate
    return list(best.values())


def _orient(
    key_i: LabelKey, key_j: LabelKey, keys_to_screen: set[LabelKey] | None
) -> tuple[LabelKey, LabelKey]:
    """Decide which label of a pair is the subject of the finding.

    When only one of the two is being screened, that one leads: in `compare`
    the finding is about the submitted concept. Otherwise the smaller key
    leads, which keeps the report independent of iteration order.
    """
    if keys_to_screen is not None:
        i_screened, j_screened = key_i in keys_to_screen, key_j in keys_to_screen
        if j_screened and not i_screened:
            return key_j, key_i
        if i_screened and not j_screened:
            return key_i, key_j
    return min(key_i, key_j), max(key_i, key_j)


def _outranks(candidate: CandidatePair, previous: CandidatePair) -> bool:
    """Report the strongest evidence for a pair, ties broken by label key."""
    if candidate.similarity_score != previous.similarity_score:
        return candidate.similarity_score > previous.similarity_score
    return (candidate.sentence_key, candidate.similar_sentence_key) < (
        previous.sentence_key,
        previous.similar_sentence_key,
    )


@dataclass(frozen=True)
class ConceptSimilarity:
    """A pair of concepts reported as similar."""

    concept_id: str
    sentence_key: LabelKey
    similar_concept_id: str
    similar_sentence_key: LabelKey
    similarity_score: float
    definition_similarity_score: float
    have_same_broader_concept: bool


def apply_definition_rule(
    candidates: list[CandidatePair],
    definition_scores: dict[frozenset[str], float],
    thresholds: Thresholds,
    concepts: dict[str, Concept],
) -> list[ConceptSimilarity]:
    """Return the candidates that are worth reporting, strongest first.

    A pair is reported when its labels agree so closely that the definitions
    cannot argue it away, or when labels and definitions both pass their
    threshold. Two concepts carrying the same label are worth reporting
    however differently their definitions are worded.
    """
    reported = []
    for pair in candidates:
        definition_score = definition_scores[
            pair_key(pair.concept_id, pair.similar_concept_id)
        ]
        certain = pair.similarity_score >= thresholds.labels_certain
        if not certain and definition_score < thresholds.definitions:
            continue
        reported.append(
            ConceptSimilarity(
                concept_id=pair.concept_id,
                sentence_key=pair.sentence_key,
                similar_concept_id=pair.similar_concept_id,
                similar_sentence_key=pair.similar_sentence_key,
                similarity_score=pair.similarity_score,
                definition_similarity_score=definition_score,
                have_same_broader_concept=bool(
                    set(concepts[pair.concept_id].parents)
                    & set(concepts[pair.similar_concept_id].parents)
                ),
            )
        )
    reported.sort(
        key=lambda found: (
            -found.similarity_score,
            -found.definition_similarity_score,
            found.concept_id,
            found.similar_concept_id,
        )
    )
    return reported
