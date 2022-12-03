# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path

import pytest
from openpyxl.reader.excel import load_workbook

from voc4cat.wrapper import main_cli

CS_CYCLES = "concept-scheme-with-cycles.xlsx"
CS_CYCLES_TURTLE = "concept-scheme-with-cycles.ttl"
CS_CYCLES_INDENT = "concept-scheme-with-cycles_indent.xlsx"
CS_CYCLES_INDENT_IRI = "concept-scheme-with-cycles_indent_iri.xlsx"


# @pytest.fixture()
# def cs_cycles_workbook(datadir):
#     """Open test-xlsx  with children-IRI-based hierarchy."""
#     os.chdir(datadir)
#     wb = load_workbook(filename=CS_CYCLES, read_only=True, data_only=True)
#     return wb


def test_main_no_args_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["voc4at"])
    exit_code = main_cli()
    captured = capsys.readouterr()
    assert "usage: voc4cat" in captured.out
    assert exit_code == 0


def test_main_no_args(capsys):
    exit_code = main_cli([])
    captured = capsys.readouterr()
    assert "usage: voc4cat" in captured.out
    assert exit_code == 0


def test_main_version(capsys):
    exit_code = main_cli(["--version"])
    captured = capsys.readouterr()
    assert captured.out.startswith("voc4cat")
    assert exit_code == 0


def test_add_IRI(datadir, tmp_path):
    expected = [
        ("ex:test/term1", "term1"),
        ("ex:test/term3", "term3"),
        ("ex:test/term4", "term4"),
        ("ex:test/term2", "term2"),
        ("ex:test/term4", "term4"),
        ("ex:test/term1", "term1"),
        ("ex:test/term2", "term2"),
    ]
    os.chdir(datadir)
    shutil.copy(CS_CYCLES_INDENT, tmp_path / CS_CYCLES_INDENT)
    os.chdir(tmp_path)

    # Try to run a command that would overwrite the input file with the output file
    with pytest.warns(
        UserWarning, match='Option "add_IRI" will overwrite the existing file'
    ):
        main_cli(
            [
                "--add_IRI",
                str(tmp_path),
            ]
        )
    # Now overwrite the file explicitly.
    main_cli(
        [
            "--add_IRI",
            "--no-warn",
            str(tmp_path),
        ]
    )
    os.chdir(tmp_path)
    wb = load_workbook(filename=CS_CYCLES_INDENT, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=2, values_only=True), expected
    ):
        assert row == expected_row


