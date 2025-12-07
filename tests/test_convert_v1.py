"""Tests for the convert_v1 module.

These tests verify that the RDF to v1.0 Excel converter works correctly,
extracting data from RDF graphs and producing valid v1.0 template Excel files.
"""

from pathlib import Path

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from rdflib import SKOS, Graph, Literal, Namespace

from voc4cat.convert_v1 import (
    aggregate_concepts,
    build_concept_to_collections_map,
    build_concept_to_ordered_collections_map,
    build_curies_converter_from_prefixes,
    convert_rdf_043_to_v1,
    excel_to_rdf_v1,
    extract_collections_from_rdf,
    extract_concept_scheme_from_rdf,
    extract_concepts_from_rdf,
    extract_mappings_from_rdf,
    parse_ordered_collection_positions,
    rdf_concept_scheme_to_v1,
    rdf_concepts_to_v1,
    rdf_mappings_to_v1,
    rdf_to_excel_v1,
)
from voc4cat.models_v1 import TEMPLATE_VERSION, PrefixV1

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
EXAMPLE_DIR = Path(__file__).parent.parent / "example"

CS_SIMPLE_TTL = TEST_DATA_DIR / "concept-scheme-simple.ttl"
V1_COMPREHENSIVE_TTL = TEST_DATA_DIR / "v1-test-comprehensive.ttl"
PHOTOCATALYSIS_TTL = EXAMPLE_DIR / "photocatalysis_example.ttl"


