import logging
import shutil
from pathlib import Path

import pytest
from test_cli import (
    CS_CYCLES_TURTLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli


@pytest.mark.parametrize(
    "test_file",
    [CS_CYCLES_TURTLE, ""],
    ids=["single file", "dir of files"],
)
def test_build_docs_ontospy(datadir, tmp_path, test_file):
    """Check that ontospy generates the expected output."""
    dst = tmp_path / test_file
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)
    outdir = tmp_path / "ontospy"
    # To test the code-path, outdir is created automatically here.
    main_cli(["docs", "--style", "ontospy", "--outdir", str(outdir), str(dst)])
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "dendro" / "index.html").exists()
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "docs" / "index.html").exists()


def test_build_docs_pylode(datadir, tmp_path):
    """Check that pylode generates the expected output."""
    dst = tmp_path
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)
    outdir = tmp_path / "pylode"
    # To test the code-path, outdir is created automatically here.
    main_cli(["docs", "--style", "pylode", "--outdir", str(outdir), str(dst)])
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "index.html").exists()


def test_build_docs(datadir, tmp_path, caplog):
    """Check overwrite warning and output folder creation."""
    dst = tmp_path
    outdir = tmp_path / "new"

    # existing non-empty output folder
    outdir.mkdir()
    shutil.copy(datadir / CS_CYCLES_TURTLE, outdir)
    shutil.copy(datadir / CS_CYCLES_TURTLE, dst)
    with caplog.at_level(logging.WARNING):
        main_cli(["docs", "--style", "pylode", "--outdir", str(outdir), str(dst)])
    assert (
        f'The folder "{outdir}" is not empty. Use "--force" to write to the folder anyway.'
        in caplog.text
    )
    # force use of existing non-empty output folder
    main_cli(
        ["docs", "--style", "pylode", "--force", "--outdir", str(outdir), str(dst)]
    )
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "index.html").exists()


def test_build_docs_no_input(tmp_path, caplog):
    """Check handling of of missing file or empty dir in documentation build."""
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["docs", "--outdir", str(tmp_path), str(tmp_path / CS_CYCLES_TURTLE)])
    assert f"File/dir not found: {tmp_path/CS_CYCLES_TURTLE}" in caplog.text

    with caplog.at_level(logging.INFO):
        main_cli(["docs", "--outdir", str(tmp_path), str(tmp_path)])
    assert "Nothing to do. No turtle file" in caplog.text


def test_build_docs_unknown_builder(tmp_path, caplog, capsys):
    """Check handling of unknown documentation builder."""
    unknown_doc_builder = "123doc"
    with pytest.raises(SystemExit) as exc_info:
        main_cli(
            [
                "docs",
                "--style",
                unknown_doc_builder,
                str(tmp_path),
                str(tmp_path / CS_CYCLES_TURTLE),
            ]
        )
    assert exc_info.value.code == 2  # noqa: PLR2004
    captured = capsys.readouterr()
    assert f"invalid choice: '{unknown_doc_builder}'" in captured.err
