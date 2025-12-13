import logging
import shutil
from pathlib import Path

import pytest

from tests.test_cli import (
    CS_CYCLES,
    CS_CYCLES_TURTLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli


@pytest.mark.parametrize(
    ("outputdir", "testfile"),
    [
        ("out", CS_CYCLES_TURTLE),
        ("", CS_CYCLES_TURTLE),
    ],
    ids=["out:dir & ttl", "out:default & ttl"],
)
def test_run_voc4cat_outputdir(
    monkeypatch, datadir, tmp_path, outputdir, testfile, temp_config
):
    """Check that an xlsx file is converted to ttl by voc4cat."""
    shutil.copy(datadir / testfile, tmp_path)
    monkeypatch.chdir(tmp_path)

    # Load/prepare an a config with required prefix definition
    config = temp_config
    vocab_name = testfile.split(".")[0]
    config.CURIES_CONVERTER_MAP[vocab_name] = config.curies_converter

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
    """Check template option error handling."""
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