class TestExtractConceptScheme:
    """Tests for extract_concept_scheme_from_rdf function."""

    def test_extract_basic_concept_scheme(self):
        """Test extracting basic concept scheme fields."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        data = extract_concept_scheme_from_rdf(graph)

        assert data["vocabulary_iri"] == "http://example.org/test/"
        assert data["title"] == "voc4cat-test-data"
        assert "concept scheme for unit testing" in data["description"].lower()
        assert data["created_date"] == "2022-12-01"
        assert data["modified_date"] == "2022-12-01"

    def test_extract_photocatalysis_concept_scheme(self):
        """Test extracting concept scheme from photocatalysis example."""
        if not PHOTOCATALYSIS_TTL.exists():
            pytest.skip("Photocatalysis example not found")

        graph = Graph().parse(PHOTOCATALYSIS_TTL, format="turtle")
        data = extract_concept_scheme_from_rdf(graph)

        # URI should have trailing slash (VocPub 5.2 convention)
        assert data["vocabulary_iri"] == "https://example.org/"
        assert (
            "photocatalysis" in data["title"].lower()
            or "example" in data["title"].lower()
        )
        assert data["created_date"] == "2023-06-29"


class TestExtractConcepts:
    """Tests for extract_concepts_from_rdf function."""

    def test_extract_concepts_from_simple(self):
        """Test extracting concepts from simple test file."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Should have 6 concepts (test01-test06)
        assert len(concepts) >= 6

        # Check a specific concept exists
        assert "http://example.org/test01" in concepts

    def test_concept_has_required_fields(self):
        """Test that extracted concepts have required fields."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Get first concept's first language data
        first_iri = next(iter(concepts.keys()))
        first_lang = next(iter(concepts[first_iri].keys()))
        data = concepts[first_iri][first_lang]

        assert "preferred_label" in data
        assert "definition" in data
        assert "alternate_labels" in data
        assert "parent_iris" in data

    def test_concept_hierarchy(self):
        """Test that parent IRIs are extracted correctly."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # test02 has test01 as parent (broader)
        if "http://example.org/test02" in concepts:
            test02_data = concepts["http://example.org/test02"]
            first_lang = next(iter(test02_data.keys()))
            assert "http://example.org/test01" in test02_data[first_lang]["parent_iris"]

    def test_english_language_first(self):
        """Test that English is listed first when present."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        for iri, lang_data in concepts.items():
            if "en" in lang_data:
                # English should be first
                first_lang = next(iter(lang_data.keys()))
                assert first_lang == "en", f"English not first for {iri}"


class TestExtractCollections:
    """Tests for extract_collections_from_rdf function."""

    def test_extract_collection_from_simple(self):
        """Test extracting collection from simple test file."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        collections = extract_collections_from_rdf(graph)

        # Should have at least 1 collection (test10)
        assert len(collections) >= 1

        # Check specific collection exists
        assert "http://example.org/test10" in collections

    def test_collection_has_required_fields(self):
        """Test that extracted collections have required fields."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        collections = extract_collections_from_rdf(graph)

        first_iri = next(iter(collections.keys()))
        first_lang = next(iter(collections[first_iri].keys()))
        data = collections[first_iri][first_lang]

        assert "preferred_label" in data
        assert "definition" in data
        assert "members" in data


class TestExtractMappings:
    """Tests for extract_mappings_from_rdf function."""

    def test_extract_mappings_from_simple(self):
        """Test extracting mappings from simple test file."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        mappings = extract_mappings_from_rdf(graph)

        # test01 has various mappings
        if "http://example.org/test01" in mappings:
            data = mappings["http://example.org/test01"]
            # Check that mapping types are present
            assert "related_matches" in data
            assert "close_matches" in data
            assert "exact_matches" in data
            assert "narrower_matches" in data
            assert "broader_matches" in data

    def test_only_concepts_with_mappings_included(self):
        """Test that only concepts with mappings are in the result."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        mappings = extract_mappings_from_rdf(graph)

        for iri, data in mappings.items():
            has_any = any(
                [
                    data.get("related_matches"),
                    data.get("close_matches"),
                    data.get("exact_matches"),
                    data.get("narrower_matches"),
                    data.get("broader_matches"),
                ]
            )
            assert has_any, f"Concept {iri} has no mappings but is in result"


class TestConceptToCollectionsMap:
    """Tests for build_concept_to_collections_map function."""

    def test_build_map_from_simple(self):
        """Test building concept-to-collections map."""
        graph = Graph().parse(CS_SIMPLE_TTL, format="turtle")
        c2c_map = build_concept_to_collections_map(graph)

        # test01-test04 are members of test10 collection
        if c2c_map:
            # At least one concept should be in a collection
            assert any(collections for collections in c2c_map.values())


class TestModelConversion:
    """Tests for model conversion functions."""

    def test_concept_scheme_to_v1(self):
        """Test converting concept scheme data to v1.0 model."""
        data = {
            "vocabulary_iri": "http://example.org/test/",
            "title": "Test Vocabulary",
            "description": "A test vocabulary",
            "created_date": "2024-01-01",
            "modified_date": "2024-01-02",
        }

        model = rdf_concept_scheme_to_v1(data)

        assert model.template_version == TEMPLATE_VERSION
        assert model.vocabulary_iri == "http://example.org/test/"
        assert model.title == "Test Vocabulary"

    def test_concepts_to_v1_single_language(self, temp_config):
        """Test converting concepts with single language."""
        concepts_data = {
            "http://example.org/c1": {
                "en": {
                    "preferred_label": "Concept 1",
                    "definition": "Definition 1",
                    "alternate_labels": ["alt1", "alt2"],
                    "parent_iris": [],
                    "source_vocab_iri": "",
                    "change_note": "",
                }
            }
        }

        models = rdf_concepts_to_v1(concepts_data, {})

        assert len(models) == 1
        assert models[0].preferred_label == "Concept 1"
        assert models[0].language_code == "en"
        assert "alt1" in models[0].alternate_labels

    def test_concepts_to_v1_multi_language(self, temp_config):
        """Test converting concepts with multiple languages."""
        concepts_data = {
            "http://example.org/c1": {
                "en": {
                    "preferred_label": "Concept 1",
                    "definition": "Definition 1",
                    "alternate_labels": [],
                    "parent_iris": ["http://example.org/parent"],
                    "source_vocab_iri": "",
                    "change_note": "",
                },
                "de": {
                    "preferred_label": "Konzept 1",
                    "definition": "Definition 1 auf Deutsch",
                    "alternate_labels": [],
                    "parent_iris": ["http://example.org/parent"],
                    "source_vocab_iri": "",
                    "change_note": "",
                },
            }
        }

        models = rdf_concepts_to_v1(concepts_data, {})

        assert len(models) == 2

        # First row (en) should have parent_iris
        en_model = next(m for m in models if m.language_code == "en")
        assert en_model.parent_iris != ""

        # Second row (de) should NOT have parent_iris (structural data only in first row)
        de_model = next(m for m in models if m.language_code == "de")
        assert de_model.parent_iris == ""

    def test_mappings_to_v1(self, temp_config):
        """Test converting mappings to v1.0 models."""
        mappings_data = {
            "http://example.org/c1": {
                "related_matches": ["http://example.org/related1"],
                "close_matches": [],
                "exact_matches": [
                    "http://example.org/exact1",
                    "http://example.org/exact2",
                ],
                "narrower_matches": [],
                "broader_matches": [],
            }
        }

        models = rdf_mappings_to_v1(mappings_data)

        assert len(models) == 1
        assert (
            "related1" in models[0].related_matches
            or "http://example.org/related1" in models[0].related_matches
        )
        assert models[0].exact_matches != ""


class TestRdfToExcelV1:
    """Tests for the main rdf_to_excel_v1 function."""

    def test_convert_simple_ttl(self, tmp_path, temp_config):
        """Test converting simple test TTL file."""
        output_path = tmp_path / "output.xlsx"

        result_path = rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        assert result_path.exists()
        assert result_path == output_path

        # Verify workbook structure
        wb = load_workbook(result_path)
        assert "Concept Scheme" in wb.sheetnames
        assert "Concepts" in wb.sheetnames
        assert "Collections" in wb.sheetnames
        assert "Mappings" in wb.sheetnames
        assert "Prefixes" in wb.sheetnames

    def test_convert_photocatalysis(self, tmp_path, temp_config):
        """Test converting photocatalysis example TTL file."""
        if not PHOTOCATALYSIS_TTL.exists():
            pytest.skip("Photocatalysis example not found")

        output_path = tmp_path / "photocatalysis.xlsx"

        result_path = rdf_to_excel_v1(PHOTOCATALYSIS_TTL, output_path)

        assert result_path.exists()

        wb = load_workbook(result_path)

        # Verify concepts sheet has data
        ws = wb["Concepts"]
        # Row 5 is first data row (after title, meaning, description, header)
        assert ws["A5"].value is not None, "Concepts sheet should have data"

    def test_default_output_path(self, tmp_path, temp_config):
        """Test that default output path uses .xlsx extension."""
        import shutil

        # Copy test file to tmp_path
        test_file = tmp_path / "test.ttl"
        shutil.copy(CS_SIMPLE_TTL, test_file)

        result_path = rdf_to_excel_v1(test_file)

        assert result_path == tmp_path / "test.xlsx"
        assert result_path.exists()

    def test_invalid_file_format(self, tmp_path, temp_config):
        """Test that invalid file format raises error."""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not rdf")

        with pytest.raises(ValueError, match="RDF file formats"):
            rdf_to_excel_v1(invalid_file)


class TestConceptsSheetStructure:
    """Tests for the structure of the generated Concepts sheet."""

    def test_concepts_sheet_has_correct_headers(self, tmp_path, temp_config):
        """Test that Concepts sheet has correct column headers."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concepts"]

        expected_headers = [
            "Concept IRI*",
            "Language Code*",
            "Preferred Label*",
            "Definition*",
            "Alternate Labels",
            "Parent IRIs",
            "Member of collection(s)",
            "Member of ordered collection # position",
            "Change Note",
            "Editorial Note",
            "Obsoletion reason",
            "Influenced by IRIs",
            "Source Vocab IRI or URL",
            "Source Vocab License",
            "Source Vocab Rights Holder",
        ]

        for col, expected in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual = ws[f"{col_letter}4"].value
            assert actual == expected, (
                f"Column {col} header mismatch: expected '{expected}', got '{actual}'"
            )

    def test_concepts_sheet_has_table(self, tmp_path, temp_config):
        """Test that Concepts sheet has a proper Excel table."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concepts"]

        assert ws.tables, "Concepts sheet should have a table"

    def test_concepts_sheet_has_freeze_panes(self, tmp_path, temp_config):
        """Test that Concepts sheet has freeze panes."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concepts"]

        assert ws.freeze_panes == "A5", (
            f"Expected freeze panes at A5, got {ws.freeze_panes}"
        )


