import logging
import os
import shutil
from pathlib import Path
from unittest import mock

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


@mock.patch.dict(os.environ, clear=True)  # required to hide gh-action environment vars
def test_build_docs_pylode(datadir, tmp_path):
    """Check that pylode generates the expected output."""
    dst = tmp_path
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)
    outdir = tmp_path / "pylode"
    # To test the code-path, outdir is created automatically here.
    main_cli(["docs", "--style", "pylode", "--outdir", str(outdir), str(dst)])
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "index.html").exists()


@mock.patch.dict(os.environ, {"CI": "TRUE"})
def test_build_docs_pylode_ci_no_git(monkeypatch, datadir, tmp_path, caplog):
    """Check that pylode generates additional index.html in CI, git error."""
    dst = tmp_path
    monkeypatch.chdir(dst)
    shutil.copy(datadir / CS_CYCLES_TURTLE, dst)
    shutil.copy(datadir / "valid_idranges.toml", dst / "idranges.toml")
    outdir = dst / "pylode"

    with caplog.at_level(logging.ERROR), mock.patch(
        "voc4cat.gh_index.subprocess"
    ) as subprocess:
        subprocess.Popen.return_value.returncode = 1
        main_cli(
            ["docs", "--force", "--style", "pylode", "--outdir", str(outdir), str(dst)]
        )

    assert "git command returned with error" in caplog.text


@mock.patch.dict(os.environ, {"CI": "TRUE"})
def test_build_docs_pylode_ci_no_config(monkeypatch, datadir, tmp_path, caplog):
    """Check that pylode generates additional index.html in CI, git error."""
    dst = tmp_path
    monkeypatch.chdir(dst)
    shutil.copy(datadir / CS_CYCLES_TURTLE, dst)
    outdir = dst / "pylode"

    with caplog.at_level(logging.ERROR), pytest.raises(
        Voc4catError, match="Config file not found"
    ):
        main_cli(
            ["docs", "--force", "--style", "pylode", "--outdir", str(outdir), str(dst)]
        )

    assert "Config file not found" in caplog.text


@pytest.mark.parametrize("git_output", [b"v2022.12.22\n", b""])
@mock.patch.dict(os.environ, {"CI": "TRUE"})
def test_build_docs_pylode_in_ci(  # noqa: PLR0913
    fake_process, monkeypatch, datadir, tmp_path, caplog, git_output
):
    """Check that pylode generates additional index.html in CI."""
    dst = tmp_path
    monkeypatch.chdir(dst)
    shutil.copy(datadir / CS_CYCLES_TURTLE, dst)
    shutil.copy(datadir / "valid_idranges.toml", dst / "idranges.toml")
    outdir = dst / "pylode"
    # fake_process is a fixture from pytest-subprocess
    fake_process.register(
        ["git", "-C", ".", "tag", "--list", "v[0-9]*-[0-9]*-[0-9]*"],
        stdout=git_output,
    )

    with caplog.at_level(logging.DEBUG):
        main_cli(
            ["docs", "--force", "--style", "pylode", "--outdir", str(outdir), str(dst)]
        )
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "index.html").exists()
    assert (outdir / "index.html").exists()
    if git_output:
        assert "v2022.12.22" in caplog.text


@mock.patch.dict(os.environ, clear=True)  # required to hide gh-action environment vars
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
