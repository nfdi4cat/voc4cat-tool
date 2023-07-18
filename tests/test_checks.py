"""Tests for voc4cat.checks module."""

import logging
import os
import shutil
from pathlib import Path

import pytest
from rdflib import RDF, SKOS, Graph
from voc4cat import config
from voc4cat.checks import (
    Voc4catError,
    check_for_removed_iris,
    check_number_of_files_in_inbox,
    validate_config_has_idrange,
    validate_vocabulary_files_for_ci_workflow,
)

VALID_CONFIG = "valid_idranges.toml"


def test_validate_config_has_idrange(datadir):
    """Test voc4cat.checks"""

    # default config -> no check possible
    vocab = "missing"
    assert validate_config_has_idrange(vocab) is None

    # Adapt a valid config for the test
    conf = config.load_config(datadir / VALID_CONFIG)
    conf.single_vocab = False
    extra_vocab = config.Vocab(
        id_length=5,
        permanent_iri_part="https://example.org",
        checks={},
        prefix_map={},
        id_range=[],
    )
    conf.vocabs["another_vocab"] = extra_vocab
    config.IDRANGES = config.IDrangeConfig().parse_raw(conf.json())

    assert validate_config_has_idrange("myvocab") is None
    with pytest.raises(Voc4catError) as excinfo:
        validate_config_has_idrange(vocab)
    assert f"Config for vocabulary {vocab} has no section [vocabs.*.id_range]." in str(
        excinfo.value
    )

    # Reset the globally changed config.
    config.IDRANGES = config.load_config()


def test_check_number_of_files_in_inbox(datadir, tmp_path):
    # no warning for default config
    assert check_number_of_files_in_inbox(datadir) is None

    # Load a valid stricter config
    config.IDRANGES = config.load_config(datadir / VALID_CONFIG)

    assert check_number_of_files_in_inbox(tmp_path) is None
    with pytest.raises(Voc4catError) as excinfo:
        check_number_of_files_in_inbox(datadir)
    assert "The single vocabulary option is active but " in str(excinfo.value)

    # Reset the globally changed config.
    config.IDRANGES = config.load_config()


def test_validate_vocabulary_files_for_ci_workflow_default(datadir, caplog):
    # The loose default config results only in a warning.
    with caplog.at_level(logging.WARNING):
        validate_vocabulary_files_for_ci_workflow(datadir, datadir)
    assert (
        "To validate vocabulary names an idrange-configuration must be present."
        in caplog.text
    )


def test_validate_vocabulary_files_for_ci_workflow_one_vocab(datadir, tmp_path, caplog):
    # Load a valid stricter config.
    conf = config.load_config(datadir / VALID_CONFIG)
    conf.vocabs["concept-scheme-simple"] = conf.vocabs.pop("myvocab")
    conf.vocabs["concept-scheme-simple"].checks.allow_delete = True
    config.IDRANGES = config.IDrangeConfig().parse_raw(conf.json())

    (tmp_path / "main").mkdir(parents=True)
    (tmp_path / "pr" / "inbox").mkdir(parents=True)
    (tmp_path / "pr" / "vocab").mkdir(parents=True)
    pr_inbox = tmp_path / "pr" / "inbox"
    pr_vocab = tmp_path / "pr" / "vocab"

    # Test valid use cases for single_vocab = True
    shutil.copy(datadir / "concept-scheme-simple.xlsx", pr_inbox)
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    vocab_file = "concept-scheme-simple.ttl"
    shutil.copy(datadir / vocab_file, pr_vocab)
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None
    os.remove(pr_inbox / "concept-scheme-simple.xlsx")
    assert validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox) is None

    # Test invalid use cases for single_vocab = True
    inbox_file = "concept-scheme-with-cycles.xlsx"
    shutil.copy(datadir / inbox_file, pr_inbox)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'The file in inbox "{pr_inbox/inbox_file}" must match the vocabulary name "{Path(vocab_file).stem}".'
        in str(excinfo.value)
    )
    # One vocab but without a config.
    unconfigured_vocab = "unconfigured_vocab.ttl"
    os.rename(pr_vocab / vocab_file, pr_vocab / unconfigured_vocab)
    os.remove(pr_inbox / inbox_file)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'Vocabulary "{Path(unconfigured_vocab).stem}" in "{pr_vocab}" must be also present in config.'
        in str(excinfo.value)
    )

    # One inbox file but without a config.
    os.remove(pr_vocab / unconfigured_vocab)
    inbox_file = "concept-scheme-with-cycles.xlsx"
    shutil.copy(datadir / inbox_file, pr_inbox)
    with pytest.raises(Voc4catError) as excinfo:
        validate_vocabulary_files_for_ci_workflow(pr_vocab, pr_inbox)
    assert (
        f'New vocabulary "{Path(inbox_file).stem}" in "{pr_inbox}" must be also present in config.'
        in str(excinfo.value)
    )

    # Reset the globally changed config.
    config.IDRANGES = config.load_config()


def test_validate_vocabulary_files_for_ci_workflow_multi_vocab(
    datadir, tmp_path, caplog
):
    # Load a valid stricter config.
    conf = config.load_config(datadir / VALID_CONFIG)
    conf.vocabs["concept-scheme-simple"] = conf.vocabs.pop("myvocab")
    conf.vocabs["concept-scheme-simple"].checks.allow_delete = True
    config.IDRANGES = config.IDrangeConfig().parse_raw(conf.json())

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

    # Reset the globally changed config.
    config.IDRANGES = config.load_config()


def test_check_for_removed_iris(datadir, tmp_path):
    original = datadir / "concept-scheme-simple.ttl"
    # Prepare data with removed concept
    g = Graph()
    g.parse(original, format="turtle")
    one_uri = list(g.subjects(RDF.type, SKOS.Concept))[0]
    # Leaving parts of the triple unspecified will remove all matching triples.
    g.remove((one_uri, None, None))
    reduced = tmp_path / (str(original.stem) + "_reduced.turtle")
    g.serialize(destination=reduced, format="turtle")

    with pytest.raises(
        Voc4catError,
        match=r"Forbidden removal of 1 concepts\/collections detected. See log for IRIs.",
    ):
        check_for_removed_iris(original, reduced)


@pytest.mark.parametrize(
    ("skos_el", "log_text"),
    [
        (SKOS.Concept, "Removal of a Concept detected"),
        (SKOS.Collection, "Removal of a Collection detected"),
    ],
)
def test_check_for_removed_iris_logs(datadir, tmp_path, caplog, skos_el, log_text):
    original = datadir / "concept-scheme-simple.ttl"
    # Prepare data with removed concept
    g = Graph()
    g.parse(original, format="turtle")
    one_uri = list(g.subjects(RDF.type, skos_el))[0]
    g.remove((one_uri, None, None))
    reduced = tmp_path / (str(original.stem) + "_reduced.turtle")
    g.serialize(destination=reduced, format="turtle")

    # Change to a config that allows to delete.
    conf = config.load_config(datadir / VALID_CONFIG)
    conf.vocabs["concept-scheme-simple"] = conf.vocabs.pop("myvocab")
    conf.vocabs["concept-scheme-simple"].checks.allow_delete = True
    config.IDRANGES = config.IDrangeConfig().parse_raw(conf.json())
    with caplog.at_level(logging.WARNING):
        check_for_removed_iris(original, reduced)
    assert log_text in caplog.text
    # no log message for adding content
    assert check_for_removed_iris(reduced, original) is None

    # Reset the globally changed config.
    config.IDRANGES = config.load_config()
