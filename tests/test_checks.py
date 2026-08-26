"""Tests for voc4cat.checks module."""

import logging
import os
import shutil
from pathlib import Path
from unittest import mock

import pytest
from rdflib import RDF, SKOS, Graph, Literal, Namespace, URIRef

from tests.conftest import VOCAB_IRI, write_vocab
from voc4cat.checks import (
    Voc4catError,
    check_for_removed_iris,
    check_hierarchical_redundancy,
    check_new_ids_in_actor_range,
    check_number_of_files_in_inbox,
    validate_config_has_idrange,
    validate_vocabulary_files_for_ci_workflow,
)

VALID_CONFIG = "valid_idranges.toml"


def test_validate_config_has_idrange(datadir, temp_config):
    """Test voc4cat.checks"""

    # default config -> no check possible
    vocab = "missing"
    assert validate_config_has_idrange(vocab) is None

    # Adapt a valid config for the test
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.single_vocab = False
    extra_vocab = config.Vocab(
        id_length=5,
        permanent_iri_part="https://example.org",
        checks={},
        prefix_map={},
        id_range=[],
        # Mandatory fields
        vocabulary_iri="https://example.org/another/",
        title="Another Vocabulary",
        description="Another test vocabulary",
        created_date="2025-01-01",
        creator="Test Author",
        repository="https://github.com/test/another",
    )
    config.IDRANGES.vocabs["another_vocab"] = extra_vocab
    config.load_config(config=config.IDRANGES)

    assert validate_config_has_idrange("myvocab") is None
    with pytest.raises(Voc4catError) as excinfo:
        validate_config_has_idrange(vocab)
    assert (
        f"Config requires at least one ID range in a section [[vocabs.{vocab}.id_range]]."
        in str(excinfo.value)
    )


def test_check_number_of_files_in_inbox(datadir, tmp_path, temp_config, cs_cycles_xlsx):
    # no warning for default config
    assert check_number_of_files_in_inbox(datadir) is None

    # Load a valid stricter config
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)

    assert check_number_of_files_in_inbox(tmp_path) is None

    # Create a test directory with multiple xlsx files to trigger the error
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(cs_cycles_xlsx, inbox / "vocab1.xlsx")
    shutil.copy(cs_cycles_xlsx, inbox / "vocab2.xlsx")

    with pytest.raises(Voc4catError) as excinfo:
        check_number_of_files_in_inbox(inbox)
    assert "The single vocabulary option is active but " in str(excinfo.value)


# To give the same result on gh-actions we need to clear the CI_RUN envvar
@mock.patch.dict(os.environ, {"CI_RUN": ""})
def test_validate_vocabulary_files_for_ci_workflow_default(
    datadir, caplog, temp_config, tmp_path, cs_cycles_xlsx
):
    """
    Test for validate_vocabulary_files_for_ci_workflow.

    Tests for default config. single_vocab=False and envvar "CI_Run" not set.
    """
    # The loose default config results only in a warning.
    with caplog.at_level(logging.WARNING):
        validate_vocabulary_files_for_ci_workflow(datadir, datadir)
    assert (
        "To validate file names the config requires at least one vocabulary section."
        in caplog.text
    )
    caplog.clear()

    # Load the valid test config and change it to accept multiple vocabularies
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.single_vocab = False
    config.load_config(config=config.IDRANGES)

    inbox = tmp_path / "pr" / "inbox"
    inbox.mkdir(parents=True)
    vocab = tmp_path / "pr" / "vocab"
    vocab.mkdir(parents=True)
    shutil.copy(cs_cycles_xlsx, inbox / "concept-scheme-with-cycles.xlsx")

    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(vocab, inbox)
    assert (
        'Missing vocabulary id_range config for "concept-scheme-with-cycles".'
        in str(excinfo.value)
    )

    # Check for inappropriate file in inbox
    # To reach this check we need a correct idrange section.
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.single_vocab = False
    config.IDRANGES.vocabs["concept-scheme-with-cycles"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)

    (inbox / "extra_file").touch()

    with caplog.at_level(logging.WARNING):
        retval = validate_vocabulary_files_for_ci_workflow(vocab, inbox)
    assert (
        f'Directory "{inbox}" should only contain xlsx files and README.md.'
        in caplog.text
    )
    assert retval is None


