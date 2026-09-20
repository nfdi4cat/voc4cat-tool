"""Tests for voc4cat.similarity.

The module holds the selection and reporting logic of voc-assistant and
imports no part of the optional `assistant` extra, so these tests run
wherever the package is installed.
"""

import pytest
from curies import Converter

from voc4cat import similarity

DUPLICATES = "similarity-duplicates.ttl"

CO_PRECIPITATION_1 = "https://example.org/0000001"
CO_PRECIPITATION_2 = "https://example.org/0000002"
COPRECIPITATION = "https://example.org/0000003"
CALCINATION = "https://example.org/0000004"
SYNTHESIS_METHOD = "https://example.org/0000010"
PREPARATION = "https://example.org/0000011"
PROCESSING = "https://example.org/0000012"


@pytest.fixture
def concepts(datadir):
    return similarity.load_vocab(datadir / DUPLICATES)


# === Loading ===


def test_load_vocab_reads_label_definition_and_parents(concepts):
    concept = concepts[CO_PRECIPITATION_1]

    assert concept.uri == CO_PRECIPITATION_1
    assert concept.pref_label == "co-precipitation"
    assert concept.definition.startswith("Precipitation of more than one substance")
    assert concept.parents == [SYNTHESIS_METHOD]


def test_load_vocab_collects_all_alt_labels(concepts):
    assert sorted(concepts[CALCINATION].alt_labels) == [
        "co-precipitation",
        "thermal decomposition",
    ]


def test_load_vocab_collects_every_broader_concept(concepts):
    assert sorted(concepts[PREPARATION].parents) == [SYNTHESIS_METHOD, PROCESSING]


def test_load_vocab_derives_curie_without_a_converter(concepts):
    """Without configuration the CURIE is derived from the IRI itself."""
    assert concepts[CO_PRECIPITATION_1].curie == "0000001"


def test_load_vocab_uses_the_converter_when_given(datadir):
    converter = Converter.from_prefix_map({"ex": "https://example.org/"})
    concepts = similarity.load_vocab(datadir / DUPLICATES, converter=converter)

    assert concepts[CO_PRECIPITATION_1].curie == "ex:0000001"


def test_load_vocab_tolerates_a_concept_without_a_definition(tmp_path):
    """A missing definition is a data problem, not a reason to crash."""
    ttl = tmp_path / "no-definition.ttl"
    ttl.write_text(
        "@prefix ex: <https://example.org/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        'ex:0000001 a skos:Concept ; skos:prefLabel "lonely"@en .\n',
        encoding="utf-8",
    )

    concepts = similarity.load_vocab(ttl)

    assert concepts["https://example.org/0000001"].definition == ""


# === Label sentences ===


def test_build_label_sentences_keys_pref_labels_by_concept(concepts):
    labels = similarity.build_label_sentences(concepts, include_alt_labels=False)

    assert labels[(CO_PRECIPITATION_1, "pref_label")] == "co-precipitation"
    assert len(labels) == len(concepts)


def test_build_label_sentences_appends_alt_labels_with_their_position(concepts):
    labels = similarity.build_label_sentences(concepts, include_alt_labels=True)

    alt_labels = {
        key[1]: value for key, value in labels.items() if key[0] == CALCINATION
    }
    assert alt_labels == {
        "pref_label": "calcination",
        "altLabel-0": "co-precipitation",
        "altLabel-1": "thermal decomposition",
    }


def test_build_label_sentences_strips_surrounding_whitespace(tmp_path):
    ttl = tmp_path / "padded.ttl"
    ttl.write_text(
        "@prefix ex: <https://example.org/> .\n"
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        'ex:0000001 a skos:Concept ; skos:prefLabel "  padded  "@en ;\n'
        '    skos:definition "d"@en .\n',
        encoding="utf-8",
    )
    concepts = similarity.load_vocab(ttl)

    labels = similarity.build_label_sentences(concepts, include_alt_labels=False)

    assert labels[("https://example.org/0000001", "pref_label")] == "padded"


# === Which labels get screened (defect 3) ===


def test_keys_of_concepts_selects_every_label_of_the_named_concepts(concepts):
    """Alt labels of a screened concept must be screened too.

    The defect this replaces indexed positions in the concept dict, which
    could never name an alt label, so `compare` skipped them silently.
    """
    labels = similarity.build_label_sentences(concepts, include_alt_labels=True)

    keys = similarity.keys_of_concepts(labels, {CALCINATION})

    assert keys == {
        (CALCINATION, "pref_label"),
        (CALCINATION, "altLabel-0"),
        (CALCINATION, "altLabel-1"),
    }


def test_keys_of_concepts_ignores_concepts_that_carry_no_label(concepts):
    labels = similarity.build_label_sentences(concepts, include_alt_labels=True)

    assert similarity.keys_of_concepts(labels, {"https://example.org/9999999"}) == set()


