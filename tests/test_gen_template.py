"""Tests for the gen_template module.

These tests verify that the v1.0 template generator creates Excel templates
with the correct structure.
"""

import logging

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from voc4cat.cli import main_cli
from voc4cat.gen_template import generate_template_v1
from voc4cat.models_v1 import (
    DEFAULT_PREFIXES,
    TEMPLATE_VERSION,
    CollectionV1,
    ConceptSchemeV1,
    ConceptV1,
    MappingV1,
    PrefixV1,
)


class TestTemplateGeneration:
    """Tests for template generation functionality."""

    def test_generate_template_creates_all_sheets(self, tmp_path):
        """Verify all 6 sheets are created."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)

        expected_sheets = {
            "Concept Scheme",
            "Concepts",
            "Collections",
            "Mappings",
            "ID Ranges",
            "Prefixes",
        }
        actual_sheets = set(wb.sheetnames)

        # Should have all expected sheets
        assert expected_sheets.issubset(actual_sheets), (
            f"Missing sheets: {expected_sheets - actual_sheets}"
        )

    def test_generate_template_sheet_order(self, tmp_path):
        """Verify sheets are in the correct order."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)

        expected_order = [
            "Concept Scheme",
            "Concepts",
            "Collections",
            "Mappings",
            "ID Ranges",
            "Prefixes",
        ]
        actual_order = wb.sheetnames[:6]

        assert actual_order == expected_order, (
            f"Sheet order mismatch: expected {expected_order}, got {actual_order}"
        )

    def test_concepts_sheet_has_table(self, tmp_path):
        """Verify Concepts sheet has proper table with correct columns."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Concepts"]

        # Check table exists
        assert ws.tables, "Concepts sheet should have a table"
        table_names = list(ws.tables.keys())
        assert len(table_names) == 1, "Should have exactly one table"

        # Check column headers (row 4 contains headers)
        expected_headers = [
            "Concept IRI*",
            "Language Code*",
            "Preferred Label*",
            "Definition*",
            "Alternate Labels",
            "Parent IRIs",
            "Member of collection(s)",
            "Member of ordered collection # position",
            "Provenance (read-only)",
            "Change Note",
            "Editorial Note",
            "Obsoletion reason",
            "Influenced by IRIs",
            "Source Vocab IRI or URL",
            "Source Vocab License",
            "Source Vocab Rights Holder",
        ]

        for col, expected_header in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual_header = ws[f"{col_letter}5"].value
            assert actual_header == expected_header, (
                f"Column {col} header mismatch: expected '{expected_header}', got '{actual_header}'"
            )

    def test_concepts_sheet_has_freeze_panes(self, tmp_path):
        """Verify Concepts sheet has freeze panes set."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Concepts"]

        assert ws.freeze_panes == "A6", (
            f"Expected freeze panes at A6, got {ws.freeze_panes}"
        )

    def test_collections_sheet_has_table(self, tmp_path):
        """Verify Collections sheet has proper table."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Collections"]

        assert ws.tables, "Collections sheet should have a table"

        # Check column headers
        expected_headers = [
            "Collection IRI",
            "Language Code*",
            "Preferred Label",
            "Definition",
            "Parent Collection IRIs",
            "Ordered? Yes or No (default)",
            "Provenance (read-only)",
            "Change Note*",
            "Editorial Note",
            "Obsoletion reason",
        ]

        for col, expected_header in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual_header = ws[f"{col_letter}5"].value
            assert actual_header == expected_header, (
                f"Column {col} header mismatch: expected '{expected_header}', got '{actual_header}'"
            )

    def test_mappings_sheet_has_table(self, tmp_path):
        """Verify Mappings sheet has proper table."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Mappings"]

        assert ws.tables, "Mappings sheet should have a table"

        # Check column headers
        expected_headers = [
            "Concept IRI*",
            "Related Matches",
            "Close Matches",
            "Exact Matches",
            "Narrower Matches",
            "Broader Matches",
            "Editorial Note",
        ]

        for col, expected_header in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual_header = ws[f"{col_letter}5"].value
            assert actual_header == expected_header, (
                f"Column {col} header mismatch: expected '{expected_header}', got '{actual_header}'"
            )

    def test_prefixes_sheet_has_default_prefixes(self, tmp_path):
        """Verify Prefixes sheet contains standard prefixes."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Prefixes"]

        # Check table exists
        assert ws.tables, "Prefixes sheet should have a table"

        # Check some key prefixes are present
        expected_prefixes = {"ex", "skos"}
        found_prefixes = set()

        # Prefixes start after header row
        for row in range(4, ws.max_row + 1):
            prefix = ws[f"A{row}"].value
            if prefix:
                found_prefixes.add(prefix)

        assert expected_prefixes.issubset(found_prefixes), (
            f"Missing expected prefixes: {expected_prefixes - found_prefixes}"
        )

    def test_concept_scheme_has_correct_fields(self, tmp_path):
        """Verify Concept Scheme sheet has correct fields."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["Concept Scheme"]

        # Check that Template version is first field
        assert ws["A4"].value == "Template version"
        assert ws["B4"].value == TEMPLATE_VERSION

        # Check other key fields exist
        expected_fields = [
            "Vocabulary IRI",
            "Prefix",
            "Title",
            "Description",
            "Created Date",
        ]

        found_fields = []
        for row in range(4, ws.max_row + 1):
            field = ws[f"A{row}"].value
            if field:
                found_fields.append(field)

        for field in expected_fields:
            assert field in found_fields, f"Missing field: {field}"

    def test_id_ranges_sheet_has_correct_structure(self, tmp_path):
        """Verify ID Ranges sheet has title and correct headers."""
        output_path = tmp_path / "test_template.xlsx"
        wb = generate_template_v1(output_path)
        ws = wb["ID Ranges"]

        # Check title row
        assert ws["A1"].value == "ID Ranges (read-only)"

        # Check headers (row 3)
        expected_headers = ["gh-name", "ID Range", "Unused IDs"]
        actual_headers = [ws["A3"].value, ws["B3"].value, ws["C3"].value]
        assert actual_headers == expected_headers

        # Data row should be empty (headers only in blank template)
        assert ws["A4"].value is None or ws["A4"].value == ""