@mock.patch.dict(os.environ, {"CI_RUN": "true"})
def test_validate_vocabulary_files_for_ci_workflow_single_vocab(
    datadir, tmp_path, temp_config, cs_cycles_xlsx
):
    """Test for validate_vocabulary_files_for_ci_workflow.

    Tests for single_vocab=True and envvar "CI_Run" set.
    """
    # Load a valid stricter config.
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.vocabs["concept-scheme-with-cycles"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)

    pr_inbox = tmp_path / "pr" / "inbox"
    pr_inbox.mkdir(parents=True)
    pr_vocab = tmp_path / "pr" / "vocab"
    pr_vocab.mkdir(parents=True)

    # Test valid use cases for single_vocab = True
    shutil.copy(cs_cycles_xlsx, pr_inbox / "concept-scheme-with-cycles.xlsx")
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    vocab_file = "concept-scheme-with-cycles.ttl"
    shutil.copy(datadir / vocab_file, pr_vocab)
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    os.remove(pr_inbox / "concept-scheme-with-cycles.xlsx")
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None

    # More than one vocab in vocab-dir (copy cycles.ttl with different name)
    shutil.copy(
        datadir / "concept-scheme-with-cycles.ttl", pr_vocab / "other-vocab.ttl"
    )
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert f'Directory "{pr_vocab}" may contain only a single vocabulary.' in str(
        excinfo.value
    )
    os.remove(pr_vocab / "other-vocab.ttl")

    # Test invalid use cases for single_vocab = True
    inbox_file = "other-vocab.xlsx"
    shutil.copy(cs_cycles_xlsx, pr_inbox / inbox_file)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'The file in inbox "{pr_inbox / inbox_file}" must match the vocabulary name "{Path(vocab_file).stem}".'
        in str(excinfo.value)
    )

    # Inappropriate other files inbox
    shutil.copy(datadir / "valid_idranges.toml", pr_inbox)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert f'Directory "{pr_inbox}" may only contain xlsx files and README.md.' in str(
        excinfo.value
    )
    os.remove(pr_inbox / "valid_idranges.toml")

    # One vocab but without idranges specified.
    unconfigured_vocab = "unconfigured_vocab.ttl"
    os.rename(pr_vocab / vocab_file, pr_vocab / unconfigured_vocab)
    os.remove(pr_inbox / inbox_file)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'Vocabulary "{Path(unconfigured_vocab).stem}" in "{pr_vocab}" must be also present in config.'
        in str(excinfo.value)
    )

    # One inbox file but without idranges specified.
    os.remove(pr_vocab / unconfigured_vocab)
    inbox_file = "other-vocab.xlsx"
    shutil.copy(cs_cycles_xlsx, pr_inbox / inbox_file)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'New vocabulary "{Path(inbox_file).stem}" in "{pr_inbox}" must be also present in config.'
        in str(excinfo.value)
    )