class TestCollectionsSheetStructure:
    """Tests for the structure of the generated Collections sheet."""

    def test_collections_sheet_has_correct_headers(self, tmp_path, temp_config):
        """Test that Collections sheet has correct column headers."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Collections"]

        expected_headers = [
            "Collection IRI",
            "Language Code*",
            "Preferred Label",
            "Definition",
            "Parent Collection IRIs",
            "Ordered? Yes or No (default)",
            "Change Note*",
            "Editorial Note",
            "Obsoletion reason",
        ]

        for col, expected in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual = ws[f"{col_letter}4"].value
            assert actual == expected, (
                f"Column {col} header mismatch: expected '{expected}', got '{actual}'"
            )


class TestMappingsSheetStructure:
    """Tests for the structure of the generated Mappings sheet."""

    def test_mappings_sheet_has_correct_headers(self, tmp_path, temp_config):
        """Test that Mappings sheet has correct column headers."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Mappings"]

        expected_headers = [
            "Concept IRI*",
            "Related Matches",
            "Close Matches",
            "Exact Matches",
            "Narrower Matches",
            "Broader Matches",
            "Editorial Note",
        ]

        for col, expected in enumerate(expected_headers, 1):
            col_letter = get_column_letter(col)
            actual = ws[f"{col_letter}4"].value
            assert actual == expected, (
                f"Column {col} header mismatch: expected '{expected}', got '{actual}'"
            )


