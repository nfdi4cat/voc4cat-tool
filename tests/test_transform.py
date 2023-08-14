import logging
import os
import shutil
from unittest import mock

import pytest
from openpyxl import load_workbook
from rdflib import Graph, Literal
from rdflib.namespace import DCTERMS, OWL, SKOS, XSD
from test_cli import (
    CS_CYCLES,
    CS_CYCLES_INDENT_DOT,
    CS_CYCLES_INDENT_IRI,
    CS_CYCLES_MULTI_LANG,
    CS_CYCLES_MULTI_LANG_IND,
    CS_SIMPLE,
    CS_SIMPLE_TURTLE,
)
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli

# ===== Tests for no option set =====


def test_transform_no_option(monkeypatch, datadir, tmp_path, caplog):
    shutil.copy(datadir / CS_SIMPLE, tmp_path / CS_SIMPLE)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", str(tmp_path)])
    assert "nothing to do for xlsx files" in caplog.text

    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path / CS_SIMPLE_TURTLE)
    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", str(tmp_path)])
    assert "nothing to do for rdf files" in caplog.text


def test_transform_unsupported_filetype(monkeypatch, datadir, tmp_path, caplog):
    shutil.copy(datadir / "README.md", tmp_path)
    monkeypatch.chdir(tmp_path)
    # Try to run a command that would overwrite the input file with the output file
    with caplog.at_level(logging.WARNING):
        main_cli(["transform", str(tmp_path / "README.md")])
    assert "Unsupported filetype: " in caplog.text


# ===== Tests for option --make-ids =====


def test_make_ids_missing_file(caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["transform", "--make-ids", "ex", "1", "missing.xyz"])
    assert "File/dir not found: missing.xyz" in caplog.text


def test_make_ids_overwrite_warning(monkeypatch, datadir, tmp_path, caplog):
    shutil.copy(datadir / CS_SIMPLE, tmp_path / CS_SIMPLE)
    monkeypatch.chdir(tmp_path)
    # Try to run a command that would overwrite the input file with the output file
    # a) dir as input:
    with caplog.at_level(logging.WARNING):
        main_cli(["transform", "--make-ids", "ex", "1", str(tmp_path)])
    assert "This command will overwrite the existing file" in caplog.text
    # b) file as input
    with caplog.at_level(logging.WARNING):
        main_cli(["transform", "--make-ids", "ex", "1", str(tmp_path / CS_SIMPLE)])
    assert "This command will overwrite the existing file" in caplog.text


def test_make_ids_no_voc_base_iri(monkeypatch, datadir, tmp_path):
    shutil.copy(datadir / CS_SIMPLE, tmp_path)
    monkeypatch.chdir(tmp_path)
    # change excel file: Delete vocabulary base IRI
    wb = load_workbook(filename=CS_SIMPLE)
    ws = wb["Concept Scheme"]
    ws.cell(row=2, column=2).value = None
    new_filename = "no_voc_base_iri.xlsx"
    wb.save(new_filename)
    wb.close()

    main_cli(
        [
            "transform",
            "--make-ids",
            "na",
            "1001",
            "--inplace",
            str(tmp_path / new_filename),
        ]
    )
    wb = load_workbook(filename=new_filename, read_only=True, data_only=True)
    ws = wb["Concept Scheme"]
    assert ws.cell(row=2, column=2).value == "https://example.org/"


def test_make_ids_invalid_id(datadir):
    with pytest.raises(
        Voc4catError,
        match="Start ID must be an integer number.",
    ):
        main_cli(
            [
                "transform",
                "--make-ids",
                "ex",
                "###",
                "--inplace",
                str(datadir / CS_SIMPLE),
            ]
        )


def test_make_ids_invalid_negative_id(datadir):
    with pytest.raises(
        Voc4catError,
        match="Start ID must be greater than zero.",
    ):
        main_cli(
            [
                "transform",
                "--make-ids",
                "ex",
                "-1",
                "--inplace",
                str(datadir / CS_SIMPLE),
            ]
        )


