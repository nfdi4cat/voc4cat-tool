import logging
import shutil
from pathlib import Path

import pytest
from test_cli import (
    CS_CYCLES,
    CS_CYCLES_INDENT,
    CS_CYCLES_INDENT_IRI,
    CS_SIMPLE,
    CS_SIMPLE_TURTLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli
from voc4cat.utils import ConversionError


@pytest.mark.parametrize(
    ("test_file", "msg"),
    [
        (CS_CYCLES, "xlsx check passed"),
        (
            CS_CYCLES_INDENT_IRI,
            'Same Concept IRI "ex:test/term1" used more than once for language "en"',
        ),
    ],
    ids=["no error", "with error"],
)
def test_check_xlsx(datadir, tmp_path, caplog, test_file, msg):
    dst = tmp_path / test_file
    shutil.copy(datadir / test_file, dst)
    with caplog.at_level(logging.INFO):
        main_cli(["check", "--inplace", str(dst)])
    assert msg in caplog.text
    # TODO check that erroneous cells get colored.


def test_check_skos_rdf(datadir, tmp_path, caplog):
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    with caplog.at_level(logging.INFO):
        main_cli(["check", str(tmp_path / CS_SIMPLE_TURTLE)])
    assert "The file is valid according to the vocpub profile." in caplog.text


def test_check_skos_badfile(monkeypatch, datadir, tmp_path, caplog):
    """Check failing profile validation."""
    shutil.copy(datadir / CS_CYCLES_INDENT, tmp_path)
    monkeypatch.chdir(tmp_path)
    main_cli(["convert", CS_CYCLES_INDENT])
    with caplog.at_level(logging.ERROR), pytest.raises(ConversionError):
        main_cli(["check", str(Path(CS_CYCLES_INDENT).with_suffix(".ttl"))])
    assert "VIOLATION: Validation Result in MinCountConstraintComponent" in caplog.text


def test_check_list_profiles(capsys):
    main_cli(["check", "--listprofiles"])
    captured = capsys.readouterr()
    assert "Profiles" in captured.out


def test_check_missing_vocab(caplog):
    with caplog.at_level(logging.ERROR):
        main_cli(["check"])
    assert "Argument VOCAB is required for this sub-command" in caplog.text


def test_check_overwrite_warning(monkeypatch, datadir, tmp_path, caplog):
    shutil.copy(datadir / CS_SIMPLE, tmp_path / CS_SIMPLE)
    monkeypatch.chdir(tmp_path)
    # Try to run a command that would overwrite the input file with the output file
    # a) dir as input:
    with caplog.at_level(logging.WARNING):
        main_cli(["check", str(tmp_path)])
    assert "This command will overwrite the existing file" in caplog.text
    # b) file as input
    with caplog.at_level(logging.WARNING):
        main_cli(["check", str(tmp_path / CS_SIMPLE)])


def test_check_ci_pre(datadir, tmp_path, temp_config, caplog):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    vocabdir = tmp_path / "vocabularies"
    vocabdir.mkdir(parents=True, exist_ok=True)
    # Copy test files
    shutil.copy(datadir / CS_SIMPLE, inbox / "myvocab.xlsx")
    shutil.copy(datadir / "valid_idranges.toml", tmp_path / "idranges.toml")
    # Load/prepare a valid strict config
    config = temp_config
    config.load_config(tmp_path / "idranges.toml")
    config.IDRANGES.vocabs["myvocab"].id_length = 2
    config.IDRANGES.vocabs["myvocab"].permanent_iri_part = "http://example.org/test"
    config.load_config(config=config.IDRANGES)
    # Convert vocabulary to ttl and store in vocabdir
    main_cli(["convert", "-v", "--outdir", str(vocabdir), str(inbox)])

    # Test with one xlsx file in inbox
    with caplog.at_level(logging.DEBUG):
        main_cli(["check", "-v", "--ci-pre", str(inbox), str(vocabdir)])
    assert "Found 1 xlsx file" in caplog.text


def test_check_ci_post(datadir, tmp_path, temp_config, caplog):
    previous = tmp_path / "previous"
    previous.mkdir()
    vocabdir = tmp_path / "vocabularies"
    vocabdir.mkdir(parents=True, exist_ok=True)
    # Copy test files
    shutil.copy(datadir / CS_SIMPLE, previous / "myvocab.xlsx")
    shutil.copy(datadir / "valid_idranges.toml", tmp_path / "idranges.toml")
    # Load/prepare a valid strict config
    config = temp_config
    config.load_config(tmp_path / "idranges.toml")
    config.IDRANGES.vocabs["myvocab"].id_length = 2
    config.IDRANGES.vocabs["myvocab"].permanent_iri_part = "http://example.org/test"
    config.load_config(config=config.IDRANGES)
    # Convert vocabulary to ttl and store in vocabdir
    main_cli(["convert", "-v", "--outdir", str(vocabdir), str(previous)])

    # Test without a previous vocabulary version in previous-dir
    with caplog.at_level(logging.DEBUG):
        main_cli(["check", "-v", "--ci-post", str(previous), str(vocabdir)])
    assert 'previous version of vocabulary "myvocab.ttl" does not exist.' in caplog.text

    shutil.copy(vocabdir / "myvocab.ttl", previous)
    # Test with a previous vocabulary version in previous-dir
    with caplog.at_level(logging.DEBUG):
        main_cli(["check", "-v", "--ci-post", str(previous), str(vocabdir)])
    assert "No removals detected." in caplog.text

    caplog.clear()
    (previous / "myvocab").mkdir()
    shutil.copy(vocabdir / "myvocab.ttl", previous / "myvocab")
    # Test with a split vocabulary in previous-dir
    with caplog.at_level(logging.DEBUG):
        main_cli(["check", "-v", "--ci-post", str(previous), str(vocabdir)])
    assert "-> previous version is a split vocabulary" in caplog.text


def test_check_ci_pre_one_folder(tmp_path, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["check", "-v", "--ci-pre", str(tmp_path)])
    assert "Need two dirs for ci_pre!" in caplog.text


def test_check_ci_post_one_folder(tmp_path, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["check", "-v", "--ci-post", str(tmp_path)])
    assert "Need two dirs for ci_post!" in caplog.text
