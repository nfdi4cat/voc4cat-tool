import logging
import os
import shutil
from unittest import mock

import pytest
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli, run_cli_app

CS_SIMPLE = "concept-scheme-simple.xlsx"
CS_SIMPLE_TURTLE = "concept-scheme-simple.ttl"
CS_CYCLES = "concept-scheme-with-cycles.xlsx"
CS_CYCLES_TURTLE = "concept-scheme-with-cycles.ttl"
CS_CYCLES_INDENT = "concept-scheme-with-cycles_indent.xlsx"
CS_CYCLES_INDENT_IRI = "concept-scheme-with-cycles_indent_iri.xlsx"
CS_CYCLES_INDENT_DOT = "concept-scheme-with-cycles_indent-by-dot.xlsx"
CS_CYCLES_MULTI_LANG = "concept-scheme-with-cycles_multilang.xlsx"
CS_CYCLES_MULTI_LANG_IND = "concept-scheme-with-cycles_multilang_indent_iri.xlsx"


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
    assert exc_info.value.code == 2  # noqa: PLR2004
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
    assert "Terminating with Voc4cat error." in caplog.text


def test_nonexisting_config(monkeypatch, datadir, caplog):
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["transform", "--config", "missing.toml", CS_SIMPLE])
    assert "Config file not found at" in caplog.text


@mock.patch.dict(os.environ, {"LOGLEVEL": "DEBUG"})
def test_valid_config(monkeypatch, datadir, caplog, tmp_path, temp_config):
    # Don't remove "temp_config". The fixture avoid global config change.
    shutil.copy(datadir / CS_SIMPLE, tmp_path / CS_SIMPLE)
    monkeypatch.chdir(datadir)
    with caplog.at_level(logging.DEBUG):
        main_cli(
            [
                "transform",
                "--config",
                str(datadir / "valid_idranges.toml"),
                str(tmp_path / CS_SIMPLE),
            ]
        )
    assert "Config loaded from" in caplog.text


def test_invalid_outdir(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(datadir)
    shutil.copy(datadir / "README.md", tmp_path)
    with caplog.at_level(logging.ERROR), pytest.raises(
        Voc4catError, match="Outdir must be a directory but it is a file."
    ):
        main_cli(["transform", "--outdir", str(tmp_path / "README.md"), CS_SIMPLE])
    assert "Outdir must be a directory but it is a file." in caplog.text