# === Thresholds ===


def test_thresholds_reject_a_certain_threshold_below_the_label_threshold():
    """A certain threshold under the label threshold can never be reached."""
    with pytest.raises(ValueError, match="threshold-labels-certain"):
        similarity.Thresholds(labels=0.9, definitions=0.8, labels_certain=0.85)


def test_thresholds_accept_a_certain_threshold_equal_to_the_label_threshold():
    thresholds = similarity.Thresholds(labels=0.9, definitions=0.8, labels_certain=0.9)

    assert thresholds.labels_certain == 0.9


# === Candidate selection ===


def score_matrix(labels, pairs, default=0.0):
    """Build a symmetric score matrix over the label keys of `labels`."""
    keys = list(labels)
    matrix = [[default] * len(keys) for _ in keys]
    for position in range(len(keys)):
        matrix[position][position] = 1.0
    for (key_a, key_b), score in pairs.items():
        i, j = keys.index(key_a), keys.index(key_b)
        matrix[i][j] = matrix[j][i] = score
    return matrix


@pytest.fixture
def labels(concepts):
    return similarity.build_label_sentences(concepts, include_alt_labels=True)


@pytest.fixture
def thresholds():
    return similarity.Thresholds(labels=0.9, definitions=0.8, labels_certain=0.98)


def test_select_candidates_reports_a_pair_above_the_label_threshold(labels, thresholds):
    scores = score_matrix(
        labels,
        {((CO_PRECIPITATION_1, "pref_label"), (CO_PRECIPITATION_2, "pref_label")): 1.0},
    )

    candidates = similarity.select_candidates(labels, scores, thresholds)

    assert len(candidates) == 1
    assert candidates[0].similarity_score == 1.0
    assert {candidates[0].concept_id, candidates[0].similar_concept_id} == {
        CO_PRECIPITATION_1,
        CO_PRECIPITATION_2,
    }


def test_select_candidates_ignores_a_pair_below_the_label_threshold(labels, thresholds):
    scores = score_matrix(
        labels,
        {
            (
                (CO_PRECIPITATION_1, "pref_label"),
                (COPRECIPITATION, "pref_label"),
            ): 0.5781
        },
    )

    assert similarity.select_candidates(labels, scores, thresholds) == []


def test_select_candidates_admits_a_score_exactly_on_the_threshold(labels, thresholds):
    """The threshold is inclusive, so `--threshold-defs 0` lets everything through."""
    scores = score_matrix(
        labels,
        {((CO_PRECIPITATION_1, "pref_label"), (COPRECIPITATION, "pref_label")): 0.9},
    )

    assert len(similarity.select_candidates(labels, scores, thresholds)) == 1


def test_select_candidates_never_pairs_a_concept_with_itself(labels, thresholds):
    """A concept's own pref label and alt label always match; that is not news."""
    scores = score_matrix(
        labels,
        {((CALCINATION, "pref_label"), (CALCINATION, "altLabel-0")): 1.0},
    )

    assert similarity.select_candidates(labels, scores, thresholds) == []


def test_select_candidates_reports_a_concept_pair_once_at_its_best_score(
    labels, thresholds
):
    """Pref/pref and pref/alt matches of the same two concepts are one finding."""
    scores = score_matrix(
        labels,
        {
            ((CO_PRECIPITATION_1, "pref_label"), (CALCINATION, "altLabel-0")): 1.0,
            ((CO_PRECIPITATION_1, "pref_label"), (CALCINATION, "pref_label")): 0.92,
        },
    )

    candidates = similarity.select_candidates(labels, scores, thresholds)

    assert len(candidates) == 1
    assert candidates[0].similarity_score == 1.0
    assert candidates[0].similar_sentence_key == (CALCINATION, "altLabel-0")


def test_select_candidates_screens_only_the_requested_labels(labels, thresholds):
    scores = score_matrix(
        labels,
        {
            (
                (CO_PRECIPITATION_1, "pref_label"),
                (CO_PRECIPITATION_2, "pref_label"),
            ): 1.0,
            ((PREPARATION, "pref_label"), (PROCESSING, "pref_label")): 0.95,
        },
    )

    candidates = similarity.select_candidates(
        labels,
        scores,
        thresholds,
        keys_to_screen={(CO_PRECIPITATION_1, "pref_label")},
    )

    assert len(candidates) == 1
    assert candidates[0].concept_id == CO_PRECIPITATION_1


