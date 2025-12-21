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
    assert (outdir / testfile).with_suffix(".xlsx").exists()
    assert (outdir / log.name).exists()


def test_duplicates(datadir, tmp_path, caplog, cs_cycles_xlsx):
    """Check that files do not have the same stem."""
    shutil.copy(cs_cycles_xlsx, tmp_path / CS_CYCLES)
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


def test_template_with_conflicting_sheets(monkeypatch, datadir, tmp_path, caplog):
    """Check that templates with reserved sheet names are rejected."""
    from openpyxl import Workbook

    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_CYCLES_TURTLE, tmp_path)

    # Create template with a reserved sheet name
    wb = Workbook()
    wb.active.title = "Branding"  # OK - not reserved
    wb.create_sheet("Concepts")  # CONFLICT - reserved name
    template_path = tmp_path / "bad_template.xlsx"
    wb.save(template_path)
    wb.close()

    with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
        main_cli(["convert", "--template", str(template_path), str(tmp_path)])

    assert "reserved sheet names" in caplog.text
    assert "Concepts" in caplog.text


def test_template_sheets_preserved_and_ordered(
    monkeypatch, datadir, tmp_path, temp_config
):
    """Check that template sheets are preserved and placed first."""
    from openpyxl import Workbook, load_workbook

    monkeypatch.chdir(tmp_path)
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    shutil.copy(datadir / CS_CYCLES_TURTLE, vocab_dir)

    # Create valid template with branding sheets (outside vocab_dir)
    wb = Workbook()
    wb.active.title = "Cover"
    wb.create_sheet("Instructions")
    wb.create_sheet("Help")
    template_path = tmp_path / "branding_template.xlsx"
    wb.save(template_path)
    wb.close()

    # Set up config for the vocabulary (name matches input file stem)
    config = temp_config
    vocab_name = "concept-scheme-with-cycles"
    config.CURIES_CONVERTER_MAP[vocab_name] = config.curies_converter

    main_cli(["convert", "--template", str(template_path), str(vocab_dir)])

    # Check output (name matches input file stem)
    output_path = vocab_dir / "concept-scheme-with-cycles.xlsx"
    assert output_path.exists()

    result_wb = load_workbook(output_path)
    sheets = result_wb.sheetnames

    # Template sheets should come first
    assert sheets[0] == "Cover"
    assert sheets[1] == "Instructions"
    assert sheets[2] == "Help"

    # Auto-created sheets should follow
    assert "Concept Scheme" in sheets
    assert "Concepts" in sheets
    assert "Collections" in sheets
    assert "Mappings" in sheets
    assert "ID Ranges" in sheets
    assert "Prefixes" in sheets

    # Verify order: template sheets before auto-created
    cover_idx = sheets.index("Cover")
    cs_idx = sheets.index("Concept Scheme")
    assert cover_idx < cs_idx

    result_wb.close()


def test_template_warning_for_xlsx_input(
    monkeypatch, datadir, tmp_path, caplog, cs_cycles_xlsx
):
    """Check that a warning is logged when template is used with xlsx input."""
    from openpyxl import Workbook

    monkeypatch.chdir(tmp_path)
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir()
    shutil.copy(cs_cycles_xlsx, vocab_dir / CS_CYCLES)

    # Create a valid template (outside vocab_dir)
    wb = Workbook()
    wb.active.title = "Branding"
    template_path = tmp_path / "template.xlsx"
    wb.save(template_path)
    wb.close()

    # The conversion may fail for other reasons (missing config), but the warning
    # should be logged before that happens
    with caplog.at_level(logging.WARNING):
        try:
            main_cli(["convert", "--template", str(template_path), str(vocab_dir)])
        except Voc4catError:
            pass  # Expected - conversion needs config, but warning comes first

    assert "Template option ignored for xlsx->RDF conversion" in caplog.text
