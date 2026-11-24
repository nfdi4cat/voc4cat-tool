import logging
import os
import shutil
from unittest import mock

import pytest
from openpyxl import load_workbook

from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli, run_cli_app

CS_CYCLES = "concept-scheme-with-cycles.xlsx"
CS_CYCLES_TURTLE = "concept-scheme-with-cycles.ttl"


def test_run_cli_app_no_args_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["voc4cat"])
    run_cli_app()
    captured = capsys.readouterr()
    assert "usage: voc4cat" in captured.out


def test_run_cli_app_no_args(capsys):
    run_cli_app([])
    captured = capsys.readouterr()
    assert "usage: voc4cat" in captured.out


def test_main_unknown_arg(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main_cli(["--unknown-arg"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "voc4cat: error: unrecognized arguments: --unknown-arg" in captured.err


def test_main_version(capsys):
    main_cli(["--version"])
    captured = capsys.readouterr()
    assert captured.out.startswith("voc4cat")


def test_main_subcmd_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run_cli_app(["transform", "--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: voc4cat transform" in captured.out


# ===== Tests for common options of all subcommands =====


def test_unsupported_filetype(monkeypatch, datadir, caplog):
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.WARNING):
        main_cli(["transform", "README.md"])
    assert "Unsupported filetype:" in caplog.text


def test_nonexisting_file(monkeypatch, datadir, caplog):
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["transform", "missing.xyz"])
    assert "File/dir not found: missing.xyz" in caplog.text


def test_exit_errorvalue(monkeypatch, datadir, caplog):
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc_info:
        run_cli_app(["transform", "missing.xyz"])
    assert exc_info.value.code == 1
    assert "Terminating with error:" in caplog.text


def test_nonexisting_config(monkeypatch, datadir, caplog):
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["transform", "--config", "missing.toml", CS_CYCLES])
    assert "Config file not found at" in caplog.text


@mock.patch.dict(os.environ, {"LOGLEVEL": "DEBUG"})
def test_valid_config(
    monkeypatch, datadir, caplog, tmp_path, temp_config, cs_cycles_xlsx
):
    # Don't remove "temp_config". The fixture avoid global config change.
    shutil.copy(cs_cycles_xlsx, tmp_path / CS_CYCLES)
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.DEBUG):
        main_cli(
            [
                "transform",
                "--config",
                str(datadir / "valid_idranges.toml"),
                str(tmp_path / CS_CYCLES),
            ]
        )
    assert "Config loaded from" in caplog.text


def test_invalid_outdir(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(datadir)
    shutil.copy(datadir / "README.md", tmp_path)
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(
            Voc4catError, match=r"Outdir must be a directory but it is a file."
        ),
    ):
        main_cli(["transform", "--outdir", str(tmp_path / "README.md"), CS_CYCLES])
    assert "Outdir must be a directory but it is a file." in caplog.text


@pytest.mark.parametrize("command", ["check", "convert"])
@pytest.mark.parametrize(
    ("sheet", "edits", "field", "row"),
    [
        ("Concepts", {"D7": None}, "definition", 7),
        ("Concepts", {"C7": None}, "preferred_label", 7),
        ("Collections", {"D6": None}, "definition", 6),
        ("Mappings", {"B6": "ex:other"}, "concept_iri", 6),
    ],
    ids=[
        "concept definition",
        "concept label",
        "collection definition",
        "mapping concept",
    ],
)
def test_empty_required_cell_is_reported(
    datadir,
    tmp_path,
    caplog,
    temp_config,
    cs_cycles_xlsx,
    command,
    sheet,
    edits,
    field,
    row,
):
    """An empty required cell ends the command with an error naming sheet and row."""
    # Conversion needs the vocabulary's config for the concept scheme metadata.
    config = temp_config
    config.load_config(datadir / "valid_idranges.toml")
    config.IDRANGES.vocabs["concept-scheme-with-cycles"] = config.IDRANGES.vocabs.pop(
        "myvocab"
    )
    config.load_config(config=config.IDRANGES)
    xlsx = tmp_path / CS_CYCLES
    shutil.copy(cs_cycles_xlsx, xlsx)
    wb = load_workbook(xlsx)
    for cell, value in edits.items():
        wb[sheet][cell] = value
    wb.save(xlsx)
    wb.close()
    outdir = tmp_path / "out"
    outdir.mkdir()

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exc_info:
        run_cli_app([command, "--outdir", str(outdir), str(xlsx)])

    assert exc_info.value.code == 1
    assert "Unexpected error" not in caplog.text
    assert f'sheet "{sheet}"' in caplog.text
    assert f"Row {row}: Required field '{field}' is empty" in caplog.text