class TestConceptSchemeSheet:
    """Tests for the Concept Scheme sheet."""

    def test_concept_scheme_has_template_version(self, tmp_path, temp_config):
        """Test that Concept Scheme sheet has template version."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concept Scheme"]

        # Template version should be first field
        assert ws["A4"].value == "Template version"
        assert ws["B4"].value == TEMPLATE_VERSION

    def test_concept_scheme_has_vocabulary_iri(self, tmp_path, temp_config):
        """Test that Concept Scheme sheet has vocabulary IRI."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concept Scheme"]

        # Find vocabulary IRI row
        found = False
        for row in range(4, 30):
            if ws[f"A{row}"].value == "Vocabulary IRI":
                assert ws[f"B{row}"].value == "http://example.org/test/"
                found = True
                break

        assert found, "Vocabulary IRI field not found"


class TestPrefixesSheet:
    """Tests for the Prefixes sheet."""

    def test_prefixes_sheet_has_data(self, tmp_path, temp_config):
        """Test that Prefixes sheet has prefix data."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Prefixes"]

        # Should have at least some prefixes
        # Row 4 is header, row 5+ is data
        assert ws["A5"].value is not None, "Prefixes sheet should have data"


class TestMultiLanguageSupport:
    """Tests for multi-language handling."""

    def test_multi_language_concepts_create_multiple_rows(self, tmp_path):
        """Test that concepts with multiple languages create multiple rows."""
        # Create a simple RDF with multi-language concept
        EX = Namespace("http://example.org/")
        graph = Graph()
        graph.bind("ex", EX)
        graph.bind("skos", SKOS)

        # Add concept scheme
        graph.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        graph.add((EX.scheme, SKOS.definition, Literal("A test scheme", lang="en")))
        from rdflib import DCTERMS, RDF, XSD

        graph.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        graph.add(
            (EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date))
        )
        graph.add(
            (EX.scheme, DCTERMS.modified, Literal("2024-01-01", datatype=XSD.date))
        )

        # Add multi-language concept
        graph.add((EX.concept1, RDF.type, SKOS.Concept))
        graph.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        graph.add((EX.concept1, SKOS.prefLabel, Literal("Testkonzept", lang="de")))
        graph.add((EX.concept1, SKOS.definition, Literal("A test concept", lang="en")))
        graph.add((EX.concept1, SKOS.definition, Literal("Ein Testkonzept", lang="de")))
        graph.add((EX.concept1, SKOS.inScheme, EX.scheme))

        # Save to temp file
        ttl_path = tmp_path / "multi_lang.ttl"
        graph.serialize(destination=str(ttl_path), format="turtle")

        # Convert
        output_path = tmp_path / "multi_lang.xlsx"
        rdf_to_excel_v1(ttl_path, output_path)

        # Verify
        wb = load_workbook(output_path)
        ws = wb["Concepts"]

        # Count rows with concept IRI
        concept_rows = []
        for row in range(5, ws.max_row + 1):
            if ws[f"A{row}"].value:
                concept_rows.append(row)

        # Should have 2 rows (en and de)
        assert len(concept_rows) >= 2, (
            "Should have at least 2 rows for multi-language concept"
        )

        # Check both languages are present
        langs = [ws[f"B{row}"].value for row in concept_rows]
        assert "en" in langs
        assert "de" in langs


class TestCollectionMembership:
    """Tests for collection membership handling."""

    def test_concept_membership_in_collection(self, tmp_path, temp_config):
        """Test that concept membership in collections is recorded."""
        output_path = tmp_path / "output.xlsx"
        rdf_to_excel_v1(CS_SIMPLE_TTL, output_path)

        wb = load_workbook(output_path)
        ws = wb["Concepts"]

        # Find "Member of collection(s)" column (column G)
        member_col = "G"

        # Check if any concept has collection membership
        has_membership = False
        for row in range(5, ws.max_row + 1):
            if ws[f"{member_col}{row}"].value:
                has_membership = True
                break

        # In concept-scheme-simple.ttl, test01-test04 are members of test10 collection
        assert has_membership, "Some concepts should have collection membership"


class TestRoundTrip:
    """Tests for lossless round-trip conversion RDF -> XLSX -> RDF."""

    def test_roundtrip_photocatalysis(self, tmp_path, temp_config):
        """Test that photocatalysis RDF -> XLSX -> RDF preserves core data.

        Note: The photocatalysis example uses older predicates (e.g. rdfs:isDefinedBy)
        that are now mapped to newer predicates (e.g. prov:hadPrimarySource) in v1.0.
        Therefore exact triple count match is not expected. The important thing is
        that core SKOS data is preserved.
        """
        if not PHOTOCATALYSIS_TTL.exists():
            pytest.skip("Photocatalysis example not found")

        # Load original
        original = Graph().parse(PHOTOCATALYSIS_TTL, format="turtle")

        # RDF -> XLSX
        xlsx_path = tmp_path / "photocatalysis.xlsx"
        rdf_to_excel_v1(PHOTOCATALYSIS_TTL, xlsx_path)

        # XLSX -> RDF
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        # Check that concept count matches
        from rdflib import RDF

        original_concepts = list(original.subjects(RDF.type, SKOS.Concept))
        roundtrip_concepts = list(roundtrip.subjects(RDF.type, SKOS.Concept))
        assert len(original_concepts) == len(roundtrip_concepts), (
            f"Concept count mismatch: original={len(original_concepts)}, "
            f"roundtrip={len(roundtrip_concepts)}"
        )

        # Check that all prefLabels are preserved
        original_labels = set(str(o) for o in original.objects(None, SKOS.prefLabel))
        roundtrip_labels = set(str(o) for o in roundtrip.objects(None, SKOS.prefLabel))
        assert original_labels == roundtrip_labels, (
            f"Label mismatch.\n"
            f"Only in original: {original_labels - roundtrip_labels}\n"
            f"Only in roundtrip: {roundtrip_labels - original_labels}"
        )

    def test_roundtrip_preserves_all_predicates(self, tmp_path, temp_config):
        """Test that all predicates are preserved during round-trip."""
        if not PHOTOCATALYSIS_TTL.exists():
            pytest.skip("Photocatalysis example not found")

        # Load original
        original = Graph().parse(PHOTOCATALYSIS_TTL, format="turtle")

        # RDF -> XLSX -> RDF
        xlsx_path = tmp_path / "photocatalysis.xlsx"
        rdf_to_excel_v1(PHOTOCATALYSIS_TTL, xlsx_path)
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        # Get all predicates
        original_predicates = set(p for _, p, _ in original)
        roundtrip_predicates = set(p for _, p, _ in roundtrip)

        # Same predicates
        assert original_predicates == roundtrip_predicates, (
            f"Predicate mismatch.\n"
            f"Only in original: {original_predicates - roundtrip_predicates}\n"
            f"Only in roundtrip: {roundtrip_predicates - original_predicates}"
        )


# =============================================================================
# V1.0 Feature Tests - New columns and predicates
# =============================================================================


class TestV1NewFeatures:
    """Tests for new v1.0 template features."""

    def test_extract_editorial_note(self):
        """Test that editorial notes are extracted from RDF."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Concept 0000001 has editorial note
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = f"{photocat_ns}0000001"

        assert concept_iri in concepts
        en_data = concepts[concept_iri].get("en", {})
        assert (
            en_data.get("editorial_note")
            == "Review multi-language labels for accuracy."
        )

    def test_extract_obsolete_concept(self):
        """Test that obsolete concepts are extracted with reason."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Concept 0000005 is obsolete
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = f"{photocat_ns}0000005"

        assert concept_iri in concepts
        en_data = concepts[concept_iri].get("en", {})
        assert en_data.get("obsolete_reason") == "This concept was added in error."

    def test_extract_source_vocab_attribution(self):
        """Test that source vocabulary attribution is extracted."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Concept 0000002 has source attribution
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = f"{photocat_ns}0000002"

        assert concept_iri in concepts
        en_data = concepts[concept_iri].get("en", {})
        assert (
            en_data.get("source_vocab_iri")
            == "https://goldbook.iupac.org/terms/view/P04580"
        )
        assert (
            en_data.get("source_vocab_license")
            == "https://creativecommons.org/licenses/by/4.0/"
        )
        assert en_data.get("source_vocab_rights_holder") == "IUPAC Gold Book"

    def test_extract_influenced_by(self):
        """Test that influenced by IRIs are extracted."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        concepts = extract_concepts_from_rdf(graph)

        # Concept 0000002 has influenced_by
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = f"{photocat_ns}0000002"

        assert concept_iri in concepts
        en_data = concepts[concept_iri].get("en", {})
        influenced = en_data.get("influenced_by_iris", [])
        assert len(influenced) == 2
        assert "https://doi.org/10.1351/goldbook.P04580" in influenced

    def test_extract_ordered_collection(self):
        """Test that ordered collections are extracted."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        collections = extract_collections_from_rdf(graph)

        # coll002 is an ordered collection
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        coll_iri = f"{photocat_ns}coll002"

        assert coll_iri in collections
        en_data = collections[coll_iri].get("en", {})
        assert en_data.get("ordered") is True
        assert len(en_data.get("ordered_members", [])) == 2

    def test_extract_collection_editorial_note(self):
        """Test that collection editorial notes are extracted."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        collections = extract_collections_from_rdf(graph)

        # coll001 has editorial note
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        coll_iri = f"{photocat_ns}coll001"

        assert coll_iri in collections
        en_data = collections[coll_iri].get("en", {})
        assert "subcollections" in en_data.get("editorial_note", "")


class TestOrderedCollectionPositions:
    """Tests for ordered collection position parsing."""

    def test_parse_simple_position(self):
        """Test parsing simple position format."""
        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        result = parse_ordered_collection_positions("ex:coll1 # 1", converter)

        assert result == {"http://example.org/coll1": 1}

    def test_parse_multiple_positions(self):
        """Test parsing multiple positions."""
        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        result = parse_ordered_collection_positions(
            "ex:coll1 # 1 ex:coll2 # 3", converter
        )

        assert result == {
            "http://example.org/coll1": 1,
            "http://example.org/coll2": 3,
        }

    def test_parse_position_with_whitespace(self):
        """Test parsing positions with extra whitespace."""
        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        result = parse_ordered_collection_positions("ex:coll1  #  2", converter)

        assert result == {"http://example.org/coll1": 2}

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        result = parse_ordered_collection_positions("", converter)

        assert result == {}


class TestBuildOrderedCollectionMaps:
    """Tests for building ordered collection maps."""

    def test_build_concept_to_ordered_collections_map(self):
        """Test building concept to ordered collections map from RDF."""
        graph = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")
        c2o_map = build_concept_to_ordered_collections_map(graph)

        # coll002 has ordered members: 0000003 at pos 1, 0000004 at pos 2
        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"

        concept3 = f"{photocat_ns}0000003"
        if concept3 in c2o_map:
            assert f"{photocat_ns}coll002" in c2o_map[concept3]
            assert c2o_map[concept3][f"{photocat_ns}coll002"] == 1

        concept4 = f"{photocat_ns}0000004"
        if concept4 in c2o_map:
            assert f"{photocat_ns}coll002" in c2o_map[concept4]
            assert c2o_map[concept4][f"{photocat_ns}coll002"] == 2


class TestV1RoundTrip:
    """Tests for v1.0 specific round-trip conversion."""

    def test_roundtrip_comprehensive(self, tmp_path, temp_config):
        """Test round-trip with comprehensive v1.0 test data."""
        # Load original
        original = Graph().parse(V1_COMPREHENSIVE_TTL, format="turtle")

        # RDF -> XLSX
        xlsx_path = tmp_path / "v1_comprehensive.xlsx"
        rdf_to_excel_v1(V1_COMPREHENSIVE_TTL, xlsx_path)

        # XLSX -> RDF
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        # Check triple counts
        original_count = len(original)
        roundtrip_count = len(roundtrip)

        # Allow small difference due to BNode handling in RDF lists
        assert abs(original_count - roundtrip_count) <= 10, (
            f"Triple count mismatch: original={original_count}, roundtrip={roundtrip_count}"
        )

    def test_roundtrip_preserves_editorial_note(self, tmp_path, temp_config):
        """Test that editorial notes survive round-trip."""
        # RDF -> XLSX -> RDF
        xlsx_path = tmp_path / "editorial_note.xlsx"
        rdf_to_excel_v1(V1_COMPREHENSIVE_TTL, xlsx_path)
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        # Check editorial note is preserved
        from rdflib import SKOS, URIRef

        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = URIRef(f"{photocat_ns}0000001")

        editorial_notes = list(roundtrip.objects(concept_iri, SKOS.editorialNote))
        assert len(editorial_notes) > 0
        assert any("Review multi-language" in str(n) for n in editorial_notes)

    def test_roundtrip_preserves_obsolete(self, tmp_path, temp_config):
        """Test that obsolete concepts survive round-trip."""
        # RDF -> XLSX -> RDF
        xlsx_path = tmp_path / "obsolete.xlsx"
        rdf_to_excel_v1(V1_COMPREHENSIVE_TTL, xlsx_path)
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        # Check deprecated flag and history note are preserved
        from rdflib import OWL, SKOS, URIRef

        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = URIRef(f"{photocat_ns}0000005")

        # Check deprecated flag
        deprecated = list(roundtrip.objects(concept_iri, OWL.deprecated))
        assert len(deprecated) > 0

        # Check history note has obsolete reason
        history_notes = list(roundtrip.objects(concept_iri, SKOS.historyNote))
        assert len(history_notes) > 0
        assert any("added in error" in str(n) for n in history_notes)

    def test_roundtrip_preserves_source_attribution(self, tmp_path, temp_config):
        """Test that source attribution survives round-trip."""
        from rdflib import DCTERMS, PROV, URIRef

        # RDF -> XLSX -> RDF
        xlsx_path = tmp_path / "source_attr.xlsx"
        rdf_to_excel_v1(V1_COMPREHENSIVE_TTL, xlsx_path)
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        concept_iri = URIRef(f"{photocat_ns}0000002")

        # Check hadPrimarySource
        sources = list(roundtrip.objects(concept_iri, PROV.hadPrimarySource))
        assert len(sources) > 0

        # Check license
        licenses = list(roundtrip.objects(concept_iri, DCTERMS.license))
        assert len(licenses) > 0

        # Check rightsHolder
        rights_holders = list(roundtrip.objects(concept_iri, DCTERMS.rightsHolder))
        assert len(rights_holders) > 0

    def test_roundtrip_preserves_ordered_collection(self, tmp_path, temp_config):
        """Test that ordered collections survive round-trip."""
        from rdflib import SKOS, URIRef

        # RDF -> XLSX -> RDF
        xlsx_path = tmp_path / "ordered_coll.xlsx"
        rdf_to_excel_v1(V1_COMPREHENSIVE_TTL, xlsx_path)
        roundtrip = excel_to_rdf_v1(xlsx_path, output_type="graph")

        photocat_ns = "https://w3id.org/nfdi4cat/voc4cat-photocat/"
        coll_iri = URIRef(f"{photocat_ns}coll002")

        # Check it's an OrderedCollection
        from rdflib import RDF

        types = list(roundtrip.objects(coll_iri, RDF.type))
        assert SKOS.OrderedCollection in types

        # Check memberList exists
        member_lists = list(roundtrip.objects(coll_iri, SKOS.memberList))
        assert len(member_lists) > 0


class TestAlternateLabelSeparator:
    """Tests for alternate label separator handling."""

    def test_alternate_labels_split_by_pipe(self, temp_config):
        """Test that alternate labels are split by pipe separator."""
        from voc4cat.models_v1 import ConceptV1

        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        concept_rows = [
            ConceptV1(
                concept_iri="ex:c1",
                language_code="en",
                preferred_label="Test",
                definition="A test",
                alternate_labels="alt1 | alt2 | alt3",
            )
        ]

        concepts = aggregate_concepts(concept_rows, converter)
        concept = concepts["http://example.org/c1"]

        assert concept.alt_labels["en"] == ["alt1", "alt2", "alt3"]

    def test_alternate_labels_trim_whitespace(self, temp_config):
        """Test that whitespace is trimmed from alternate labels."""
        from voc4cat.models_v1 import ConceptV1

        prefixes = [PrefixV1(prefix="ex", namespace="http://example.org/")]
        converter = build_curies_converter_from_prefixes(prefixes)

        concept_rows = [
            ConceptV1(
                concept_iri="ex:c1",
                language_code="en",
                preferred_label="Test",
                definition="A test",
                alternate_labels="  alt1  |  alt2  ",
            )
        ]

        concepts = aggregate_concepts(concept_rows, converter)
        concept = concepts["http://example.org/c1"]

        # Whitespace should be trimmed
        assert concept.alt_labels["en"] == ["alt1", "alt2"]


# =============================================================================
# 043 to v1.0 RDF Conversion Tests
# =============================================================================


class TestConvert043ToV1:
    """Tests for 043 to v1.0 RDF conversion."""

    def test_convert_photocatalysis(self, tmp_path):
        """Test converting photocatalysis example from 043 to v1.0."""
        if not PHOTOCATALYSIS_TTL.exists():
            pytest.skip("Photocatalysis example not found")

        output_path = tmp_path / "photocatalysis_v1.ttl"
        result_path = convert_rdf_043_to_v1(PHOTOCATALYSIS_TTL, output_path)

        assert result_path.exists()
        assert result_path == output_path

        # Load and verify
        converted = Graph().parse(result_path, format="turtle")
        assert len(converted) > 0

    def test_history_note_transformed_to_change_note(self, tmp_path):
        """Test that skos:historyNote is transformed to skos:changeNote."""
        from rdflib import DCTERMS, RDF, XSD

        # Create test RDF with skos:historyNote
        EX = Namespace("http://example.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        # Add concept scheme
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add concept with historyNote (043 style)
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((EX.concept1, SKOS.historyNote, Literal("Created by author", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        # Save test file
        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)

        # Verify
        converted = Graph().parse(output_path, format="turtle")

        # Should have skos:changeNote, not skos:historyNote
        change_notes = list(converted.objects(EX.concept1, SKOS.changeNote))
        history_notes = list(converted.objects(EX.concept1, SKOS.historyNote))

        assert len(change_notes) == 1
        assert len(history_notes) == 0
        assert "Created by author" in str(change_notes[0])

    def test_is_defined_by_on_concept_transformed(self, tmp_path):
        """Test that rdfs:isDefinedBy on concepts becomes prov:hadPrimarySource."""
        from rdflib import DCTERMS, PROV, RDF, RDFS, XSD

        # Create test RDF with rdfs:isDefinedBy on a concept
        EX = Namespace("http://example.org/")
        EXT = Namespace("http://external.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("ext", EXT)
        g.bind("skos", SKOS)

        # Add concept scheme
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add concept with rdfs:isDefinedBy pointing to external source
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Borrowed Concept", lang="en")))
        g.add((EX.concept1, RDFS.isDefinedBy, EXT.source))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        # Save test file
        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)

        # Verify
        converted = Graph().parse(output_path, format="turtle")

        # Should have prov:hadPrimarySource, not rdfs:isDefinedBy on concept
        primary_sources = list(converted.objects(EX.concept1, PROV.hadPrimarySource))
        is_defined_by = list(converted.objects(EX.concept1, RDFS.isDefinedBy))

        assert len(primary_sources) == 1
        assert len(is_defined_by) == 0
        assert str(primary_sources[0]) == str(EXT.source)

    def test_is_defined_by_on_collection_preserved(self, tmp_path):
        """Test that rdfs:isDefinedBy on collections is preserved."""
        from rdflib import DCTERMS, RDF, RDFS, XSD

        # Create test RDF with rdfs:isDefinedBy on a collection
        EX = Namespace("http://example.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        # Add concept scheme
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add collection with rdfs:isDefinedBy pointing to scheme
        g.add((EX.collection1, RDF.type, SKOS.Collection))
        g.add((EX.collection1, SKOS.prefLabel, Literal("Test Collection", lang="en")))
        g.add((EX.collection1, RDFS.isDefinedBy, EX.scheme))
        g.add((EX.collection1, SKOS.inScheme, EX.scheme))

        # Save test file
        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)

        # Verify
        converted = Graph().parse(output_path, format="turtle")

        # rdfs:isDefinedBy should be preserved on collection
        is_defined_by = list(converted.objects(EX.collection1, RDFS.isDefinedBy))

        assert len(is_defined_by) == 1
        assert str(is_defined_by[0]) == str(EX.scheme)

    def test_unknown_predicates_dropped_with_warning(self, tmp_path, caplog):
        """Test that unknown predicates are dropped and logged."""
        import logging

        from rdflib import DCTERMS, RDF, XSD

        # Create test RDF with unknown predicate
        EX = Namespace("http://example.org/")
        CUSTOM = Namespace("http://custom.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("custom", CUSTOM)
        g.bind("skos", SKOS)

        # Add concept scheme
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add concept with unknown predicate
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.concept1, CUSTOM.unknownPredicate, Literal("custom value")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        # Save test file
        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert with logging capture
        output_path = tmp_path / "test_v1.ttl"
        with caplog.at_level(logging.WARNING):
            convert_rdf_043_to_v1(input_path, output_path)

        # Verify warning was logged
        assert "unknown predicate" in caplog.text.lower()
        assert "custom.org/unknownPredicate" in caplog.text

        # Verify predicate was dropped
        converted = Graph().parse(output_path, format="turtle")
        custom_values = list(converted.objects(EX.concept1, CUSTOM.unknownPredicate))
        assert len(custom_values) == 0

    def test_default_output_path(self, tmp_path):
        """Test that default output path adds _v1 suffix."""
        from rdflib import DCTERMS, RDF, XSD

        # Create minimal test RDF
        EX = Namespace("http://example.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Save test file
        input_path = tmp_path / "my_vocab.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert without specifying output
        result_path = convert_rdf_043_to_v1(input_path)

        # Should create my_vocab_v1.ttl
        expected_path = tmp_path / "my_vocab_v1.ttl"
        assert result_path == expected_path
        assert result_path.exists()

    def test_output_format_xml(self, tmp_path):
        """Test conversion to XML format."""
        from rdflib import DCTERMS, RDF, XSD

        # Create minimal test RDF
        EX = Namespace("http://example.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        input_path = tmp_path / "test.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert to XML
        output_path = tmp_path / "test_v1.rdf"
        result_path = convert_rdf_043_to_v1(
            input_path, output_path, output_format="xml"
        )

        assert result_path.exists()

        # Verify it's valid XML
        converted = Graph().parse(result_path, format="xml")
        assert len(converted) > 0