def test_hierarchy_from_indent(datadir, tmp_path):
    # fmt: off
    expected = [  # data in children-IRI-representation
        ('ex:test/term1', 'term1', 'en', 'def for term1', 'en', 'AltLbl for term1', 'ex:test/term2, ex:test/term3', 'Prov for term1', 'ex:XYZ/term1'),  # noqa:E501
        ('ex:test/term2', 'term2', 'en', 'def for term2', 'en', 'AltLbl for term2', 'ex:test/term4',                'Prov for term2', 'ex:XYZ/term2'),  # noqa:E501
        ('ex:test/term3', 'term3', 'en', 'def for term3', 'en', 'AltLbl for term3', 'ex:test/term4',                'Prov for term3', 'ex:XYZ/term3'),  # noqa:E501
        ('ex:test/term4', 'term4', 'en', 'def for term4', 'en', 'AltLbl for term4', None,                           'Prov for term4', 'ex:XYZ/term4'),  # noqa:E501
        (None, None, None, None, None, None, None, None, None)
    ]
    # fmt: on
    expected_len = len(expected[0])
    os.chdir(datadir)
    main_cli(
        [
            "--hierarchy-from-indent",
            "--output_directory",
            str(tmp_path),
            CS_CYCLES_INDENT_IRI,
        ]
    )
    os.chdir(tmp_path)
    wb = load_workbook(filename=CS_CYCLES_INDENT_IRI, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(ws.iter_rows(min_row=3, values_only=True), expected):
        assert len(row) == expected_len
        assert row in expected  # We intentionally don't check the row position here!


def test_hierarchy_to_indent(datadir, tmp_path):
    # fmt: off
    expected = [  # data in children-IRI-representation
        ('ex:test/term1', 'term1',     'en', 'def for term1', 'en', 'AltLbl for term1', None, 'Prov for term1', 'ex:XYZ/term1'),  # noqa:E501
        ('ex:test/term3', '..term3',   'en', 'def for term3', 'en', 'AltLbl for term3', None, 'Prov for term3', 'ex:XYZ/term2'),  # noqa:E501
        ('ex:test/term4', '....term4', 'en', 'def for term4', 'en', 'AltLbl for term4', None, 'Prov for term4', 'ex:XYZ/term3'),  # noqa:E501
        ('ex:test/term2', 'term2',     'en', 'def for term2', 'en', 'AltLbl for term2', None, 'Prov for term2', 'ex:XYZ/term4'),  # noqa:E501
        ('ex:test/term4', '..term4',   'en', None, None, None, None, None, None),
        ('ex:test/term1', 'term1',     'en', None, None, None, None, None, None),
        ('ex:test/term2', '..term2',   'en', None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None, None),
    ]
    # fmt: on
    expected_len = len(expected[0])
    os.chdir(datadir)
    main_cli(
        [
            "--hierarchy-to-indent",
            "--indent-separator",
            "..",
            "--output_directory",
            str(tmp_path),
            CS_CYCLES,
        ]
    )
    os.chdir(tmp_path)
    wb = load_workbook(filename=CS_CYCLES, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(ws.iter_rows(min_row=3, values_only=True), expected):
        assert len(row) == expected_len
        assert row == expected_row


def test_run_ontospy(datadir, tmp_path):
    """Check that ontospy generates the expected output."""
    dst = tmp_path / CS_CYCLES_TURTLE
    shutil.copy(datadir / CS_CYCLES_TURTLE, dst)
    outdir = tmp_path / "ontospy"
    # To test the code-path, outdir is created automatically here.
    main_cli(["--docs", "--output_directory", str(outdir), str(dst)])
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "dendro" / "index.html").exists()
    assert (outdir / Path(CS_CYCLES_TURTLE).stem / "docs" / "index.html").exists()


@pytest.mark.parametrize(
    "test_file,err,msg",
    [
        (CS_CYCLES, 0, "All checks passed successfully."),
        (
            CS_CYCLES_INDENT_IRI,
            1,
            'ERROR: Same Concept IRI "ex:test/term1"'
            ' used more than once for language "en"',
        ),
    ],
    ids=["no error", "with error"],
)
def test_check(datadir, tmp_path, capsys, test_file, err, msg):
    dst = tmp_path / test_file
    shutil.copy(datadir / test_file, dst)
    exit_code = main_cli(["--check", "--no-warn", str(dst)])
    captured = capsys.readouterr()
    # TODO check that erroneous cells get colored.
    assert exit_code == err
    assert msg in captured.out


def test_unsupported_filetype(datadir, capsys):
    os.chdir(datadir)
    exit_code = main_cli(["README.md"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Files for processing must end with" in captured.out


def test_nonexisting_file(datadir, capsys):
    os.chdir(datadir)
    exit_code = main_cli(["missing.txt"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "File not found:" in captured.out


@pytest.mark.parametrize(
    "test_file",
    [CS_CYCLES, ""],
    ids=["single file", "dir of files"],
)
def test_run_vocexcel(datadir, tmp_path, test_file):
    """Check that an xlsx file is converted to ttl by vocexcel."""
    dst = tmp_path / test_file
    shutil.copy(datadir / CS_CYCLES, dst)
    # We also test if the logging option is passed on to vocexcel.
    log = tmp_path / "logs" / "test-run.log"
    main_cli(["--logfile", str(log), str(dst)])
    expected = (tmp_path / CS_CYCLES).with_suffix(".ttl")
    assert expected.exists()
    assert log.exists()


@pytest.mark.parametrize(
    "test_file",
    [CS_CYCLES, ""],
    ids=["single file", "dir of files"],
)
def test_forwarding(datadir, tmp_path, test_file):
    """Check a file by voc4cat then forward it to vocexcel then to ontospy."""
    dst = tmp_path / test_file
    shutil.copy(datadir / CS_CYCLES, dst)
    os.chdir(tmp_path)
    main_cli(
        [
            "--check",
            "--forward",
            "--logfile",
            "test.log",
            "--no-warn",
            "--docs",
            str(dst),
        ]
    )
    assert (tmp_path / CS_CYCLES).with_suffix(".ttl").exists()
    assert (tmp_path / Path(CS_CYCLES).stem / "dendro" / "index.html").exists()
    assert (tmp_path / Path(CS_CYCLES).stem / "docs" / "index.html").exists()
    assert (tmp_path / "test.log").exists()
