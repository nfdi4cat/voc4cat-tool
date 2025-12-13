import logging
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

from tests.test_cli import (
    CS_CYCLES,
    CS_SIMPLE_TURTLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli
from voc4cat.utils import ConversionError


@pytest.mark.parametrize(
    ("test_file", "msg"),
    [
        (CS_CYCLES, "xlsx check passed"),
    ],
    ids=["no error"],
)
def test_check_xlsx(datadir, tmp_path, caplog, test_file, msg):
    dst = tmp_path / test_file
    shutil.copy(datadir / test_file, dst)
    with caplog.at_level(logging.INFO):
        main_cli(["check", "--inplace", str(dst)])
    assert msg in caplog.text


def test_check_xlsx_with_cell_coloring(datadir, tmp_path, caplog):
    """Test that erroneous cells get colored when duplicates are found."""
    test_file = "concept-scheme-duplicates.xlsx"
    dst = tmp_path / test_file
    shutil.copy(datadir / test_file, dst)

    with caplog.at_level(logging.ERROR):
        main_cli(["check", "--inplace", str(dst)])

    # Check that the error was logged
    assert (
        'Same Concept IRI "ex:test01" used more than once for language "en"'
        in caplog.text
    )

    # Check that cells were colored orange
    wb = load_workbook(dst)
    ws = wb["Concepts"]

    # Expected orange color from check.py: PatternFill("solid", start_color="00FFCC00")
    expected_color = "00FFCC00"

    # Check that the duplicate concept IRI cells are colored (rows 3 and 4, columns A and C)
    assert ws["A3"].fill.start_color.rgb == expected_color, (
        "First duplicate IRI cell should be colored orange"
    )
    assert ws["C3"].fill.start_color.rgb == expected_color, (
        "First duplicate language cell should be colored orange"
    )
    assert ws["A4"].fill.start_color.rgb == expected_color, (
        "Second duplicate IRI cell should be colored orange"
    )
    assert ws["C4"].fill.start_color.rgb == expected_color, (
        "Second duplicate language cell should be colored orange"
    )

    wb.close()


def test_check_skos_rdf(datadir, tmp_path, caplog):
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    with caplog.at_level(logging.INFO):
        main_cli(["check", str(tmp_path / CS_SIMPLE_TURTLE)])
    assert "The file is valid according to the vocpub profile." in caplog.text


def test_check_skos_badfile(monkeypatch, datadir, tmp_path, temp_config, caplog):
    """Check failing profile validation."""
    # Load/prepare an a config with required prefix definition
    config = temp_config
    vocab_name = "concept-scheme-badfile"
    config.CURIES_CONVERTER_MAP[vocab_name] = config.curies_converter
    with caplog.at_level(logging.ERROR), pytest.raises(ConversionError):
        main_cli(["check", str(Path(datadir / vocab_name).with_suffix(".ttl"))])
    assert "VIOLATION: Validation Result in MinCountConstraintComponent" in caplog.text


def test_check_list_profiles(capsys):
    main_cli(["check", "--listprofiles"])
    captured = capsys.readouterr()
    assert "Known profiles:" in captured.out
    assert "builtin\tvocpub" in captured.out


def test_check_list_profiles_with_config(datadir, capsys, temp_config):
    """Test --listprofiles shows custom profiles when config is provided."""
    main_cli(
        [
            "check",
            "--config",
            str(datadir / "idranges_with_scheme.toml"),
            "--listprofiles",
        ]
    )
    captured = capsys.readouterr()
    assert "Known profiles:" in captured.out
    assert "builtin\tvocpub" in captured.out
    assert "config\tmyvocab" in captured.out
    assert "custom_profile.ttl" in captured.out


def test_check_missing_vocab(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main_cli(["check"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "usage: voc4cat check" in captured.out
    assert "--listprofiles" in captured.out


def test_check_ci_pre_one_folder(tmp_path, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["check", "-v", "--ci-pre", str(tmp_path)])
    assert "Need two dirs for ci_pre!" in caplog.text


def test_check_ci_post_one_folder(tmp_path, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["check", "-v", "--ci-post", str(tmp_path)])
    assert "Need two dirs for ci_post!" in caplog.text
