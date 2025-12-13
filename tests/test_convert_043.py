"""Tests for the convert_043 module.

These tests verify that the 0.4.3 to v1.0 RDF format converter works correctly,
transforming predicates and enriching ConceptScheme metadata.
"""

from pathlib import Path

import pytest
from rdflib import DCTERMS, RDF, SKOS, Graph, Literal, Namespace

from voc4cat.convert_043 import convert_rdf_043_to_v1

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
EXAMPLE_DIR = Path(__file__).parent.parent / "example"

PHOTOCATALYSIS_TTL = EXAMPLE_DIR / "photocatalysis_example.ttl"


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
        from rdflib import XSD

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
        from rdflib import PROV, RDFS, XSD

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
        from rdflib import RDFS, XSD

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

    def test_has_part_on_concept_scheme_dropped(self, tmp_path):
        """Test that dcterms:hasPart on ConceptScheme is dropped."""
        from rdflib import XSD

        # Create test RDF with dcterms:hasPart on ConceptScheme (linking to collection)
        EX = Namespace("http://example.org/")
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        # Add concept scheme with hasPart
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))
        g.add((EX.scheme, DCTERMS.hasPart, EX.collection1))

        # Add collection
        g.add((EX.collection1, RDF.type, SKOS.Collection))
        g.add((EX.collection1, SKOS.prefLabel, Literal("Test Collection", lang="en")))
        g.add((EX.collection1, SKOS.inScheme, EX.scheme))

        # Save test file
        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)

        # Verify
        converted = Graph().parse(output_path, format="turtle")

        # dcterms:hasPart should be dropped from ConceptScheme
        has_part = list(converted.objects(EX.scheme, DCTERMS.hasPart))
        assert len(has_part) == 0

        # But collection should still exist
        collections = list(converted.subjects(RDF.type, SKOS.Collection))
        assert len(collections) == 1

    def test_unknown_predicates_dropped_with_warning(self, tmp_path, caplog):
        """Test that unknown predicates are dropped and logged."""
        import logging

        from rdflib import XSD

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
        from rdflib import XSD

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
        from rdflib import XSD

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
