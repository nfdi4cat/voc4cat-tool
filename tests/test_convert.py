import logging
import shutil
from pathlib import Path

import pytest
import voc4cat
from test_cli import (
    CS_CYCLES,
    CS_CYCLES_TURTLE,
    CS_SIMPLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli


@pytest.mark.parametrize(
    "test_file",
    [CS_SIMPLE, ""],
    ids=["single file", "dir of files"],
)
def test_run_vocexcel(datadir, tmp_path, test_file):
    """Check that an xlsx file is converted to ttl by vocexcel."""
    dst = tmp_path / test_file
    shutil.copy(datadir / CS_SIMPLE, dst)
    # We also test if the logging option works.
    log = tmp_path / "logs" / "test-run.log"
    main_cli(["convert", "-v", "--logfile", str(log), str(dst)])
    expected = (tmp_path / CS_SIMPLE).with_suffix(".ttl")
    assert expected.exists()
    assert log.exists()


@pytest.mark.parametrize(
    ("outputdir", "testfile"),
    [
        ("out", CS_CYCLES),
        ("", CS_CYCLES),
        ("out", CS_CYCLES_TURTLE),
        ("", CS_CYCLES_TURTLE),
    ],
    ids=["out:dir & xlsx", "out:default & xlsx", "out:dir & ttl", "out:default & ttl"],
)
def test_run_vocexcel_outputdir(monkeypatch, datadir, tmp_path, outputdir, testfile):
    """Check that an xlsx file is converted to ttl by vocexcel."""
    shutil.copy(datadir / testfile, tmp_path)
    monkeypatch.chdir(tmp_path)
    # Check if log is placed in out folder.
    log = Path(outputdir) / "test-run.log"
    main_cli(
        ["convert", "--logfile", str(log)]
        + (["--outdir", str(outputdir)] if outputdir else [])
        + [str(tmp_path)]
    )
    outdir = tmp_path / outputdir
    if testfile.endswith("xlsx"):
        assert (outdir / testfile).with_suffix(".ttl").exists()
    else:
        assert (outdir / testfile).with_suffix(".xlsx").exists()
    assert (outdir / log.name).exists()


def test_duplicates(datadir, tmp_path, caplog):
    """Check that files do not have the same stem."""
    shutil.copy(datadir / CS_CYCLES, tmp_path)
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["convert", str(tmp_path)])
    assert "Files may only be present in one format." in caplog.text


def test_template(monkeypatch, datadir, tmp_path, caplog):
    """Check template option."""
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["convert", "--template", "missing.xlsx", str(tmp_path)])
    assert "Template file not found: " in caplog.text

    caplog.clear()
    Path(tmp_path / "template.txt").touch()
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["convert", "--template", "template.txt", str(tmp_path)])
    assert 'Template file must be of type ".xlsx".' in caplog.text

    caplog.clear()
    std_template = str(Path(voc4cat.__file__).parent / "blank_043.xlsx")
    with caplog.at_level(logging.INFO):
        main_cli(["convert", "-v", "--template", std_template, str(tmp_path)])
    assert "->" in caplog.text