def test_make_ids_invalid_base_iri(datadir):
    with pytest.raises(
        Voc4catError,
        match='The base_iri must be in IRI-form and start with "http".',
    ):
        main_cli(
            [
                "transform",
                "--make-ids",
                "ex:ftp://example.org",
                "1",
                "--inplace",
                str(datadir / CS_SIMPLE),
            ]
        )


@pytest.mark.parametrize(
    ("indir", "outdir"),
    [(True, ""), (True, "out"), (False, ""), (False, "out")],
    ids=[
        "in:dir, out:default",
        "in:dir, out:dir",
        "in:file, out:default",
        "in:file, out:dir",
    ],
)
def test_make_ids_variants(monkeypatch, datadir, tmp_path, indir, outdir):
    # fmt: off
    expected_concepts = [
        ("ex:test/0001001", "term1", "en", "def for term1", "en", "AltLbl for term1", "ex:test/0001002, ex:test/0001003",),
        ("ex:test/0001002", "term2", "en", "def for term2", "en", "AltLbl for term2", None,),
        ("ex:test/0001003", "term3", "en", "def for term3", "en", "AltLbl for term3", "ex:test/0001004",),
        ("ex:test/0001004", "term4", "en", "def for term4", "en", "AltLbl for term4", None, ),
        ("ex:test/0001005", "term5", "en", "def for term5", "en", "AltLbl for term5", None, ),
        ("ex:test/0001006", "term6", "en", "def for term6", "en", "AltLbl for term6", None,),
    ]
    expected_collections = [
        ("ex:test/0001007", "con", "def for con", "ex:test/0001001, ex:test/0001002, ex:test/0001003, ex:test/0001004",),
    ]
    expected_additional = [
        ("ex:test/0001001", "ex:test/0001002", "ex:test/0001003", "ex:test/0001004", "ex:test/0001005", "ex:test/0001006", ),
    ]
    # fmt: on
    shutil.copy(datadir / CS_SIMPLE, tmp_path)
    monkeypatch.chdir(tmp_path)
    main_cli(
        ["transform", "--make-ids", "ex", "1001", "--inplace"]
        + (["--outdir", outdir] if outdir else [])
        + ([str(tmp_path)] if indir else [str(tmp_path / CS_SIMPLE)])
    )
    xlsxfile = tmp_path / outdir / CS_SIMPLE if outdir else tmp_path / CS_SIMPLE
    wb = load_workbook(filename=xlsxfile, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=7, values_only=True), expected_concepts
    ):
        assert row == expected_row
    ws = wb["Collections"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=4, values_only=True), expected_collections
    ):
        assert row == expected_row
    ws = wb["Additional Concept Features"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=6, values_only=True), expected_additional
    ):
        assert row == expected_row


def test_make_ids_base_iri(monkeypatch, datadir, tmp_path):
    # fmt: off
    expected_concepts = [
        ("https://example.com/new_0001001", "term1", "en", "def for term1", "en", "AltLbl for term1", "https://example.com/new_0001002, https://example.com/new_0001003",),
        ("https://example.com/new_0001002", "term2", "en", "def for term2", "en", "AltLbl for term2", None,),
        ("https://example.com/new_0001003", "term3", "en", "def for term3", "en", "AltLbl for term3", "https://example.com/new_0001004",),
        ("https://example.com/new_0001004", "term4", "en", "def for term4", "en", "AltLbl for term4", None, ),
        ("https://example.com/new_0001005", "term5", "en", "def for term5", "en", "AltLbl for term5", None, ),
        ("https://example.com/new_0001006", "term6", "en", "def for term6", "en", "AltLbl for term6", None,),
    ]
    expected_collections = [
        ("https://example.com/new_0001007", "con", "def for con", "https://example.com/new_0001001, https://example.com/new_0001002, https://example.com/new_0001003, https://example.com/new_0001004",),
    ]
    expected_additional = [
        ("https://example.com/new_0001001", "https://example.com/new_0001002", "https://example.com/new_0001003", "https://example.com/new_0001004", "https://example.com/new_0001005", "https://example.com/new_0001006", ),
    ]
    # fmt: on
    shutil.copy(datadir / CS_SIMPLE, tmp_path)
    monkeypatch.chdir(tmp_path)
    main_cli(
        [
            "transform",
            "--make-ids",
            "ex:https://example.com/new_",
            "1001",
            "--inplace",
            str(tmp_path / CS_SIMPLE),
        ]
    )
    xlsxfile = tmp_path / CS_SIMPLE
    wb = load_workbook(filename=xlsxfile, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=7, values_only=True), expected_concepts
    ):
        assert row == expected_row
    ws = wb["Collections"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=4, values_only=True), expected_collections
    ):
        assert row == expected_row
    ws = wb["Additional Concept Features"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=6, values_only=True), expected_additional
    ):
        assert row == expected_row