@mock.patch.dict(os.environ, {"CI_RUN": "true"}, clear=True)
def test_validate_vocabulary_files_for_ci_workflow_multi_vocab(
    datadir, tmp_path, temp_config, caplog, cs_cycles_xlsx
):
    """Test for validate_vocabulary_files_for_ci_workflow.

    Tests for single_vocab=False and envvar "CI_Run" set.
    """
    # Load a valid stricter config.
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.vocabs["concept-scheme-with-cycles"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.IDRANGES.vocabs["concept-scheme-with-cycles"].checks.allow_delete = True
    config.load_config(config=config.IDRANGES)

    (tmp_path / "pr" / "inbox").mkdir(parents=True)
    (tmp_path / "pr" / "vocab").mkdir(parents=True)
    pr_inbox = tmp_path / "pr" / "inbox"
    pr_vocab = tmp_path / "pr" / "vocab"

    # Test multi-vocab scenario: configured vocab + unconfigured vocab
    shutil.copy(cs_cycles_xlsx, pr_inbox / "other-vocab.xlsx")
    shutil.copy(cs_cycles_xlsx, pr_inbox / "concept-scheme-with-cycles.xlsx")
    shutil.copy(datadir / "concept-scheme-with-cycles.ttl", pr_vocab)

    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert 'Missing vocabulary id_range config for "other-vocab".' in str(excinfo.value)


@pytest.mark.parametrize(
    ("skos_el", "log_text"),
    [
        (SKOS.Concept, "Removal of a Concept detected"),
        (SKOS.Collection, "Removal of a Collection detected"),
    ],
)
def test_check_for_removed_iris(  # noqa: PLR0913
    datadir, tmp_path, temp_config, caplog, skos_el, log_text
):
    original = datadir / "concept-scheme-with-cycles.ttl"
    # Prepare data with removed concept
    g = Graph()
    g.parse(original, format="turtle")
    one_uri = next(iter(g.subjects(RDF.type, skos_el)))
    g.remove((one_uri, None, None))
    reduced = tmp_path / (str(original.stem) + "_reduced.turtle")
    g.serialize(destination=reduced, format="turtle")

    # Test with a config that forbids to delete.
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.vocabs["concept-scheme-with-cycles"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(
            Voc4catError,
            match=r"Forbidden removal of 1 concepts\/collections detected. See log for IRIs.",
        ),
    ):
        check_for_removed_iris(original, reduced)
    assert log_text in caplog.text

    # Change to a config that allows to delete.
    config.IDRANGES.vocabs["concept-scheme-with-cycles"].checks.allow_delete = True
    config.load_config(config=config.IDRANGES)
    with caplog.at_level(logging.WARNING):
        check_for_removed_iris(original, reduced)
    assert log_text in caplog.text
    # no log message for adding content
    assert check_for_removed_iris(reduced, original) is None


def test_check_hierarchical_redundancy_with_redundancy(tmp_path):
    """Test detection of redundant hierarchical relationships."""
    # Create a vocabulary with redundant hierarchy:
    # C -> broader -> B -> broader -> A
    # C -> broader -> A  (redundant! A is ancestor of B)
    ex = Namespace("http://example.org/")
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("ex", ex)  # Bind prefix for CURIE output

    # Add concept scheme
    cs = URIRef("http://example.org/scheme")
    g.add((cs, RDF.type, SKOS.ConceptScheme))
    g.add((cs, SKOS.prefLabel, Literal("Test Scheme", lang="en")))

    # Add concepts A, B, C
    for concept_id in ["A", "B", "C"]:
        concept = ex[concept_id]
        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.prefLabel, Literal(f"Concept {concept_id}", lang="en")))
        g.add((concept, SKOS.inScheme, cs))

    # A is top concept
    g.add((cs, SKOS.hasTopConcept, ex.A))

    # B -> broader -> A
    g.add((ex.B, SKOS.broader, ex.A))

    # C -> broader -> B (direct parent)
    g.add((ex.C, SKOS.broader, ex.B))

    # C -> broader -> A (redundant! A is already reachable via B)
    g.add((ex.C, SKOS.broader, ex.A))

    vocab_file = tmp_path / "redundant_vocab.ttl"
    g.serialize(destination=vocab_file, format="turtle")

    redundancies = check_hierarchical_redundancy(vocab_file)

    assert len(redundancies) == 1
    concept, ancestor, parent = redundancies[0]
    # Results are now in CURIE format
    assert concept == "ex:C"
    assert ancestor == "ex:A"
    assert parent == "ex:B"


def test_check_hierarchical_redundancy_without_redundancy(tmp_path):
    """Test that clean hierarchies produce no warnings."""
    # Create a vocabulary without redundancy:
    # C -> broader -> B -> broader -> A (clean chain)
    ex = Namespace("http://example.org/")
    g = Graph()
    g.bind("skos", SKOS)

    # Add concept scheme
    cs = URIRef("http://example.org/scheme")
    g.add((cs, RDF.type, SKOS.ConceptScheme))
    g.add((cs, SKOS.prefLabel, Literal("Test Scheme", lang="en")))

    # Add concepts A, B, C
    for concept_id in ["A", "B", "C"]:
        concept = ex[concept_id]
        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.prefLabel, Literal(f"Concept {concept_id}", lang="en")))
        g.add((concept, SKOS.inScheme, cs))

    # A is top concept
    g.add((cs, SKOS.hasTopConcept, ex.A))

    # B -> broader -> A
    g.add((ex.B, SKOS.broader, ex.A))

    # C -> broader -> B (only direct parent, no redundancy)
    g.add((ex.C, SKOS.broader, ex.B))

    vocab_file = tmp_path / "clean_vocab.ttl"
    g.serialize(destination=vocab_file, format="turtle")

    redundancies = check_hierarchical_redundancy(vocab_file)

    assert len(redundancies) == 0


# ===== check_new_ids_in_actor_range =====


@pytest.fixture
def myvocab_config(datadir, temp_config):
    """Config with vocabulary "myvocab": 1-10 sofia-garcia, 11-20 unknown, 21-30 orcid."""
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    return config


def test_new_id_inside_actor_range_passes(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 5])

    assert check_new_ids_in_actor_range(prev, new, "sofia-garcia") is None


def test_new_id_outside_actor_range_raises(tmp_path, myvocab_config, caplog):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    # ID 15 belongs to the range of actor "unknown", not to sofia-garcia
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 15])

    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError) as excinfo:
        check_new_ids_in_actor_range(prev, new, "sofia-garcia")

    assert "1 new IRI" in str(excinfo.value)
    assert f"{VOCAB_IRI}0000015" in caplog.text
    assert "sofia-garcia" in caplog.text


