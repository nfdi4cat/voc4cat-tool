"""Tests for voc4cat.checks module."""

import logging
import os
import shutil
from pathlib import Path
from unittest import mock

import pytest
from rdflib import RDF, SKOS, Graph
from voc4cat.checks import (
    Voc4catError,
    check_for_removed_iris,
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


def test_check_number_of_files_in_inbox(datadir, tmp_path, temp_config):
    # no warning for default config
    assert check_number_of_files_in_inbox(datadir) is None

    # Load a valid stricter config
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)

    assert check_number_of_files_in_inbox(tmp_path) is None
    with pytest.raises(Voc4catError) as excinfo:
        check_number_of_files_in_inbox(datadir)
    assert "The single vocabulary option is active but " in str(excinfo.value)


# To give the same result on gh-actions we need to clear the CI_RUN envvar
@mock.patch.dict(os.environ, {"CI_RUN": ""})
def test_validate_vocabulary_files_for_ci_workflow_default(
    datadir, caplog, temp_config, tmp_path
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
    shutil.copy(datadir / "concept-scheme-simple.xlsx", inbox)

    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(vocab, inbox)
    assert 'Missing vocabulary id_range config for "concept-scheme-simple".' in str(
        excinfo.value
    )

    # Check for inappropriate file in inbox
    # To reach this check we need a correct idrange section.
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.single_vocab = False
    config.IDRANGES.vocabs["concept-scheme-simple"] = config.IDRANGES.vocabs.pop(
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
    datadir, tmp_path, temp_config
):
    """Test for validate_vocabulary_files_for_ci_workflow.

    Tests for single_vocab=True and envvar "CI_Run" set.
    """
    # Load a valid stricter config.
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.vocabs["concept-scheme-simple"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)

    pr_inbox = tmp_path / "pr" / "inbox"
    pr_inbox.mkdir(parents=True)
    pr_vocab = tmp_path / "pr" / "vocab"
    pr_vocab.mkdir(parents=True)

    # Test valid use cases for single_vocab = True
    shutil.copy(datadir / "concept-scheme-simple.xlsx", pr_inbox)
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    vocab_file = "concept-scheme-simple.ttl"
    shutil.copy(datadir / vocab_file, pr_vocab)
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    os.remove(pr_inbox / "concept-scheme-simple.xlsx")
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None

    # More than one vocab in vocab-dir
    shutil.copy(datadir / "concept-scheme-with-cycles.ttl", pr_vocab)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert f'Directory "{pr_vocab}" may contain only a single vocabulary.' in str(
        excinfo.value
    )
    os.remove(pr_vocab / "concept-scheme-with-cycles.ttl")

    # Test invalid use cases for single_vocab = True
    inbox_file = "concept-scheme-with-cycles.xlsx"
    shutil.copy(datadir / inbox_file, pr_inbox)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'The file in inbox "{pr_inbox/inbox_file}" must match the vocabulary name "{Path(vocab_file).stem}".'
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
    inbox_file = "concept-scheme-with-cycles.xlsx"
    shutil.copy(datadir / inbox_file, pr_inbox)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'New vocabulary "{Path(inbox_file).stem}" in "{pr_inbox}" must be also present in config.'
        in str(excinfo.value)
    )


@mock.patch.dict(os.environ, {"CI_RUN": "true"}, clear=True)
def test_validate_vocabulary_files_for_ci_workflow_multi_vocab(
    datadir, tmp_path, temp_config, caplog
):
    """Test for validate_vocabulary_files_for_ci_workflow.

    Tests for single_vocab=False and envvar "CI_Run" set.
    """
    # Load a valid stricter config.
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)
    config.IDRANGES.vocabs["concept-scheme-simple"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.IDRANGES.vocabs["concept-scheme-simple"].checks.allow_delete = True
    config.load_config(config=config.IDRANGES)

    (tmp_path / "pr" / "inbox").mkdir(parents=True)
    (tmp_path / "pr" / "vocab").mkdir(parents=True)
    pr_inbox = tmp_path / "pr" / "inbox"
    pr_vocab = tmp_path / "pr" / "vocab"

    # Test valid use cases for single_vocab = True
    shutil.copy(datadir / "concept-scheme-with-cycles.xlsx", pr_inbox)
    shutil.copy(datadir / "concept-scheme-simple.xlsx", pr_inbox)
    shutil.copy(datadir / "concept-scheme-simple.ttl", pr_vocab)

    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        'Missing vocabulary id_range config for "concept-scheme-with-cycles".'
        in str(excinfo.value)
    )


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
    original = datadir / "concept-scheme-simple.ttl"
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
    config.IDRANGES.vocabs["concept-scheme-simple"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)

    with caplog.at_level(logging.ERROR), pytest.raises(
        Voc4catError,
        match=r"Forbidden removal of 1 concepts\/collections detected. See log for IRIs.",
    ):
        check_for_removed_iris(original, reduced)
    assert log_text in caplog.text

    # Change to a config that allows to delete.
    config.IDRANGES.vocabs["concept-scheme-simple"].checks.allow_delete = True
    config.load_config(config=config.IDRANGES)
    with caplog.at_level(logging.WARNING):
        check_for_removed_iris(original, reduced)
    assert log_text in caplog.text
    # no log message for adding content
    assert check_for_removed_iris(reduced, original) is None