def test_make_ids_multilang(tmp_path, datadir):
    # fmt: off
    expected_concepts = [
        ("ex:test/0001001", "term1", "en", "def for term1", "en", "AltLbl for term1", "ex:test/0001002, ex:test/0001003",),
        ("ex:test/0001002", "term2", "en", "def for term2", "en", "AltLbl for term2", "ex:test/0001004",),
        ("ex:test/0001003", "term3", "en", "def for term3", "en", "AltLbl for term3", "ex:test/0001004",),
        ("ex:test/0001004", "term4", "en", "def for term4", "en", "AltLbl for term4", None, ),
        ("ex:test/0001004", "Begr4", "de", "Def für Begr4", "de", "AltLbl für Begr4", None, ),
        ("ex:test/0001001", "Begr1", "de", "Def für Begr1", "de", "AltLbl für Begr1", None, ),
    ]
    # fmt: on
    main_cli(
        [
            "transform",
            "--make-ids",
            "ex",
            "1001",
            "--outdir",
            str(tmp_path),
            str(datadir / CS_CYCLES_MULTI_LANG),
        ]
    )
    xlsxfile = tmp_path / CS_CYCLES_MULTI_LANG
    wb = load_workbook(filename=xlsxfile, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=7, values_only=True), expected_concepts
    ):
        assert row == expected_row


# ===== Tests for option --from-indent / --to-indent =====


@pytest.mark.parametrize(
    "option",
    ["--from-indent", "--to-indent"],
)
def test_no_separator(monkeypatch, datadir, option):
    monkeypatch.chdir(datadir)
    with pytest.raises(
        Voc4catError,
        match="Setting the indent separator to zero length is not allowed.",
    ):
        main_cli(["transform", option, "--indent", "", CS_CYCLES])


# ===== Tests for option --from-indent =====


def test_hierarchy_from_indent_on_dir(tmp_path, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["transform", "--from-indent", str(tmp_path / "missing.xlsx")])
    assert "File/dir not found:" in caplog.text