def test_id_in_gap_between_actor_ranges_raises(tmp_path, temp_config, mandatory_fields):
    """Ranges of one actor are disjoint; IDs in the gap are not allowed."""
    config = temp_config
    config.IDRANGES.vocabs["myvocab"] = config.Vocab(
        id_length=7,
        permanent_iri_part=VOCAB_IRI,
        checks={},
        prefix_map={},
        id_range=[
            {"first_id": 1, "last_id": 100, "gh_name": "sofia-garcia"},
            {"first_id": 250, "last_id": 300, "gh_name": "sofia-garcia"},
        ],
        **mandatory_fields,
    )
    config.load_config(config=config.IDRANGES)

    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    in_second_range = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 275])
    assert check_new_ids_in_actor_range(prev, in_second_range, "sofia-garcia") is None

    in_gap = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 175])
    with pytest.raises(Voc4catError):
        check_new_ids_in_actor_range(prev, in_gap, "sofia-garcia")


def test_id_range_of_other_vocabulary_does_not_apply(
    tmp_path, myvocab_config, mandatory_fields
):
    """A range granted for another vocabulary must not permit IDs here."""
    config = myvocab_config
    config.IDRANGES.single_vocab = False
    config.IDRANGES.vocabs["othervocab"] = config.Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/other/",
        checks={},
        prefix_map={},
        id_range=[{"first_id": 500, "last_id": 600, "gh_name": "sofia-garcia"}],
        **mandatory_fields,
    )
    config.load_config(config=config.IDRANGES)

    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 550])

    with pytest.raises(Voc4catError):
        check_new_ids_in_actor_range(prev, new, "sofia-garcia")


def test_unchanged_out_of_range_id_is_not_flagged(tmp_path, myvocab_config):
    """Editing a vocabulary must not fail over IDs someone else created."""
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[15])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[15, 5])

    assert check_new_ids_in_actor_range(prev, new, "sofia-garcia") is None


def test_all_ids_checked_when_no_previous_version(tmp_path, myvocab_config):
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[15])

    with pytest.raises(Voc4catError):
        check_new_ids_in_actor_range(None, new, "sofia-garcia")


def test_collections_are_checked(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1], collection_ids=[15])

    with pytest.raises(Voc4catError):
        check_new_ids_in_actor_range(prev, new, "sofia-garcia")


def test_ordered_collections_are_checked(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1], ordered_ids=[15])

    with pytest.raises(Voc4catError):
        check_new_ids_in_actor_range(prev, new, "sofia-garcia")


def test_iris_outside_the_vocabulary_are_ignored(tmp_path, myvocab_config):
    """Concepts of other vocabularies may be referenced and are not our IDs."""
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(
        tmp_path / "myvocab.ttl",
        concept_ids=[1, 5],
        foreign=["https://other.example/0000015"],
    )

    assert check_new_ids_in_actor_range(prev, new, "sofia-garcia") is None


def test_actor_is_matched_case_insensitively(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 5])

    assert check_new_ids_in_actor_range(prev, new, "Sofia-Garcia") is None


def test_actor_without_id_range_raises(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 5])

    with pytest.raises(Voc4catError) as excinfo:
        check_new_ids_in_actor_range(prev, new, "mallory")

    assert "mallory" in str(excinfo.value)
    assert "myvocab" in str(excinfo.value)


@mock.patch.dict(os.environ, {"CI_RUN": "true"})
def test_missing_actor_raises_in_ci(tmp_path, myvocab_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 15])

    with pytest.raises(Voc4catError) as excinfo:
        check_new_ids_in_actor_range(prev, new, "")

    assert "GITHUB_ACTOR" in str(excinfo.value)


@mock.patch.dict(os.environ, {"CI_RUN": ""})
def test_missing_actor_warns_outside_ci(tmp_path, myvocab_config, caplog):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 15])

    with caplog.at_level(logging.WARNING):
        assert check_new_ids_in_actor_range(prev, new, "") is None

    assert "GITHUB_ACTOR" in caplog.text


def test_no_check_without_vocabulary_config(tmp_path, temp_config):
    prev = write_vocab(tmp_path / "prev.ttl", concept_ids=[1])
    new = write_vocab(tmp_path / "myvocab.ttl", concept_ids=[1, 15])

    assert check_new_ids_in_actor_range(prev, new, "sofia-garcia") is None
