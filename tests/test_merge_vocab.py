import logging
import shutil
from unittest import mock

import pytest
from test_cli import CS_CYCLES_TURTLE, CS_SIMPLE_TURTLE
from voc4cat.merge_vocab import main_cli


def test_main_no_args_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["merge_vocab"])
    with pytest.raises(SystemExit):
        main_cli()
    captured = capsys.readouterr()
    assert "usage: merge_vocab" in captured.err
    assert "the following arguments are required" in captured.err


def test_main_no_args(capsys):
    with pytest.raises(SystemExit):
        main_cli([])
    captured = capsys.readouterr()
    assert "usage: merge_vocab" in captured.err


def test_main_no_files(caplog):
    with caplog.at_level(logging.ERROR):
        exit_code = main_cli(["aa", "bb"])
    assert 'This script requires both folders to exist: "aa" and "bb"' in caplog.text
    assert exit_code == 1


def test_main_merge_dirs(datadir, tmp_path, caplog):
    """Check merge that only copies files."""
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    ttl_inbox = tmp_path / "ttl_inbox"
    ttl_inbox.mkdir()
    extra = ttl_inbox / "extra.txt"
    extra.touch()
    splitvoc = ttl_inbox / "splitvoc"
    splitvoc.mkdir()

    shutil.copy(datadir / CS_CYCLES_TURTLE, ttl_inbox / CS_CYCLES_TURTLE)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, splitvoc)

    with caplog.at_level(logging.DEBUG):
        exit_code = main_cli([str(ttl_inbox), str(vocab)])
    assert f'Skipping "{extra}"' in caplog.text
    assert (vocab / CS_CYCLES_TURTLE).exists()
    assert (vocab / "splitvoc" / CS_SIMPLE_TURTLE).exists()
    assert exit_code == 0


def test_main_merge_split_vocab_dir(datadir, tmp_path, caplog):
    """Check merge of dir with split vocab."""
    vocab = tmp_path / "vocab"
    (vocab / "splitvoc").mkdir(parents=True)
    ttl_inbox = tmp_path / "ttl_inbox"
    (ttl_inbox / "splitvoc").mkdir(parents=True)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, ttl_inbox / "splitvoc")
    shutil.copy(datadir / CS_SIMPLE_TURTLE, vocab / "splitvoc")

    with caplog.at_level(logging.DEBUG), mock.patch(
        "voc4cat.merge_vocab.subprocess"
    ) as subprocess:
        subprocess.Popen.return_value.returncode = 1
        exit_code = main_cli([str(ttl_inbox), str(vocab)])
    assert "Entering directory" in caplog.text
    assert exit_code == 1


def test_main_merge_files(datadir, tmp_path, caplog):
    """Check merge that merges the content of files."""
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    logf = vocab / "test.log"
    ttl_inbox = tmp_path / "ttl_inbox"
    ttl_inbox.mkdir()
    new = ttl_inbox / CS_CYCLES_TURTLE
    shutil.copy(datadir / CS_CYCLES_TURTLE, new)
    exists = vocab / CS_CYCLES_TURTLE
    shutil.copy(datadir / CS_CYCLES_TURTLE, exists)

    with caplog.at_level(logging.INFO):
        exit_code = main_cli(["--logfile", str(logf), str(ttl_inbox), str(vocab)])
    assert f"git merge-file --theirs {exists} {exists} {new}" in caplog.text
    assert exit_code == 0
    assert logf.exists()

    with mock.patch("voc4cat.merge_vocab.subprocess") as subprocess:
        subprocess.Popen.return_value.returncode = 1
        exit_code = main_cli(["--logfile", str(logf), str(ttl_inbox), str(vocab)])
    assert exit_code == 1
