"""Tests for the convert_043 module.

These tests verify that the 0.4.3 to v1.0 RDF format converter works correctly,
transforming predicates and enriching ConceptScheme metadata.
"""

import logging
from pathlib import Path

from rdflib import (
    DCAT,
    DCTERMS,
    OWL,
    PROV,
    RDF,
    RDFS,
    SKOS,
    XSD,
    Graph,
    Literal,
    Namespace,
)

from voc4cat.config import Vocab
from voc4cat.convert_043 import convert_rdf_043_to_v1

logger = logging.getLogger(__name__)
EX = Namespace("http://example.org/")

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
VOCAB_043_TTL = TEST_DATA_DIR / "vocab-043-test.ttl"


class TestConvert043ToV1:
    """Tests for 043 to v1.0 RDF conversion."""

    def test_convert_043_vocab(self, tmp_path):
        """Test converting 0.4.3 format vocabulary to v1.0."""
        output_path = tmp_path / "vocab_043_v1.ttl"
        result_path = convert_rdf_043_to_v1(VOCAB_043_TTL, output_path)

        assert result_path.exists()
        assert result_path == output_path

        # Load and verify
        converted = Graph().parse(result_path, format="turtle")
        assert len(converted) > 0

        # Verify concepts were preserved
        concepts = list(converted.subjects(RDF.type, SKOS.Concept))
        assert len(concepts) == 7  # 7 concepts in test fixture

    def test_history_note_transformed_to_change_note(self, tmp_path):
        """Test that skos:historyNote is transformed to skos:changeNote."""
        # Create test RDF with skos:historyNote
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
        # Create test RDF with rdfs:isDefinedBy on a concept
        EXT = Namespace("http://external.org/")  # noqa: N806
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
        # Create test RDF with rdfs:isDefinedBy on a collection
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
        # Create test RDF with dcterms:hasPart on ConceptScheme (linking to collection)
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
        # Create test RDF with unknown predicate
        CUSTOM = Namespace("http://custom.org/")  # noqa: N806
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
        # Create minimal test RDF
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
        # Create minimal test RDF
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

    def test_convert_with_vocab_config_enriches_metadata(self, tmp_path):
        """Test that vocab_config enriches ConceptScheme metadata."""
        # Create minimal test RDF
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Original Title", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add a concept so the conversion has something to process
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Create vocab config with enrichment values
        vocab_config = Vocab(
            id_length=7,
            permanent_iri_part="http://example.org/",
            checks={},
            prefix_map={},
            vocabulary_iri="http://example.org/scheme",
            title="Config Title",
            description="Description from config",
            created_date="2025-01-01",
            creator="https://orcid.org/0000-0001-2345-6789",
            repository="https://github.com/test/repo",
        )

        # Convert with vocab_config
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path, vocab_config=vocab_config)

        # Load and verify enrichment
        converted = Graph().parse(output_path, format="turtle")

        # Verify title was updated from config
        titles = list(converted.objects(EX.scheme, SKOS.prefLabel))
        assert len(titles) == 1
        assert str(titles[0]) == "Config Title"

        # Verify description was added from config
        descriptions = list(converted.objects(EX.scheme, SKOS.definition))
        assert len(descriptions) == 1
        assert str(descriptions[0]) == "Description from config"

        # Verify created date was updated from config
        created_dates = list(converted.objects(EX.scheme, DCTERMS.created))
        assert len(created_dates) == 1
        assert str(created_dates[0]) == "2025-01-01"

    def test_convert_with_vocab_config_custodian(self, tmp_path):
        """Test that vocab_config custodian is added as dcat:contactPoint."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        vocab_config = Vocab(
            id_length=7,
            permanent_iri_part="http://example.org/",
            checks={},
            prefix_map={},
            vocabulary_iri="http://example.org/scheme",
            title="Test",
            description="Test",
            created_date="2024-01-01",
            creator="https://orcid.org/0000-0001-2345-6789",
            repository="https://github.com/test/repo",
            custodian="David Linke",
        )

        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path, vocab_config=vocab_config)

        converted = Graph().parse(output_path, format="turtle")

        # Verify custodian was added as dcat:contactPoint
        custodians = list(converted.objects(EX.scheme, DCAT.contactPoint))
        assert len(custodians) == 1
        assert str(custodians[0]) == "David Linke"

    def test_convert_without_vocab_config_preserves_rdf_metadata(self, tmp_path):
        """Test that without vocab_config, RDF metadata is preserved."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.bind("owl", OWL)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Original Title", lang="en")))
        g.add((EX.scheme, SKOS.definition, Literal("Original Description", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))
        g.add((EX.scheme, OWL.versionInfo, Literal("1.0.0")))

        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert WITHOUT vocab_config
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)

        converted = Graph().parse(output_path, format="turtle")

        # Verify original RDF values are preserved
        titles = list(converted.objects(EX.scheme, SKOS.prefLabel))
        assert len(titles) == 1
        assert str(titles[0]) == "Original Title"

        descriptions = list(converted.objects(EX.scheme, SKOS.definition))
        assert len(descriptions) == 1
        assert str(descriptions[0]) == "Original Description"

        versions = list(converted.objects(EX.scheme, OWL.versionInfo))
        assert len(versions) == 1
        assert str(versions[0]) == "1.0.0"

    def test_convert_with_vocab_config_preserves_concepts(self, tmp_path):
        """Test that conversion with vocab_config preserves concepts."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add multiple concepts
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Concept One", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        g.add((EX.concept2, RDF.type, SKOS.Concept))
        g.add((EX.concept2, SKOS.prefLabel, Literal("Concept Two", lang="en")))
        g.add((EX.concept2, SKOS.inScheme, EX.scheme))

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        vocab_config = Vocab(
            id_length=7,
            permanent_iri_part="http://example.org/",
            checks={},
            prefix_map={},
            vocabulary_iri="http://example.org/scheme",
            title="Updated Title",
            description="Updated description",
            created_date="2025-01-01",
            creator="https://orcid.org/0000-0001-2345-6789",
            repository="https://github.com/test/repo",
        )

        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path, vocab_config=vocab_config)

        converted = Graph().parse(output_path, format="turtle")

        # Verify concepts are preserved
        concepts = list(converted.subjects(RDF.type, SKOS.Concept))
        assert len(concepts) == 2

        # Verify concept labels are unchanged
        concept1_labels = list(converted.objects(EX.concept1, SKOS.prefLabel))
        assert len(concept1_labels) == 1
        assert str(concept1_labels[0]) == "Concept One"

        concept2_labels = list(converted.objects(EX.concept2, SKOS.prefLabel))
        assert len(concept2_labels) == 1
        assert str(concept2_labels[0]) == "Concept Two"
