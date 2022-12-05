# -*- coding: utf-8 -*-
import shutil
from unittest import mock

from test_wrapper import CS_CYCLES_TURTLE
from voc4cat.merge_vocab import main_cli


def test_main_no_args_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["merge_vocab"])
    exit_code = main_cli()
    captured = capsys.readouterr()
    assert "Usage: " in captured.out
    assert exit_code == 1


def test_main_no_args(capsys):
    exit_code = main_cli([])
    captured = capsys.readouterr()
    assert "Usage: " in captured.out
    assert exit_code == 1


def test_main_no_files(capsys):
    exit_code = main_cli(["aa", "bb"])
    captured = capsys.readouterr()
    assert 'This script requires both folders to exist: "aa" and "bb"' in captured.out
    assert exit_code == 1


def test_main_merge_dirs(datadir, tmp_path, capsys):
    """Check merge that only copies files."""
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    ttl_inbox = tmp_path / "ttl_inbox"
    ttl_inbox.mkdir()
    extra = ttl_inbox / "extra"
    extra.mkdir()
    shutil.copy(datadir / CS_CYCLES_TURTLE, ttl_inbox / CS_CYCLES_TURTLE)
    exit_code = main_cli([str(ttl_inbox), str(vocab)])
    captured = capsys.readouterr()
    assert f'Skipping "{extra}"' in captured.out
    assert (vocab / CS_CYCLES_TURTLE).exists()
    assert exit_code == 0


def test_main_merge_files(datadir, tmp_path, capsys):
    """Check merge that merges the content of files."""
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    ttl_inbox = tmp_path / "ttl_inbox"
    ttl_inbox.mkdir()
    new = ttl_inbox / CS_CYCLES_TURTLE
    shutil.copy(datadir / CS_CYCLES_TURTLE, new)
    exists = vocab / CS_CYCLES_TURTLE
    shutil.copy(datadir / CS_CYCLES_TURTLE, exists)
    exit_code = main_cli([str(ttl_inbox), str(vocab)])
    captured = capsys.readouterr()
    assert f"git merge-file --theirs {exists} {exists} {new}" in captured.out
    assert exit_code == 0

    with mock.patch("voc4cat.merge_vocab.subprocess") as subprocess:
        subprocess.Popen.return_value.returncode = 1
        exit_code = main_cli([str(ttl_inbox), str(vocab)])
    assert exit_code == 1
