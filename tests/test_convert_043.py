"""Tests for the convert_043 module.

These tests verify that the 0.4.3 to v1.0 RDF format converter works correctly,
transforming predicates and enriching ConceptScheme metadata.
"""

import logging
from pathlib import Path

import pytest
from rdflib import (
    DCAT,
    DCTERMS,
    FOAF,
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
from voc4cat.convert_v1 import HISTORY_NOTE_FIRST_TIME

logger = logging.getLogger(__name__)
EX = Namespace("http://example.org/")

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
VOCAB_043_TTL = TEST_DATA_DIR / "vocab-043-test.ttl"


class TestConvert043ToV1:
    """Tests for 043 to v1.0 RDF conversion."""

    def _convert_and_parse(
        self, tmp_path, graph, *, vocab_config=None, output_format="turtle"
    ):
        """Convert graph via 043->v1 pipeline and return parsed result."""
        input_path = tmp_path / "test_043.ttl"
        graph.serialize(destination=str(input_path), format="turtle")
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(
            input_path,
            output_path,
            vocab_config=vocab_config,
            output_format=output_format,
        )
        return Graph().parse(output_path, format=output_format)

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

        converted = self._convert_and_parse(tmp_path, g)

        # The 043 historyNote should be transformed to changeNote
        change_notes = list(converted.objects(EX.concept1, SKOS.changeNote))
        assert len(change_notes) == 1
        assert "Created by author" in str(change_notes[0])

        # Concept should also have the first-time historyNote (no provenance)
        history_notes = list(converted.objects(EX.concept1, SKOS.historyNote))
        assert len(history_notes) == 1
        assert str(history_notes[0]) == HISTORY_NOTE_FIRST_TIME

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

        converted = self._convert_and_parse(tmp_path, g)

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

        converted = self._convert_and_parse(tmp_path, g)

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

        converted = self._convert_and_parse(tmp_path, g)

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

        converted = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

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

        converted = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

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

        # Convert WITHOUT vocab_config
        converted = self._convert_and_parse(tmp_path, g)

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

        converted = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

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


class TestFirstTimeHistoryNote043:
    """Tests for skos:historyNote on first-time expressed concepts in 043 conversion."""

    def _convert_and_parse(self, tmp_path, graph):
        """Convert graph via 043->v1 pipeline and return parsed result."""
        input_path = tmp_path / "test_043.ttl"
        graph.serialize(destination=str(input_path), format="turtle")
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)
        return Graph().parse(output_path, format="turtle")

    def test_first_time_history_note_added_without_provenance(self, tmp_path):
        """Concept without prov:hadPrimarySource/wasInfluencedBy gets first-time historyNote."""

        # Create test RDF with concept that has no provenance predicates
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))

        converted = self._convert_and_parse(tmp_path, g)

        history_notes = list(converted.objects(EX.concept1, SKOS.historyNote))
        assert len(history_notes) == 1
        assert str(history_notes[0]) == HISTORY_NOTE_FIRST_TIME

    @pytest.mark.parametrize(
        ("provenance_predicate", "provenance_object"),
        [
            (PROV.hadPrimarySource, EX.other_vocab),
            (PROV.wasInfluencedBy, EX.other_concept),
        ],
        ids=["hadPrimarySource", "wasInfluencedBy"],
    )
    def test_first_time_history_note_not_added_with_provenance(
        self, tmp_path, provenance_predicate, provenance_object
    ):
        """Concept with provenance predicates should NOT get first-time historyNote."""

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.bind("prov", PROV)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))
        g.add((EX.concept1, provenance_predicate, provenance_object))

        converted = self._convert_and_parse(tmp_path, g)

        history_notes = list(converted.objects(EX.concept1, SKOS.historyNote))
        note_values = [str(n) for n in history_notes]
        assert HISTORY_NOTE_FIRST_TIME not in note_values

    def test_collection_gets_first_time_history_note(self, tmp_path):
        """Collection without provenance gets first-time historyNote in 043 conversion."""

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        g.add((EX.collection1, RDF.type, SKOS.Collection))
        g.add((EX.collection1, SKOS.prefLabel, Literal("Test Collection", lang="en")))
        g.add((EX.collection1, SKOS.inScheme, EX.scheme))

        converted = self._convert_and_parse(tmp_path, g)

        history_notes = list(converted.objects(EX.collection1, SKOS.historyNote))
        assert len(history_notes) == 1
        assert str(history_notes[0]) == HISTORY_NOTE_FIRST_TIME