class TestModels:
    """Tests for v1.0 Pydantic models."""

    def test_concept_scheme_default_values(self):
        """Test ConceptSchemeV1 has correct defaults."""
        cs = ConceptSchemeV1()
        assert cs.template_version == TEMPLATE_VERSION
        assert cs.vocabulary_iri == ""
        assert cs.prefix == ""

    def test_concept_v1_model(self):
        """Test ConceptV1 model creation."""
        concept = ConceptV1(
            concept_iri="ex:0001",
            language_code="en",
            preferred_label="Test",
            definition="A test concept",
        )
        assert concept.concept_iri == "ex:0001"
        assert concept.language_code == "en"
        assert concept.preferred_label == "Test"
        assert concept.alternate_labels == ""  # default

    def test_collection_v1_model(self):
        """Test CollectionV1 model creation."""
        collection = CollectionV1(
            collection_iri="ex:col1",
            language_code="en",
            preferred_label="Collection",
        )
        assert collection.collection_iri == "ex:col1"
        assert collection.ordered is None  # default

    def test_mapping_v1_model(self):
        """Test MappingV1 model creation."""
        mapping = MappingV1(
            concept_iri="ex:0001",
            exact_matches="http://example.org/ext/concept1",
        )
        assert mapping.concept_iri == "ex:0001"
        assert mapping.exact_matches == "http://example.org/ext/concept1"
        assert mapping.related_matches == ""  # default

    def test_prefix_v1_model(self):
        """Test PrefixV1 model creation."""
        prefix = PrefixV1(prefix="ex", namespace="https://example.org/")
        assert prefix.prefix == "ex"
        assert prefix.namespace == "https://example.org/"

    def test_default_prefixes_count(self):
        """Test that default prefixes list has expected entries."""
        assert len(DEFAULT_PREFIXES) == 2, (
            f"Expected 2 prefixes, got {len(DEFAULT_PREFIXES)}"
        )