@pytest.mark.parametrize(
    ("xlsxfile", "indent"),
    [(CS_CYCLES_INDENT_IRI, None), (CS_CYCLES_INDENT_DOT, "..")],
    ids=["indent:Excel", "indent:dots"],
)
def test_hierarchy_from_indent(monkeypatch, datadir, tmp_path, xlsxfile, indent):
    # fmt: off
    expected = [  # data in children-IRI-representation
        ("ex:test/term1", "term1", "en", "def for term1", "en", "AltLbl for term1", "ex:test/term2, ex:test/term3", "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term2", "term2", "en", "def for term2", "en", "AltLbl for term2", "ex:test/term4",                "Prov for term2", "ex:XYZ/term2"),
        ("ex:test/term3", "term3", "en", "def for term3", "en", "AltLbl for term3", "ex:test/term4",                "Prov for term3", "ex:XYZ/term3"),
        ("ex:test/term4", "term4", "en", "def for term4", "en", "AltLbl for term4", None,                           "Prov for term4", "ex:XYZ/term4"),
        (None, None, None, None, None, None, None, None, None)
    ]
    # fmt: on
    expected_len = len(expected[0])
    monkeypatch.chdir(datadir)
    main_cli(
        ["transform", "--from-indent"]
        + (
            [
                "--indent",
                indent,
            ]
            if indent
            else []
        )
        + [
            "--outdir",
            str(tmp_path),
            xlsxfile,
        ]
    )
    monkeypatch.chdir(tmp_path)
    wb = load_workbook(filename=xlsxfile, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, _expected_row in zip(ws.iter_rows(min_row=3, values_only=True), expected):
        assert len(row) == expected_len
        assert row in expected  # We intentionally don't check the row position here!


def test_hierarchy_from_indent_multilang(monkeypatch, datadir, tmp_path):
    # fmt: off
    expected = [  # data in children-IRI-representation
        ("ex:test/term1", "term1", "en", "def for term1", "en", "AltLbl for term1", "ex:test/term2, ex:test/term3", "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term1", "Begr1", "de", "Def für Begr1", "de", "AltLbl für Begr1", "ex:test/term2, ex:test/term3", "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term2", "term2", "en", "def for term2", "en", "AltLbl for term2", "ex:test/term4", "Prov for term2", "ex:XYZ/term2"),
        ("ex:test/term3", "term3", "en", "def for term3", "en", "AltLbl for term3", "ex:test/term4", "Prov for term3", "ex:XYZ/term3"),
        ("ex:test/term4", "term4", "en", "def for term4", "en", "AltLbl for term4", None,            "Prov for term4", "ex:XYZ/term4"),
        ("ex:test/term4", "Begr4", "de", "Def für Begr4", "de", "AltLbl für Begr4", None,            "Prov for term4", "ex:XYZ/term4"),
        (None, None, None, None, None, None, None, None, None)
    ]
    # fmt: on
    expected_len = len(expected[0])
    monkeypatch.chdir(datadir)
    main_cli(
        [
            "transform",
            "--from-indent",
            "--outdir",
            str(tmp_path),
            CS_CYCLES_MULTI_LANG_IND,
        ]
    )
    monkeypatch.chdir(tmp_path)
    wb = load_workbook(
        filename=CS_CYCLES_MULTI_LANG_IND, read_only=True, data_only=True
    )
    ws = wb["Concepts"]
    for row, _expected_row in zip(ws.iter_rows(min_row=3, values_only=True), expected):
        assert len(row) == expected_len
        assert row in expected  # We intentionally don't check the row position here!


def test_hierarchy_from_indent_merge(monkeypatch, datadir, tmp_path):
    shutil.copy(datadir / CS_CYCLES_INDENT_IRI, tmp_path)
    monkeypatch.chdir(tmp_path)
    # change excel file: Delete vocabulary base IRI
    wb = load_workbook(filename=CS_CYCLES_INDENT_IRI)
    ws = wb["Concepts"]
    ws.cell(row=8, column=4).value = "Contradicting def."
    iri = ws.cell(row=8, column=1).value
    new_filename = "indent_merge_problem.xlsx"
    wb.save(new_filename)
    wb.close()
    with pytest.raises(
        Voc4catError,
        match=f"Cannot merge rows for {iri}. Resolve differences manually.",
    ):
        main_cli(
            ["transform", "--from-indent", "--inplace", str(tmp_path / new_filename)]
        )


# ===== Tests for option --to-indent =====


@pytest.mark.parametrize(
    "indent",
    ["..", None],
    ids=["indent:dots", "indent:Excel"],
)
def test_hierarchy_to_indent(monkeypatch, datadir, tmp_path, indent):
    # fmt: off
    expected_rows = [  # data in children-IRI-representation
        ("ex:test/term1", "term1",     "en", "def for term1", "en", "AltLbl for term1", None, "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term3", "..term3",   "en", "def for term3", "en", "AltLbl for term3", None, "Prov for term3", "ex:XYZ/term3"),
        ("ex:test/term4", "....term4", "en", "def for term4", "en", "AltLbl for term4", None, "Prov for term4", "ex:XYZ/term4"),
        ("ex:test/term2", "term2",     "en", "def for term2", "en", "AltLbl for term2", None, "Prov for term2", "ex:XYZ/term2"),
        ("ex:test/term4", "..term4",   "en", None, None, None, None, None, None),
        ("ex:test/term1", "term1",     "en", None, None, None, None, None, None),
        ("ex:test/term2", "..term2",   "en", None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None, None),
    ]
    # fmt: on
    expected_levels = [0, 1, 2, 0, 1, 0, 1, 0]
    assert len(expected_rows) == len(expected_levels)
    expected_len = len(expected_rows[0])

    monkeypatch.chdir(datadir)
    main_cli(
        ["transform", "--to-indent"]
        + (
            [
                "--indent",
                indent,
            ]
            if indent
            else []
        )
        + [
            "--outdir",
            str(tmp_path),
            CS_CYCLES,
        ]
    )
    monkeypatch.chdir(tmp_path)
    wb = load_workbook(filename=CS_CYCLES, read_only=True)
    ws = wb["Concepts"]
    for row, expected_row, expected_level in zip(
        ws.iter_rows(min_row=3), expected_rows, expected_levels
    ):
        assert len(row) == expected_len
        if indent is None:  # Excel-indent
            assert int(row[1].alignment.indent) == expected_level

        for col in range(len(expected_rows)):
            if indent is None and col == 1:  # Excel-indent
                continue
            assert row[col].value == expected_row[col]


def test_hierarchy_to_indent_multilanguage(monkeypatch, datadir, tmp_path):
    # fmt: off
    expected_rows = [  # data in children-IRI-representation
        ("ex:test/term1", "term1",     "en", "def for term1", "en", "AltLbl for term1", None, "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term1", "Begr1",     "de", "Def für Begr1", "de", "AltLbl für Begr1", None, "Prov for term1", "ex:XYZ/term1"),
        ("ex:test/term3", "..term3",   "en", "def for term3", "en", "AltLbl for term3", None, "Prov for term3", "ex:XYZ/term3"),
        ("ex:test/term4", "....term4", "en", "def for term4", "en", "AltLbl for term4", None, "Prov for term4", "ex:XYZ/term4"),
        ("ex:test/term4", "....Begr4", "de", "Def für Begr4", "de", "AltLbl für Begr4", None, "Prov for term4", "ex:XYZ/term4"),
        ("ex:test/term2", "term2",     "en", "def for term2", "en", "AltLbl for term2", None, "Prov for term2", "ex:XYZ/term2"),
        ("ex:test/term4", "..term4",   "en", None, None, None, None, None, None),
        ("ex:test/term1", "term1",     "en", None, None, None, None, None, None),
        ("ex:test/term2", "..term2",   "en", None, None, None, None, None, None),
        (None, None, None, None, None, None, None, None, None),
    ]
    # fmt: on
    expected_levels = [0, 0, 1, 2, 2, 0, 1, 0, 1, 0]
    assert len(expected_rows) == len(expected_levels)
    monkeypatch.chdir(datadir)
    main_cli(
        [
            "transform",
            "--to-indent",
            "--outdir",
            str(tmp_path),
            CS_CYCLES_MULTI_LANG,
        ]
    )
    monkeypatch.chdir(tmp_path)
    wb = load_workbook(filename=CS_CYCLES_MULTI_LANG, read_only=True)
    ws = wb["Concepts"]
    for row, expected_row, expected_level in zip(
        ws.iter_rows(min_row=3), expected_rows, expected_levels
    ):
        # Excel-indent
        assert int(row[1].alignment.indent) == expected_level

        for col in range(len(expected_rows[0])):
            if col == 1:  # Excel-indent
                assert row[col].value == expected_row[col].strip(".")
                continue
            assert row[col].value == expected_row[col]


def test_hierarchy_to_indent_merge(monkeypatch, datadir, tmp_path):
    shutil.copy(datadir / CS_CYCLES_MULTI_LANG, tmp_path)
    monkeypatch.chdir(tmp_path)
    # change excel file: Delete vocabulary base IRI
    wb = load_workbook(filename=CS_CYCLES_MULTI_LANG)
    ws = wb["Concepts"]
    ws.cell(row=8, column=8).value = "Contradicting def."
    iri = ws.cell(row=8, column=1).value
    new_filename = "indent_merge_problem.xlsx"
    wb.save(new_filename)
    wb.close()
    with pytest.raises(Voc4catError, match=f"Merge conflict for concept {iri}"):
        main_cli(
            ["transform", "--to-indent", "--inplace", str(tmp_path / new_filename)]
        )


# ===== Tests for option --outdir =====


@pytest.mark.parametrize(
    "outdir",
    [None, "out"],
    ids=["no outdir", "with outdir"],
)
def test_outdir_variants(monkeypatch, datadir, tmp_path, outdir):
    shutil.copy(datadir / CS_CYCLES_INDENT_IRI, tmp_path)
    cmd = ["transform", "--from-indent"]
    if outdir:
        cmd.extend(["--outdir", str(tmp_path / outdir)])
    else:
        cmd.append("--inplace")
    cmd.append(str(tmp_path / CS_CYCLES_INDENT_IRI))
    monkeypatch.chdir(tmp_path)
    main_cli(cmd)

    expected = [
        ("ex:test/term1", "term1"),
        ("ex:test/term3", "term3"),
        ("ex:test/term4", "term4"),
        ("ex:test/term2", "term2"),
        (None, None),
    ]
    if outdir:
        xlsxfile = tmp_path / outdir / CS_CYCLES_INDENT_IRI
    else:
        xlsxfile = tmp_path / CS_CYCLES_INDENT_IRI
    wb = load_workbook(filename=xlsxfile, read_only=True, data_only=True)
    ws = wb["Concepts"]
    for row, expected_row in zip(
        ws.iter_rows(min_row=3, max_col=2, values_only=True), expected
    ):
        assert row == expected_row


# ===== Tests for options --split / --join =====


@pytest.mark.parametrize(
    "opt",
    [None, "--inplace"],
    ids=["default", "inplace"],
)
def test_split(monkeypatch, datadir, tmp_path, opt, caplog):
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    cmd = ["transform", "-v", "--split"]
    if opt:
        cmd.append("--inplace")
    cmd.append(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> wrote split vocabulary to" in caplog.text

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")
    assert vocdir.is_dir()
    assert (vocdir / "concept_scheme.ttl").exists()
    assert len([*vocdir.glob("*.ttl")]) == 8  # noqa: PLR2004
    if opt:
        assert not (tmp_path / CS_SIMPLE_TURTLE).exists()


@pytest.mark.parametrize(
    "opt",
    [None, "--inplace"],
    ids=["default", "inplace"],
)
def test_join(monkeypatch, datadir, tmp_path, opt, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    if opt:
        cmd.append("--inplace")
    cmd.append(str(tmp_path))

    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> joined vocabulary into" in caplog.text

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")
    assert (vocdir.parent / CS_SIMPLE_TURTLE).exists()
    if opt:
        assert not vocdir.exists()


@mock.patch.dict(
    os.environ, {"CI": "", "VOC4CAT_VERSION": "v2.0", "VOC4CAT_MODIFIED": "2023-08-15"}
)
def test_join_with_envvars(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    cmd.append(str(tmp_path))
    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> joined vocabulary into" in caplog.text
    # Were version and modified date correctly set?
    graph = Graph().parse(CS_SIMPLE_TURTLE, format="turtle")
    cs_query = "SELECT ?iri WHERE {?iri a skos:ConceptScheme.}"
    qresults = [*graph.query(cs_query, initNs={"skos": SKOS})]
    assert len(qresults) == 1

    cs_iri = qresults[0][0]
    assert (
        len(
            [
                *graph.triples(
                    (cs_iri, OWL.versionInfo, Literal("v2.0")),
                )
            ]
        )
        == 1
    )

    assert (
        len(
            [
                *graph.triples(
                    (
                        cs_iri,
                        DCTERMS.modified,
                        Literal("2023-08-15", datatype=XSD.date),
                    ),
                )
            ]
        )
        == 1
    )


@mock.patch.dict(
    os.environ, {"CI": "", "VOC4CAT_VERSION": "2.0", "VOC4CAT_MODIFIED": "2023-08-15"}
)
def test_join_with_invalid_envvar(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    cmd.append(str(tmp_path))
    with caplog.at_level(logging.ERROR), pytest.raises(
        Voc4catError, match="Invalid environment variable VOC4CAT_VERSION"
    ):
        main_cli(cmd)
    assert 'Invalid environment variable VOC4CAT_VERSION "2.0"' in caplog.text