def test_select_candidates_screens_the_alt_labels_of_a_screened_concept(
    labels, thresholds
):
    """Regression for the defect that made `compare` skip every alt label.

    The screening set is keyed on labels, so an alt label of an added concept
    is screened like its preferred label.
    """
    scores = score_matrix(
        labels,
        {((CALCINATION, "altLabel-0"), (CO_PRECIPITATION_1, "pref_label")): 1.0},
    )

    candidates = similarity.select_candidates(
        labels,
        scores,
        thresholds,
        keys_to_screen=similarity.keys_of_concepts(labels, {CALCINATION}),
    )

    assert len(candidates) == 1
    assert candidates[0].sentence_key == (CALCINATION, "altLabel-0")


def test_select_candidates_puts_the_screened_concept_first(labels, thresholds):
    """In `compare` the added concept is the subject of the finding."""
    scores = score_matrix(
        labels,
        {((CO_PRECIPITATION_2, "pref_label"), (CO_PRECIPITATION_1, "pref_label")): 1.0},
    )

    candidates = similarity.select_candidates(
        labels,
        scores,
        thresholds,
        keys_to_screen={(CO_PRECIPITATION_2, "pref_label")},
    )

    assert candidates[0].concept_id == CO_PRECIPITATION_2
    assert candidates[0].similar_concept_id == CO_PRECIPITATION_1


# === The definition rule (the defect reported in issue #387) ===


def candidate(concept_id, similar_concept_id, score):
    return similarity.CandidatePair(
        concept_id=concept_id,
        sentence_key=(concept_id, "pref_label"),
        similar_concept_id=similar_concept_id,
        similar_sentence_key=(similar_concept_id, "pref_label"),
        similarity_score=score,
    )


def test_an_identical_label_is_reported_whatever_the_definitions_say(
    concepts, thresholds
):
    """The case from issue #387.

    voc4cat:0007795 and voc4cat:0008124 both carried the prefLabel
    "co-precipitation" (label score 1.0000) but their definitions scored
    0.6614, below the 0.8 definition threshold, so the pair was dropped.
    """
    pair = candidate(CO_PRECIPITATION_1, CO_PRECIPITATION_2, 1.0)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, CO_PRECIPITATION_2): 0.6614},
        thresholds,
        concepts,
    )

    assert len(reported) == 1
    assert reported[0].similarity_score == 1.0
    assert reported[0].definition_similarity_score == 0.6614


def test_a_merely_similar_label_still_needs_a_similar_definition(concepts, thresholds):
    pair = candidate(CO_PRECIPITATION_1, CALCINATION, 0.93)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, CALCINATION): 0.6614},
        thresholds,
        concepts,
    )

    assert reported == []


def test_a_merely_similar_label_is_reported_when_the_definitions_agree(
    concepts, thresholds
):
    pair = candidate(CO_PRECIPITATION_1, CALCINATION, 0.93)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, CALCINATION): 0.85},
        thresholds,
        concepts,
    )

    assert len(reported) == 1


def test_the_certain_threshold_is_inclusive(concepts, thresholds):
    pair = candidate(CO_PRECIPITATION_1, CALCINATION, 0.98)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, CALCINATION): 0.0},
        thresholds,
        concepts,
    )

    assert len(reported) == 1


def test_a_shared_broader_concept_is_recorded(concepts, thresholds):
    """0000001 and 0000003 are both narrower than 0000010."""
    pair = candidate(CO_PRECIPITATION_1, COPRECIPITATION, 1.0)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, COPRECIPITATION): 0.9},
        thresholds,
        concepts,
    )

    assert reported[0].have_same_broader_concept is True


def test_unrelated_broader_concepts_are_recorded_as_such(concepts, thresholds):
    """0000001 is narrower than 0000010, 0000002 than 0000011."""
    pair = candidate(CO_PRECIPITATION_1, CO_PRECIPITATION_2, 1.0)

    reported = similarity.apply_definition_rule(
        [pair],
        {similarity.pair_key(CO_PRECIPITATION_1, CO_PRECIPITATION_2): 0.9},
        thresholds,
        concepts,
    )

    assert reported[0].have_same_broader_concept is False


def test_findings_are_sorted_by_label_score_then_definition_score(concepts, thresholds):
    pairs = [
        candidate(CO_PRECIPITATION_1, CALCINATION, 0.95),
        candidate(CO_PRECIPITATION_1, PREPARATION, 1.0),
        candidate(CO_PRECIPITATION_2, PROCESSING, 1.0),
    ]
    definition_scores = {
        similarity.pair_key(CO_PRECIPITATION_1, CALCINATION): 0.99,
        similarity.pair_key(CO_PRECIPITATION_1, PREPARATION): 0.81,
        similarity.pair_key(CO_PRECIPITATION_2, PROCESSING): 0.95,
    }

    reported = similarity.apply_definition_rule(
        pairs, definition_scores, thresholds, concepts
    )

    assert [
        (found.similarity_score, found.definition_similarity_score)
        for found in reported
    ] == [(1.0, 0.95), (1.0, 0.81), (0.95, 0.99)]