class TestTemplateCLI:
    """CLI integration tests for the template command."""

    def test_template_cli_default_output(self, tmp_path, monkeypatch):
        """Test template command generates file in current directory."""
        monkeypatch.chdir(tmp_path)
        main_cli(["template", "myvocab"])

        expected_file = tmp_path / "myvocab.xlsx"
        assert expected_file.exists(), f"Template file not created: {expected_file}"

        # Verify it's a valid xlsx with expected sheets
        wb = load_workbook(expected_file)
        assert "Concepts" in wb.sheetnames

    def test_template_cli_with_outdir(self, tmp_path):
        """Test template command with --outdir option."""
        outdir = tmp_path / "output"
        main_cli(["template", "--outdir", str(outdir), "testvocab"])

        expected_file = outdir / "testvocab.xlsx"
        assert expected_file.exists(), (
            f"Template file not created in outdir: {expected_file}"
        )

    def test_template_cli_with_version_option(self, tmp_path, monkeypatch):
        """Test template command with --version option."""
        monkeypatch.chdir(tmp_path)
        main_cli(["template", "--version", "v1.0", "versionedvocab"])
        assert (tmp_path / "versionedvocab.xlsx").exists()

    def test_template_cli_invalid_version(self, tmp_path):
        """Test template command with invalid --version option."""
        with pytest.raises(SystemExit) as exc_info:
            main_cli(["template", "--version", "v0.5", "somevocab"])
        assert exc_info.value.code == 2  # argparse error

    def test_template_cli_requires_vocab(self):
        """Test template command requires VOCAB argument."""
        with pytest.raises(SystemExit) as exc_info:
            main_cli(["template"])
        assert exc_info.value.code == 2  # argparse error

    def test_template_cli_no_overwrite(self, tmp_path, monkeypatch, caplog):
        """Test template command does not overwrite existing files."""
        monkeypatch.chdir(tmp_path)
        # Create first
        main_cli(["template", "existingvocab"])
        file_path = tmp_path / "existingvocab.xlsx"
        assert file_path.exists()
        original_mtime = file_path.stat().st_mtime

        # Try to create again - should log error and not overwrite
        main_cli(["template", "existingvocab"])
        assert "File already exists" in caplog.text
        assert file_path.stat().st_mtime == original_mtime  # File not modified

    def test_template_cli_strips_extension(self, tmp_path, monkeypatch):
        """Test template command strips extension from VOCAB name."""
        monkeypatch.chdir(tmp_path)
        main_cli(["template", "withext.xlsx"])

        expected_file = tmp_path / "withext.xlsx"
        assert expected_file.exists(), f"Template file not created: {expected_file}"
        # Should not create withext.xlsx.xlsx
        assert not (tmp_path / "withext.xlsx.xlsx").exists()

    def test_template_cli_with_base_template(self, tmp_path, monkeypatch):
        """Test template command with --template option preserves base sheets."""
        from openpyxl import Workbook

        monkeypatch.chdir(tmp_path)

        # Create base template with custom sheets
        base_wb = Workbook()
        base_wb.active.title = "Cover"
        base_wb.create_sheet("Instructions")
        base_wb.create_sheet("Help")
        base_template = tmp_path / "base_template.xlsx"
        base_wb.save(base_template)
        base_wb.close()

        # Generate template with base
        main_cli(["template", "--template", str(base_template), "myvocab"])

        # Verify output
        output_file = tmp_path / "myvocab.xlsx"
        assert output_file.exists()

        result_wb = load_workbook(output_file)
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

    def test_template_cli_rejects_conflicting_base_template(
        self, tmp_path, monkeypatch, caplog
    ):
        """Test template command rejects base template with reserved sheet names."""
        from openpyxl import Workbook

        from voc4cat.checks import Voc4catError

        monkeypatch.chdir(tmp_path)

        # Create base template with a reserved sheet name
        base_wb = Workbook()
        base_wb.active.title = "Cover"
        base_wb.create_sheet("Concepts")  # Reserved name - should be rejected
        base_template = tmp_path / "bad_template.xlsx"
        base_wb.save(base_template)
        base_wb.close()

        with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
            main_cli(["template", "--template", str(base_template), "myvocab"])

        assert "reserved sheet names" in caplog.text
        assert "Concepts" in caplog.text

    def test_template_cli_rejects_nonexistent_base_template(
        self, tmp_path, monkeypatch, caplog
    ):
        """Test template command rejects non-existent base template."""
        from voc4cat.checks import Voc4catError

        monkeypatch.chdir(tmp_path)

        with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
            main_cli(["template", "--template", "nonexistent.xlsx", "myvocab"])

        assert "Template file not found" in caplog.text

    def test_template_cli_rejects_invalid_base_template_format(
        self, tmp_path, monkeypatch, caplog
    ):
        """Test template command rejects base template with wrong file type."""
        from voc4cat.checks import Voc4catError

        monkeypatch.chdir(tmp_path)

        # Create a non-xlsx file
        bad_template = tmp_path / "bad_template.txt"
        bad_template.touch()

        with caplog.at_level(logging.ERROR), pytest.raises(Voc4catError):
            main_cli(["template", "--template", str(bad_template), "myvocab"])

        assert 'Template file must be of type ".xlsx"' in caplog.text
