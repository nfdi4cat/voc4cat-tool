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
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from curies import Converter
from jinja2 import Template
from rdflib import RDF, SKOS, Graph

from voc4cat.config import AcceptedSimilarity

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
    whether alternate labels are included. Empty labels are left out: they
    would match each other perfectly and report concepts as duplicates for
    carrying no label, which the parent check already reports as a data
    problem.
    """
    labels: dict[LabelKey, str] = {
        (uri, "pref_label"): concept.pref_label.strip()
        for uri, concept in concepts.items()
        if concept.pref_label.strip()
    }
    if include_alt_labels:
        for uri, concept in concepts.items():
            for position, alt_label in enumerate(concept.alt_labels):
                if alt_label.strip():
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


@dataclass(frozen=True)
class AcceptedPair:
    """An accepted_similarity entry resolved to concept IRIs."""

    iris: frozenset[str]
    concepts: tuple[str, str]
    reason: str


@dataclass(frozen=True)
class AcceptedFinding:
    """A reported pair that the vocabulary maintainers have already reviewed."""

    finding: ConceptSimilarity
    reason: str


@dataclass(frozen=True)
class UnusedAcceptedEntry:
    """An accepted_similarity entry that did not apply to this run."""

    concepts: tuple[str, str]
    reason: str
    status: str


@dataclass(frozen=True)
class PartitionedFindings:
    """Findings split into what needs review and what has been reviewed."""

    reported: list[ConceptSimilarity]
    accepted: list[AcceptedFinding]
    unused: list[UnusedAcceptedEntry]


def resolve_accepted(
    entries: Sequence[AcceptedSimilarity], converter: Converter | None
) -> list[AcceptedPair]:
    """Resolve the configured pairs to concept IRIs.

    An entry may name its concepts as CURIEs or as IRIs; anything the prefix
    map cannot expand is taken to be an IRI already.
    """
    accepted = []
    for item in entries:
        first, second = item.concepts[0], item.concepts[1]
        iris = frozenset(
            {_expand(first, converter), _expand(second, converter)},
        )
        accepted.append(
            AcceptedPair(iris=iris, concepts=(first, second), reason=item.reason)
        )
    return accepted


def _expand(concept: str, converter: Converter | None) -> str:
    if converter is None:
        return concept
    return converter.expand(concept) or concept


def partition_accepted(
    findings: list[ConceptSimilarity],
    accepted: list[AcceptedPair],
    concepts: dict[str, Concept],
    report_unmatched: bool,
) -> PartitionedFindings:
    """Set the reviewed pairs aside and name the entries that did not apply.

    ``report_unmatched`` tells whether an entry that matched no finding is
    worth reporting. It is only meaningful when the whole vocabulary was
    screened: when only additions are screened, most accepted pairs produce
    no finding and saying so would be noise.
    """
    reasons = {item.iris: item.reason for item in accepted}
    reported: list[ConceptSimilarity] = []
    reviewed: list[AcceptedFinding] = []
    matched: set[frozenset[str]] = set()
    for found in findings:
        identity = pair_key(found.concept_id, found.similar_concept_id)
        if identity in reasons:
            matched.add(identity)
            reviewed.append(AcceptedFinding(finding=found, reason=reasons[identity]))
        else:
            reported.append(found)

    unused = []
    for item in accepted:
        unknown = sorted(iri for iri in item.iris if iri not in concepts)
        if unknown:
            status = "unknown concept"
            logger.warning(
                "accepted_similarity entry (%s, %s) names a concept that is not "
                "in the vocabulary: %s",
                *item.concepts,
                ", ".join(unknown),
            )
        elif report_unmatched and item.iris not in matched:
            status = "no matching pair"
            logger.warning(
                "accepted_similarity entry (%s, %s) matched no reported pair.",
                *item.concepts,
            )
        else:
            continue
        unused.append(
            UnusedAcceptedEntry(
                concepts=item.concepts, reason=item.reason, status=status
            )
        )
    return PartitionedFindings(reported=reported, accepted=reviewed, unused=unused)


class Problem(Enum):
    """Enumeration for concept issues."""

    NO_BROADER_CONCEPT = ("W001", "No broader concept")
    MULTIPLE_BROADER_CONCEPTS = ("W002", "Multiple broader concepts")

    def __init__(self, problem_id: str, description: str) -> None:
        self.problem_id = problem_id
        self.description = description


@dataclass(frozen=True)
class ConceptIssue:
    """Class to hold concept issue information."""

    concept_id: str
    concept_label: str
    problem: Problem
    problem_detail: str


@dataclass(frozen=True)
class LinkStyle:
    """Where the concepts of a report link to.

    Without a template a concept links to its own IRI, so that a report is
    useful against a plain vocabulary file with no configuration at all.
    """

    template: str = ""
    id_pattern: re.Pattern[str] | None = None

    def url(self, uri: str) -> str:
        if not self.template or self.id_pattern is None:
            return uri
        match = self.id_pattern.search(uri)
        if match is None:
            # An IRI of another vocabulary; our ID template does not apply.
            return uri
        return Template(self.template).render(entity_id=match.group("identifier"))

    def markdown(self, uri: str, text: str) -> str:
        return f"[{text}]({self.url(uri)})"


def check_parents(
    concepts: dict[str, Concept], link_style: LinkStyle
) -> dict[str, ConceptIssue]:
    """Report concepts that have no or more than one broader concept."""
    logger.info("Checking if concepts have no or more than one broader concept.")
    issues: dict[str, ConceptIssue] = {}
    for uri, concept in concepts.items():
        if not concept.parents:
            issues[uri] = ConceptIssue(
                concept_id=concept.curie,
                concept_label=concept.pref_label,
                problem=Problem.NO_BROADER_CONCEPT,
                problem_detail="",
            )
        elif len(concept.parents) > 1:
            issues[uri] = ConceptIssue(
                concept_id=concept.curie,
                concept_label=concept.pref_label,
                problem=Problem.MULTIPLE_BROADER_CONCEPTS,
                problem_detail=" / ".join(
                    _parent_links(concept.parents, concepts, link_style)
                ),
            )
    return issues


def _parent_links(
    parents: list[str], concepts: dict[str, Concept], link_style: LinkStyle
) -> list[str]:
    """Link each broader concept, naming those of other vocabularies by IRI."""
    return [
        link_style.markdown(parent, concepts[parent].pref_label)
        if parent in concepts
        else parent
        for parent in parents
    ]


@dataclass(frozen=True)
class ComparisonResult:
    """Everything the report is rendered from."""

    method: str
    vocab_new_src: Path
    vocab_base_src: Path | None
    concepts: dict[str, Concept]
    added_count: int
    compare_all: bool
    include_alt_labels: bool
    thresholds: Thresholds
    findings: PartitionedFindings
    issues: dict[str, ConceptIssue]


def label_of(concept: Concept, role: str) -> str:
    """Return the label a finding refers to, marking alternate labels."""
    if role == "pref_label":
        return concept.pref_label
    position = int(role.rsplit("-", maxsplit=1)[-1])
    return f"{concept.alt_labels[position]} (altLabel)"


SIMILARITY_HEADER = (
    "| Concept ID | Concept label | Similar<BR>Concept ID "
    "| Similar Concept label | Similarity Score<BR>Label "
    "| Similarity Score<BR>Definition |"
)
TABLE_RULE = "|---|---|---|---|---|---|"


def render_report(
    result: ComparisonResult,
    link_style: LinkStyle | None = None,
    hide_accepted: bool = False,
) -> str:
    """Render the markdown report of a comparison."""
    style = link_style if link_style is not None else LinkStyle()
    report = [_header(result), _similarity_table(result, style)]
    if result.findings.accepted and not hide_accepted:
        report.append(_accepted_table(result, style))
    if result.findings.unused:
        # Shown even with --hide-accepted: this is a configuration problem,
        # not a decision somebody made on purpose.
        report.append(_unused_table(result))
    report.append(_issue_table(result, style))
    return "".join(report)


def _header(result: ComparisonResult) -> str:
    if result.compare_all:
        head = (
            f"# Similarities for all concepts using method {result.method}\n\n"
            f"Checked {len(result.concepts)} concepts in {result.vocab_new_src} "
            "for similarities.\n\n"
        )
    else:
        head = (
            f"# Similarities for added concepts using method {result.method}\n\n"
            f"Checked {result.added_count} additions made in {result.vocab_new_src} "
            f"for similarities with concepts in {result.vocab_base_src}.\n\n"
        )
    return head + (
        f"- Similarity threshold labels: {result.thresholds.labels}\n"
        f"- Similarity threshold definitions: {result.thresholds.definitions}\n"
        "- Label similarity reported regardless of the definitions: "
        f"{result.thresholds.labels_certain}\n"
        "- Alternate labels included in check? "
        f"{'Yes' if result.include_alt_labels else 'No'}\n\n"
    )


def _broader_column(
    found: ConceptSimilarity, result: ComparisonResult, style: LinkStyle
) -> str:
    concepts = result.concepts
    own = ", ".join(_parent_links(concepts[found.concept_id].parents, concepts, style))
    if found.have_same_broader_concept:
        return f"Y - {own}"
    other = ", ".join(
        _parent_links(concepts[found.similar_concept_id].parents, concepts, style)
    )
    return f"N - {own} / {other}"


def _similarity_row(
    found: ConceptSimilarity, result: ComparisonResult, style: LinkStyle
) -> str:
    concept = result.concepts[found.concept_id]
    similar = result.concepts[found.similar_concept_id]
    return (
        f"| {style.markdown(concept.uri, concept.curie)} "
        f"| {label_of(concept, found.sentence_key[1])} "
        f"| {style.markdown(similar.uri, similar.curie)} "
        f"| {label_of(similar, found.similar_sentence_key[1])} "
        f"| {found.similarity_score:.4f} "
        f"| {found.definition_similarity_score:.4f} "
    )


def _similarity_table(result: ComparisonResult, style: LinkStyle) -> str:
    if not result.findings.reported:
        return "No similarities found.\n"
    rows = [f"{SIMILARITY_HEADER} Same Broader Concept? |\n", f"{TABLE_RULE}---|\n"]
    rows.extend(
        f"{_similarity_row(found, result, style)}"
        f"| {_broader_column(found, result, style)} |\n"
        for found in result.findings.reported
    )
    return "".join(rows)


def _accepted_table(result: ComparisonResult, style: LinkStyle) -> str:
    rows = [
        "\n\n## Accepted similarities\n\n",
        (
            "Pairs declared in `accepted_similarity` for this vocabulary. "
            "They need no action.\n\n"
        ),
        f"{SIMILARITY_HEADER} Reason |\n",
        f"{TABLE_RULE}---|\n",
    ]
    rows.extend(
        f"{_similarity_row(accepted.finding, result, style)}| {accepted.reason} |\n"
        for accepted in result.findings.accepted
    )
    return "".join(rows)


def _unused_table(result: ComparisonResult) -> str:
    rows = [
        "\n\n## Unused accepted-similarity entries\n\n",
        "These entries of `accepted_similarity` did not apply to this run.\n\n",
        "| Concepts | Reason | Status |\n",
        "|---|---|---|\n",
    ]
    rows.extend(
        f"| {entry.concepts[0]}, {entry.concepts[1]} | {entry.reason} "
        f"| {entry.status} |\n"
        for entry in result.findings.unused
    )
    return "".join(rows)


def _issue_table(result: ComparisonResult, style: LinkStyle) -> str:
    if not result.issues:
        return "\n\n## No additional concept issues found.\n"
    rows = [
        "\n\n## Additional concept check results\n\n",
        (
            "| Concept ID | Concept label | Problem ID | Problem description "
            "| Problem details |\n"
        ),
        "|---|---|---|---|---|\n",
    ]
    rows.extend(
        f"| {style.markdown(uri, issue.concept_id)} | {issue.concept_label} "
        f"| {issue.problem.problem_id} | {issue.problem.description} "
        f"| {issue.problem_detail} |\n"
        for uri, issue in sorted(result.issues.items())
    )
    return "".join(rows)


def write_report(report: str, destination: Path) -> None:
    """Write the report, independent of the locale encoding."""
    destination.write_text(report, encoding="utf-8")
    logger.info("Similarities report written to %s", destination)