class TestConvert043EdgeCases:
    """Additional tests for convert_043 edge cases."""

    def _convert_and_parse(self, tmp_path, graph, *, vocab_config=None):
        """Convert graph via 043->v1 pipeline and return parsed result."""
        input_path = tmp_path / "test_043.ttl"
        graph.serialize(destination=str(input_path), format="turtle")
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(
            input_path,
            output_path,
            vocab_config=vocab_config,
            output_format="turtle",
        )
        return Graph().parse(output_path, format="turtle"), output_path

    def test_no_concept_scheme_warning(self, tmp_path, caplog):
        """Test warning when graph has no ConceptScheme."""
        # Create RDF without ConceptScheme
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test", lang="en")))

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
        )

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")
        output_path = tmp_path / "test_v1.ttl"

        with caplog.at_level(logging.WARNING):
            convert_rdf_043_to_v1(input_path, output_path, vocab_config=vocab_config)

        assert "No ConceptScheme found" in caplog.text

    def test_voc4cat_version_env_var(self, tmp_path, monkeypatch):
        """Test VOC4CAT_VERSION environment variable overrides version."""

        monkeypatch.setenv("VOC4CAT_VERSION", "2.0.0-test")

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))
        g.add((EX.scheme, OWL.versionInfo, Literal("1.0.0")))

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
        )

        converted, _ = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

        versions = list(converted.objects(EX.scheme, OWL.versionInfo))
        assert len(versions) == 1
        assert str(versions[0]) == "2.0.0-test"

    def test_vocab_config_homepage(self, tmp_path):
        """Test homepage handling in vocab_config."""

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

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
            homepage="https://example.org/home",
        )

        converted, _ = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

        homepages = list(converted.objects(EX.scheme, FOAF.homepage))
        assert len(homepages) == 1
        assert str(homepages[0]) == "https://example.org/home"

    def test_vocab_config_catalogue_pid(self, tmp_path):
        """Test catalogue_pid handling in vocab_config."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

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
            catalogue_pid="https://doi.org/10.1234/example",
        )

        converted, _ = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

        identifiers = list(converted.objects(EX.scheme, DCTERMS.identifier))
        assert len(identifiers) == 1
        assert str(identifiers[0]) == "https://doi.org/10.1234/example"

        see_also = list(converted.objects(EX.scheme, RDFS.seeAlso))
        assert len(see_also) == 1
        assert str(see_also[0]) == "https://doi.org/10.1234/example"

    def test_vocab_config_conforms_to_multiline(self, tmp_path):
        """Test conforms_to multi-line handling in vocab_config."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

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
            conforms_to="https://w3id.org/profile/vocpub\nhttps://w3id.org/profile/skos",
        )

        converted, _ = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

        conforms_to = list(converted.objects(EX.scheme, DCTERMS.conformsTo))
        assert len(conforms_to) == 2
        conforms_to_strs = [str(c) for c in conforms_to]
        assert "https://w3id.org/profile/vocpub" in conforms_to_strs
        assert "https://w3id.org/profile/skos" in conforms_to_strs

    def test_invalid_file_extension(self, tmp_path):
        """Test error when input file has invalid extension."""
        invalid_file = tmp_path / "vocab.txt"
        invalid_file.write_text("# Not an RDF file")

        with pytest.raises(ValueError, match="RDF file formats"):
            convert_rdf_043_to_v1(invalid_file)

    def test_vocab_config_prefix_map(self, tmp_path):
        """Test prefix_map from vocab_config is applied (code path coverage)."""
        # Use a namespace that will be referenced by concept IRI
        MYVOC = Namespace("http://example.org/vocab/")  # noqa: N806

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))
        # Add a concept using the custom namespace so prefix appears in output
        g.add((MYVOC.concept1, RDF.type, SKOS.Concept))
        g.add((MYVOC.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((MYVOC.concept1, SKOS.inScheme, EX.scheme))

        vocab_config = Vocab(
            id_length=7,
            permanent_iri_part="http://example.org/vocab/",
            checks={},
            prefix_map={"myvoc": "http://example.org/vocab/"},
            vocabulary_iri="http://example.org/scheme",
            title="Test",
            description="Test",
            created_date="2024-01-01",
            creator="https://orcid.org/0000-0001-2345-6789",
            repository="https://github.com/test/repo",
        )

        _, output_path = self._convert_and_parse(tmp_path, g, vocab_config=vocab_config)

        # Verify the prefix binding shows in serialized output
        content = output_path.read_text()
        assert "@prefix myvoc:" in content or "myvoc:concept1" in content

    def test_output_format_jsonld(self, tmp_path):
        """Test conversion to JSON-LD format with default output path."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        input_path = tmp_path / "test.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert to JSON-LD without specifying output path
        result_path = convert_rdf_043_to_v1(input_path, output_format="json-ld")

        assert result_path.suffix == ".jsonld"
        assert result_path.stem == "test_v1"
        assert result_path.exists()

    def test_output_format_xml_default_path(self, tmp_path):
        """Test conversion to XML format with default output path."""
        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        input_path = tmp_path / "test.ttl"
        g.serialize(destination=str(input_path), format="turtle")

        # Convert to XML without specifying output path
        result_path = convert_rdf_043_to_v1(input_path, output_format="xml")

        assert result_path.suffix == ".rdf"
        assert result_path.stem == "test_v1"
        assert result_path.exists()

    def test_influenced_by_history_note(self, tmp_path):
        """Test that wasInfluencedBy generates appropriate historyNote."""

        g = Graph()
        g.bind("ex", EX)
        g.bind("skos", SKOS)
        g.bind("prov", PROV)

        g.add((EX.scheme, RDF.type, SKOS.ConceptScheme))
        g.add((EX.scheme, SKOS.prefLabel, Literal("Test Scheme", lang="en")))
        g.add((EX.scheme, DCTERMS.created, Literal("2024-01-01", datatype=XSD.date)))

        # Add concept with prov:wasInfluencedBy (but no hadPrimarySource)
        g.add((EX.concept1, RDF.type, SKOS.Concept))
        g.add((EX.concept1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
        g.add((EX.concept1, SKOS.inScheme, EX.scheme))
        g.add((EX.concept1, PROV.wasInfluencedBy, EX.other_concept))

        input_path = tmp_path / "test_043.ttl"
        g.serialize(destination=str(input_path), format="turtle")
        output_path = tmp_path / "test_v1.ttl"
        convert_rdf_043_to_v1(input_path, output_path)
        converted = Graph().parse(output_path, format="turtle")

        # Should have influenced-by history note
        history_notes = list(converted.objects(EX.concept1, SKOS.historyNote))
        assert len(history_notes) == 1
        assert str(EX.other_concept) in str(history_notes[0])
