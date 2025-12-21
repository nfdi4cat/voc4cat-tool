"""Detailed tests for v1.0 features: multi-language, ordered collections, hierarchies.

This module tests all v1.0 features with programmatically generated test data.
No xlsx files are committed to git - all data is generated via fixtures.

Test coverage:
- Multi-language support for all entities (en, de)
- Ordered collections with position handling
- Collection hierarchies (collection in collection)
- Pydantic model -> RDF conversion
- Roundtrip testing (RDF -> xlsx -> RDF)
"""

import curies
import pytest
from rdflib import (
    DCTERMS,
    RDF,
    RDFS,
    SKOS,
    XSD,
    BNode,
    Graph,
    Literal,
    Namespace,
    Node,
    URIRef,
)
from rdflib import compare as rdf_compare
from rdflib.collection import Collection as RDFCollection

from voc4cat.config import Checks, Vocab
from voc4cat.convert_v1 import (
    aggregate_collections,
    aggregate_concepts,
    build_collection_graph,
    build_collection_hierarchy_map,
    build_concept_graph,
    build_concept_to_ordered_collections_map,
    build_narrower_map,
    excel_to_rdf_v1,
    extract_collections_from_rdf,
    extract_concepts_from_rdf,
    rdf_to_excel_v1,
)
from voc4cat.models_v1 import CollectionV1, ConceptV1

# =============================================================================
# Helper Functions - Graph Builders
# =============================================================================

TEST = Namespace("https://example.org/test/")


def build_multi_lang_concept_graph() -> Graph:
    """Build RDF graph with multi-language concept (en, de).

    Creates:
    - ConceptScheme with en title/definition
    - Concept 0000001 with:
      - en: prefLabel "Photocatalyst", definition, altLabels
      - de: prefLabel "Photokatalysator", definition, altLabels
    """
    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    # ConceptScheme
    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Test Vocabulary", lang="en")))
    g.add(
        (
            scheme,
            SKOS.definition,
            Literal("Test vocabulary for multi-language testing", lang="en"),
        )
    )
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Multi-language concept
    c1 = TEST["0000001"]
    g.add((c1, RDF.type, SKOS.Concept))
    g.add((c1, DCTERMS.identifier, Literal("0000001", datatype=XSD.token)))
    g.add((c1, SKOS.inScheme, scheme))
    g.add((scheme, SKOS.hasTopConcept, c1))
    g.add((c1, SKOS.topConceptOf, scheme))

    # English labels
    g.add((c1, SKOS.prefLabel, Literal("Photocatalyst", lang="en")))
    g.add(
        (
            c1,
            SKOS.definition,
            Literal(
                "A substance that increases the rate of a photoreaction.", lang="en"
            ),
        )
    )
    g.add((c1, SKOS.altLabel, Literal("photo catalyst", lang="en")))
    g.add((c1, SKOS.altLabel, Literal("light-activated catalyst", lang="en")))

    # German labels
    g.add((c1, SKOS.prefLabel, Literal("Photokatalysator", lang="de")))
    g.add(
        (
            c1,
            SKOS.definition,
            Literal(
                "Ein Stoff, der die Geschwindigkeit einer Photoreaktion erhöht.",
                lang="de",
            ),
        )
    )
    g.add((c1, SKOS.altLabel, Literal("Lichtkatalysator", lang="de")))

    return g


def build_multi_lang_collection_graph() -> Graph:
    """Build RDF graph with multi-language collection (en, de).

    Creates:
    - ConceptScheme
    - Concept 0000001
    - Collection with en/de prefLabel and definition
    """
    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    # ConceptScheme
    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Test Vocabulary", lang="en")))
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Concept
    c1 = TEST["0000001"]
    g.add((c1, RDF.type, SKOS.Concept))
    g.add((c1, DCTERMS.identifier, Literal("0000001", datatype=XSD.token)))
    g.add((c1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
    g.add((c1, SKOS.definition, Literal("A test concept", lang="en")))
    g.add((c1, SKOS.inScheme, scheme))
    g.add((scheme, SKOS.hasTopConcept, c1))
    g.add((c1, SKOS.topConceptOf, scheme))

    # Multi-language collection
    coll = TEST["coll001"]
    g.add((coll, RDF.type, SKOS.Collection))
    g.add((coll, DCTERMS.identifier, Literal("coll001", datatype=XSD.token)))
    g.add((coll, SKOS.inScheme, scheme))
    g.add((coll, RDFS.isDefinedBy, scheme))
    g.add((coll, SKOS.member, c1))

    # English labels
    g.add((coll, SKOS.prefLabel, Literal("Test Collection", lang="en")))
    g.add((coll, SKOS.definition, Literal("A collection for testing", lang="en")))

    # German labels
    g.add((coll, SKOS.prefLabel, Literal("Testsammlung", lang="de")))
    g.add((coll, SKOS.definition, Literal("Eine Sammlung zum Testen", lang="de")))

    return g


def build_ordered_collection_graph() -> Graph:
    """Build RDF graph with ordered collection using skos:memberList.

    Creates:
    - ConceptScheme
    - 3 concepts (0000001, 0000002, 0000003)
    - OrderedCollection with memberList in non-sequential order: 2, 3, 1
    """

    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Test Vocabulary", lang="en")))
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Add concepts
    for i in [1, 2, 3]:
        c = TEST[f"000000{i}"]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, DCTERMS.identifier, Literal(f"000000{i}", datatype=XSD.token)))
        g.add((c, SKOS.prefLabel, Literal(f"Concept {i}", lang="en")))
        g.add((c, SKOS.definition, Literal(f"Definition for concept {i}", lang="en")))
        g.add((c, SKOS.inScheme, scheme))
        g.add((scheme, SKOS.hasTopConcept, c))
        g.add((c, SKOS.topConceptOf, scheme))

    # Ordered collection with specific order: 2, 3, 1 (to test non-sequential)
    coll = TEST["coll001"]
    g.add((coll, RDF.type, SKOS.OrderedCollection))
    g.add((coll, DCTERMS.identifier, Literal("coll001", datatype=XSD.token)))
    g.add((coll, SKOS.prefLabel, Literal("Ordered Test Collection", lang="en")))
    g.add(
        (coll, SKOS.definition, Literal("A collection with ordered members", lang="en"))
    )
    g.add((coll, SKOS.inScheme, scheme))
    g.add((coll, RDFS.isDefinedBy, scheme))

    # Create memberList as RDF List with order: 2, 3, 1
    list_node = BNode()
    member_refs: list[Node] = [TEST["0000002"], TEST["0000003"], TEST["0000001"]]
    RDFCollection(g, list_node, member_refs)
    g.add((coll, SKOS.memberList, list_node))

    return g


def build_collection_hierarchy_graph() -> Graph:
    """Build RDF graph with nested collection hierarchy.

    Structure:
    - ConceptScheme
    - Parent collection (coll001) containing child collection (coll002)
    - Child collection (coll002) containing concepts (0000001, 0000002)
    """
    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Test Vocabulary", lang="en")))
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Add concepts
    for i in [1, 2]:
        c = TEST[f"000000{i}"]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, DCTERMS.identifier, Literal(f"000000{i}", datatype=XSD.token)))
        g.add((c, SKOS.prefLabel, Literal(f"Concept {i}", lang="en")))
        g.add((c, SKOS.definition, Literal(f"Definition for concept {i}", lang="en")))
        g.add((c, SKOS.inScheme, scheme))
        g.add((scheme, SKOS.hasTopConcept, c))
        g.add((c, SKOS.topConceptOf, scheme))

    # Parent collection
    parent = TEST["coll001"]
    g.add((parent, RDF.type, SKOS.Collection))
    g.add((parent, DCTERMS.identifier, Literal("coll001", datatype=XSD.token)))
    g.add((parent, SKOS.prefLabel, Literal("Parent Collection", lang="en")))
    g.add(
        (
            parent,
            SKOS.definition,
            Literal("Parent collection containing child", lang="en"),
        )
    )
    g.add((parent, SKOS.inScheme, scheme))
    g.add((parent, RDFS.isDefinedBy, scheme))

    # Child collection (member of parent)
    child = TEST["coll002"]
    g.add((child, RDF.type, SKOS.Collection))
    g.add((child, DCTERMS.identifier, Literal("coll002", datatype=XSD.token)))
    g.add((child, SKOS.prefLabel, Literal("Child Collection", lang="en")))
    g.add(
        (child, SKOS.definition, Literal("Child collection with concepts", lang="en"))
    )
    g.add((child, SKOS.inScheme, scheme))
    g.add((child, RDFS.isDefinedBy, scheme))

    # Hierarchy: parent contains child
    g.add((parent, SKOS.member, child))

    # Child contains concepts
    g.add((child, SKOS.member, TEST["0000001"]))
    g.add((child, SKOS.member, TEST["0000002"]))

    return g


def build_three_level_hierarchy_graph() -> Graph:
    """Build RDF graph with 3-level collection hierarchy.

    Structure:
    - Grandparent collection (coll001) containing parent (coll002)
    - Parent collection (coll002) containing child (coll003)
    - Child collection (coll003) containing concept (0000001)
    """
    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Test Vocabulary", lang="en")))
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Concept
    c1 = TEST["0000001"]
    g.add((c1, RDF.type, SKOS.Concept))
    g.add((c1, DCTERMS.identifier, Literal("0000001", datatype=XSD.token)))
    g.add((c1, SKOS.prefLabel, Literal("Test Concept", lang="en")))
    g.add((c1, SKOS.definition, Literal("A test concept", lang="en")))
    g.add((c1, SKOS.inScheme, scheme))
    g.add((scheme, SKOS.hasTopConcept, c1))
    g.add((c1, SKOS.topConceptOf, scheme))

    # Grandparent collection
    grandparent = TEST["coll001"]
    g.add((grandparent, RDF.type, SKOS.Collection))
    g.add((grandparent, DCTERMS.identifier, Literal("coll001", datatype=XSD.token)))
    g.add((grandparent, SKOS.prefLabel, Literal("Grandparent Collection", lang="en")))
    g.add((grandparent, SKOS.inScheme, scheme))
    g.add((grandparent, RDFS.isDefinedBy, scheme))

    # Parent collection
    parent = TEST["coll002"]
    g.add((parent, RDF.type, SKOS.Collection))
    g.add((parent, DCTERMS.identifier, Literal("coll002", datatype=XSD.token)))
    g.add((parent, SKOS.prefLabel, Literal("Parent Collection", lang="en")))
    g.add((parent, SKOS.inScheme, scheme))
    g.add((parent, RDFS.isDefinedBy, scheme))

    # Child collection
    child = TEST["coll003"]
    g.add((child, RDF.type, SKOS.Collection))
    g.add((child, DCTERMS.identifier, Literal("coll003", datatype=XSD.token)))
    g.add((child, SKOS.prefLabel, Literal("Child Collection", lang="en")))
    g.add((child, SKOS.inScheme, scheme))
    g.add((child, RDFS.isDefinedBy, scheme))

    # Hierarchy: grandparent -> parent -> child -> concept
    g.add((grandparent, SKOS.member, parent))
    g.add((parent, SKOS.member, child))
    g.add((child, SKOS.member, c1))

    return g


def build_comprehensive_test_graph() -> Graph:  # noqa: PLR0915
    """Build comprehensive graph with all features: multi-lang, ordered, hierarchy.

    Creates:
    - ConceptScheme with en title/definition
    - 3 multi-language concepts (en, de)
    - 1 ordered collection with members
    - 1 regular collection
    - Collection hierarchy (parent -> child)
    """

    g = Graph()
    g.bind("test", TEST)
    g.bind("skos", SKOS)

    # ConceptScheme
    scheme = TEST[""]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Comprehensive Test Vocabulary", lang="en")))
    g.add(
        (
            scheme,
            SKOS.definition,
            Literal("Vocabulary testing all v1.0 features", lang="en"),
        )
    )
    g.add((scheme, DCTERMS.created, Literal("2025-01-01", datatype=XSD.date)))
    g.add((scheme, DCTERMS.identifier, Literal("example.org", datatype=XSD.token)))

    # Concepts with multi-language support
    for i in [1, 2, 3]:
        c = TEST[f"000000{i}"]
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, DCTERMS.identifier, Literal(f"000000{i}", datatype=XSD.token)))
        g.add((c, SKOS.inScheme, scheme))

        if i == 1:
            # Top concept
            g.add((scheme, SKOS.hasTopConcept, c))
            g.add((c, SKOS.topConceptOf, scheme))
        else:
            # Child concepts
            g.add((c, SKOS.broader, TEST["0000001"]))
            g.add((TEST["0000001"], SKOS.narrower, c))

        # English labels
        g.add((c, SKOS.prefLabel, Literal(f"Concept {i}", lang="en")))
        g.add((c, SKOS.definition, Literal(f"Definition for concept {i}", lang="en")))

        # German labels
        g.add((c, SKOS.prefLabel, Literal(f"Konzept {i}", lang="de")))
        g.add((c, SKOS.definition, Literal(f"Definition für Konzept {i}", lang="de")))

    # Ordered collection
    ordered_coll = TEST["coll001"]
    g.add((ordered_coll, RDF.type, SKOS.OrderedCollection))
    g.add((ordered_coll, DCTERMS.identifier, Literal("coll001", datatype=XSD.token)))
    g.add((ordered_coll, SKOS.prefLabel, Literal("Ordered Collection", lang="en")))
    g.add((ordered_coll, SKOS.prefLabel, Literal("Geordnete Sammlung", lang="de")))
    g.add((ordered_coll, SKOS.definition, Literal("An ordered collection", lang="en")))
    g.add(
        (ordered_coll, SKOS.definition, Literal("Eine geordnete Sammlung", lang="de"))
    )
    g.add((ordered_coll, SKOS.inScheme, scheme))
    g.add((ordered_coll, RDFS.isDefinedBy, scheme))

    # memberList for ordered collection
    list_node = BNode()
    member_refs: list[Node] = [TEST["0000002"], TEST["0000003"]]
    RDFCollection(g, list_node, member_refs)
    g.add((ordered_coll, SKOS.memberList, list_node))

    # Parent collection (unordered)
    parent_coll = TEST["coll002"]
    g.add((parent_coll, RDF.type, SKOS.Collection))
    g.add((parent_coll, DCTERMS.identifier, Literal("coll002", datatype=XSD.token)))
    g.add((parent_coll, SKOS.prefLabel, Literal("Parent Collection", lang="en")))
    g.add((parent_coll, SKOS.definition, Literal("A parent collection", lang="en")))
    g.add((parent_coll, SKOS.inScheme, scheme))
    g.add((parent_coll, RDFS.isDefinedBy, scheme))

    # Child collection (member of parent)
    child_coll = TEST["coll003"]
    g.add((child_coll, RDF.type, SKOS.Collection))
    g.add((child_coll, DCTERMS.identifier, Literal("coll003", datatype=XSD.token)))
    g.add((child_coll, SKOS.prefLabel, Literal("Child Collection", lang="en")))
    g.add((child_coll, SKOS.definition, Literal("A child collection", lang="en")))
    g.add((child_coll, SKOS.inScheme, scheme))
    g.add((child_coll, RDFS.isDefinedBy, scheme))
    g.add((child_coll, SKOS.member, TEST["0000001"]))

    # Hierarchy: parent contains child
    g.add((parent_coll, SKOS.member, child_coll))

    return g


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_vocab_config():
    """Minimal Vocab config for testing."""
    return Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/test/",
        checks=Checks(allow_delete=False),
        prefix_map={"test": "https://example.org/test/"},
        vocabulary_iri="https://example.org/test/",
        title="Test Vocabulary",
        description="Test vocabulary for comprehensive testing",
        created_date="2025-01-01",
        creator="https://orcid.org/0000-0001-2345-6789",
        repository="https://github.com/test/vocab",
    )


@pytest.fixture
def multi_lang_concept_graph():
    """Graph with multi-language concept."""
    return build_multi_lang_concept_graph()


@pytest.fixture
def multi_lang_collection_graph():
    """Graph with multi-language collection."""
    return build_multi_lang_collection_graph()


@pytest.fixture
def ordered_collection_graph():
    """Graph with ordered collection."""
    return build_ordered_collection_graph()


@pytest.fixture
def collection_hierarchy_graph():
    """Graph with nested collections."""
    return build_collection_hierarchy_graph()


@pytest.fixture
def three_level_hierarchy_graph():
    """Graph with three-level collection hierarchy."""
    return build_three_level_hierarchy_graph()


# Auto-generated predicates to exclude from roundtrip comparison
AUTO_GENERATED_PREDICATES = {
    DCTERMS.provenance,  # Git blame URL (env-dependent)
    RDFS.seeAlso,  # Also contains provenance URL
    SKOS.historyNote,  # Auto-generated for concepts/collections without provenance
}


# =============================================================================
# Multi-Language Tests
# =============================================================================


def test_concept_multi_language_labels_definitions(
    multi_lang_concept_graph, minimal_vocab_config, tmp_path, monkeypatch
):
    """Test concepts with en/de prefLabel and definition.

    Verifies:
    1. RDF extraction groups by IRI then language
    2. English is ordered first
    3. Both languages preserved in roundtrip
    """

    # Disable provenance generation for clean comparison
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    # Extract concepts from RDF
    concepts_data = extract_concepts_from_rdf(multi_lang_concept_graph)

    # Verify structure
    concept_iri = "https://example.org/test/0000001"
    assert concept_iri in concepts_data
    assert "en" in concepts_data[concept_iri]
    assert "de" in concepts_data[concept_iri]

    # Verify English is first (ordered dict)
    first_lang = next(iter(concepts_data[concept_iri].keys()))
    assert first_lang == "en"

    # Verify labels
    assert concepts_data[concept_iri]["en"]["preferred_label"] == "Photocatalyst"
    assert concepts_data[concept_iri]["de"]["preferred_label"] == "Photokatalysator"

    # Test roundtrip preservation
    ttl_path = tmp_path / "multi_lang.ttl"
    multi_lang_concept_graph.serialize(destination=str(ttl_path), format="turtle")

    xlsx_path = tmp_path / "multi_lang.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)

    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    # Verify both languages present in roundtrip
    c1 = URIRef(concept_iri)
    pref_labels = list(roundtrip.objects(c1, SKOS.prefLabel))
    assert len(pref_labels) == 2

    labels_by_lang = {str(lbl.language): str(lbl) for lbl in pref_labels}
    assert labels_by_lang["en"] == "Photocatalyst"
    assert labels_by_lang["de"] == "Photokatalysator"


def test_concept_multi_language_alternate_labels(
    multi_lang_concept_graph, minimal_vocab_config, tmp_path, monkeypatch
):
    """Test alternate labels with multiple languages.

    Verifies:
    1. Multiple altLabels per language are extracted
    2. All altLabels preserved in roundtrip
    """
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    concepts_data = extract_concepts_from_rdf(multi_lang_concept_graph)
    concept_iri = "https://example.org/test/0000001"

    # Verify English altLabels
    en_alt = concepts_data[concept_iri]["en"]["alternate_labels"]
    assert "photo catalyst" in en_alt
    assert "light-activated catalyst" in en_alt

    # Verify German altLabels
    de_alt = concepts_data[concept_iri]["de"]["alternate_labels"]
    assert "Lichtkatalysator" in de_alt

    # Test roundtrip
    ttl_path = tmp_path / "alt_labels.ttl"
    multi_lang_concept_graph.serialize(destination=str(ttl_path), format="turtle")

    xlsx_path = tmp_path / "alt_labels.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)

    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    c1 = URIRef(concept_iri)
    alt_labels = list(roundtrip.objects(c1, SKOS.altLabel))

    # Should have 3 altLabels total (2 en + 1 de)
    assert len(alt_labels) == 3

    en_labels = [str(lbl) for lbl in alt_labels if lbl.language == "en"]
    de_labels = [str(lbl) for lbl in alt_labels if lbl.language == "de"]

    assert "photo catalyst" in en_labels
    assert "light-activated catalyst" in en_labels
    assert "Lichtkatalysator" in de_labels


def test_collection_multi_language_labels_definitions(
    multi_lang_collection_graph, minimal_vocab_config, tmp_path, monkeypatch
):
    """Test collections with en/de prefLabel and definition."""
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    collections_data = extract_collections_from_rdf(multi_lang_collection_graph)
    coll_iri = "https://example.org/test/coll001"

    assert coll_iri in collections_data
    assert "en" in collections_data[coll_iri]
    assert "de" in collections_data[coll_iri]

    assert collections_data[coll_iri]["en"]["preferred_label"] == "Test Collection"
    assert collections_data[coll_iri]["de"]["preferred_label"] == "Testsammlung"

    # Test roundtrip
    ttl_path = tmp_path / "coll_multi_lang.ttl"
    multi_lang_collection_graph.serialize(destination=str(ttl_path), format="turtle")

    xlsx_path = tmp_path / "coll_multi_lang.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)

    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    coll = URIRef(coll_iri)
    pref_labels = list(roundtrip.objects(coll, SKOS.prefLabel))
    assert len(pref_labels) == 2

    labels_by_lang = {str(lbl.language): str(lbl) for lbl in pref_labels}
    assert labels_by_lang["en"] == "Test Collection"
    assert labels_by_lang["de"] == "Testsammlung"


def test_multi_language_english_first_ordering(multi_lang_concept_graph):
    """Test that English is ordered first in extracted data."""

    concepts_data = extract_concepts_from_rdf(multi_lang_concept_graph)
    concept_iri = "https://example.org/test/0000001"

    # Get the language keys in order
    lang_keys = list(concepts_data[concept_iri].keys())

    # English should always be first
    assert lang_keys[0] == "en"


# =============================================================================
# Ordered Collection Tests
# =============================================================================


def test_ordered_collection_position_one_indexed(ordered_collection_graph):
    """Test that positions are 1-indexed (first member is position 1)."""

    c2o_map = build_concept_to_ordered_collections_map(ordered_collection_graph)

    coll_iri = "https://example.org/test/coll001"

    # Order was: 0000002 at pos 1, 0000003 at pos 2, 0000001 at pos 3
    assert c2o_map["https://example.org/test/0000002"][coll_iri] == 1
    assert c2o_map["https://example.org/test/0000003"][coll_iri] == 2
    assert c2o_map["https://example.org/test/0000001"][coll_iri] == 3


def test_ordered_collection_memberlist_rdf_structure(ordered_collection_graph):
    """Test that OrderedCollection uses skos:memberList with RDF List."""
    g = ordered_collection_graph
    coll_iri = "https://example.org/test/coll001"
    coll = URIRef(coll_iri)

    # Verify it's an OrderedCollection
    assert (coll, RDF.type, SKOS.OrderedCollection) in g

    # Verify memberList exists
    member_list = g.value(coll, SKOS.memberList)
    assert member_list is not None

    # Parse the RDF List and verify order
    rdf_list = RDFCollection(g, member_list)
    members = list(rdf_list)

    assert len(members) == 3
    assert str(members[0]) == "https://example.org/test/0000002"  # Position 1
    assert str(members[1]) == "https://example.org/test/0000003"  # Position 2
    assert str(members[2]) == "https://example.org/test/0000001"  # Position 3


def test_ordered_collection_roundtrip_order_preserved(
    ordered_collection_graph, minimal_vocab_config, tmp_path, monkeypatch
):
    """Test that member order is preserved through RDF -> xlsx -> RDF roundtrip."""
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    # Serialize original graph
    ttl_path = tmp_path / "ordered.ttl"
    ordered_collection_graph.serialize(destination=str(ttl_path), format="turtle")

    # Roundtrip
    xlsx_path = tmp_path / "ordered.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)
    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    # Verify order preserved
    coll = URIRef("https://example.org/test/coll001")
    member_list = roundtrip.value(coll, SKOS.memberList)
    assert member_list is not None

    rdf_list = RDFCollection(roundtrip, member_list)
    members = list(rdf_list)

    # Order should be: 0000002, 0000003, 0000001
    assert str(members[0]).endswith("0000002")
    assert str(members[1]).endswith("0000003")
    assert str(members[2]).endswith("0000001")


def test_ordered_collection_extraction(ordered_collection_graph):
    """Test that ordered collections are correctly identified and extracted."""

    collections_data = extract_collections_from_rdf(ordered_collection_graph)
    coll_iri = "https://example.org/test/coll001"

    assert coll_iri in collections_data
    # Check the ordered flag
    assert collections_data[coll_iri]["en"]["ordered"] is True
    # Check ordered_members list
    ordered_members = collections_data[coll_iri]["en"]["ordered_members"]
    assert len(ordered_members) == 3
    assert ordered_members[0] == "https://example.org/test/0000002"
    assert ordered_members[1] == "https://example.org/test/0000003"
    assert ordered_members[2] == "https://example.org/test/0000001"


# =============================================================================
# Collection Hierarchy Tests
# =============================================================================


def test_collection_in_collection_via_parent_iris(collection_hierarchy_graph):
    """Test that parent_collection_iris correctly represents hierarchy."""

    hierarchy_map = build_collection_hierarchy_map(collection_hierarchy_graph)

    # Child collection should have parent
    child_iri = "https://example.org/test/coll002"
    parent_iri = "https://example.org/test/coll001"

    assert child_iri in hierarchy_map
    assert parent_iri in hierarchy_map[child_iri]


def test_multi_level_collection_hierarchy(three_level_hierarchy_graph):
    """Test 3-level collection hierarchy: grandparent -> parent -> child."""
    hierarchy_map = build_collection_hierarchy_map(three_level_hierarchy_graph)

    grandparent_iri = "https://example.org/test/coll001"
    parent_iri = "https://example.org/test/coll002"
    child_iri = "https://example.org/test/coll003"

    # Parent should have grandparent as parent
    assert parent_iri in hierarchy_map
    assert grandparent_iri in hierarchy_map[parent_iri]

    # Child should have parent as parent
    assert child_iri in hierarchy_map
    assert parent_iri in hierarchy_map[child_iri]


def test_collection_hierarchy_roundtrip(
    collection_hierarchy_graph, minimal_vocab_config, tmp_path, monkeypatch
):
    """Test that collection hierarchy is preserved through roundtrip.

    Verifies that skos:member relationships for collection-in-collection are
    correctly roundtripped: RDF -> XLSX (parent_collection_iris) -> RDF (skos:member).
    """
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    # Serialize original
    ttl_path = tmp_path / "hierarchy.ttl"
    collection_hierarchy_graph.serialize(destination=str(ttl_path), format="turtle")

    # Roundtrip
    xlsx_path = tmp_path / "hierarchy.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)
    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    # Verify hierarchy preserved: parent should have child as member
    parent = URIRef("https://example.org/test/coll001")
    child = URIRef("https://example.org/test/coll002")

    members = list(roundtrip.objects(parent, SKOS.member))
    assert child in members, (
        f"Child collection not found in parent's skos:member. Members: {members}"
    )


# =============================================================================
# Pydantic Model -> RDF Tests
# =============================================================================


def test_concept_v1_to_aggregated_to_rdf():
    """Test ConceptV1 -> AggregatedConcept -> RDF graph conversion."""

    # Build converter
    prefix_map = {"test": "https://example.org/test/"}
    converter = curies.Converter.from_prefix_map(prefix_map)

    concept_rows = [
        ConceptV1(
            concept_iri="test:0000001",
            language_code="en",
            preferred_label="Test Concept",
            definition="A test concept",
            alternate_labels="alias1 | alias2",
        ),
        ConceptV1(
            concept_iri="test:0000001",
            language_code="de",
            preferred_label="Testkonzept",
            definition="Ein Testkonzept",
        ),
    ]

    concepts = aggregate_concepts(concept_rows, converter)

    # Verify aggregation
    iri = "https://example.org/test/0000001"
    assert iri in concepts
    concept = concepts[iri]
    assert concept.pref_labels["en"] == "Test Concept"
    assert concept.pref_labels["de"] == "Testkonzept"
    assert concept.alt_labels["en"] == ["alias1", "alias2"]

    # Build RDF graph
    scheme_iri = URIRef("https://example.org/test/")
    narrower_map = build_narrower_map(concepts)
    graph = build_concept_graph(concept, scheme_iri, narrower_map)

    c = URIRef(iri)

    # Verify multi-language labels
    pref_labels = list(graph.objects(c, SKOS.prefLabel))
    assert len(pref_labels) == 2

    alt_labels = list(graph.objects(c, SKOS.altLabel))
    assert len(alt_labels) == 2


def test_collection_v1_to_aggregated_to_rdf():
    """Test CollectionV1 -> AggregatedCollection -> RDF graph conversion."""

    # Build converter
    prefix_map = {"test": "https://example.org/test/"}
    converter = curies.Converter.from_prefix_map(prefix_map)

    collection_rows = [
        CollectionV1(
            collection_iri="test:coll001",
            language_code="en",
            preferred_label="Test Collection",
            definition="A test collection",
            ordered="Yes",
        ),
        CollectionV1(
            collection_iri="test:coll001",
            language_code="de",
            preferred_label="Testsammlung",
            definition="Eine Testsammlung",
        ),
    ]

    collections = aggregate_collections(collection_rows, converter)

    # Verify aggregation
    iri = "https://example.org/test/coll001"
    assert iri in collections
    coll = collections[iri]
    assert coll.ordered is True
    assert coll.pref_labels["en"] == "Test Collection"
    assert coll.pref_labels["de"] == "Testsammlung"

    # Build RDF graph
    scheme_iri = URIRef("https://example.org/test/")
    ordered_members = {iri: ["https://example.org/test/0000001"]}
    graph = build_collection_graph(coll, scheme_iri, {}, ordered_members)

    c = URIRef(iri)

    # Verify it's an OrderedCollection
    assert (c, RDF.type, SKOS.OrderedCollection) in graph

    # Verify multi-language labels
    pref_labels = list(graph.objects(c, SKOS.prefLabel))
    assert len(pref_labels) == 2


# =============================================================================
# Comprehensive Roundtrip Test
# =============================================================================


def test_roundtrip_full_vocabulary_isomorphic(
    tmp_path, minimal_vocab_config, monkeypatch
):
    """Test complete roundtrip with isomorphic graph comparison.

    Creates a comprehensive vocabulary with:
    - Multi-language concepts (en, de)
    - Ordered collection
    - Collection hierarchy

    Known limitation in roundtrip:
    - ConceptScheme metadata comes from config, not original RDF (read-only sheet)

    This test verifies concept, collection, and hierarchy data fidelity.
    """

    # Disable provenance (generated from env vars, not roundtripped)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    # Build comprehensive test graph
    original = build_comprehensive_test_graph()

    # Serialize to file
    ttl_path = tmp_path / "comprehensive.ttl"
    original.serialize(destination=str(ttl_path), format="turtle")

    # Roundtrip
    xlsx_path = tmp_path / "comprehensive.xlsx"
    rdf_to_excel_v1(ttl_path, xlsx_path, vocab_config=minimal_vocab_config)
    roundtrip = excel_to_rdf_v1(
        xlsx_path, output_type="graph", vocab_config=minimal_vocab_config
    )

    # Filter graphs to exclude known differences
    SDO = Namespace("https://schema.org/")  # noqa: N806

    def filter_for_comparison(g: Graph, exclude_scheme_triples: bool = True) -> Graph:
        """Filter graph for comparison, excluding known non-roundtripped data."""
        scheme_iri = URIRef("https://example.org/test/")
        filtered = Graph()
        for s, p, o in g:
            # Skip provenance predicates
            if p in AUTO_GENERATED_PREDICATES:
                continue
            # Skip ConceptScheme triples (metadata comes from config)
            # but Keep hasTopConcept relationships
            if exclude_scheme_triples and s == scheme_iri and p != SKOS.hasTopConcept:
                continue
            # Skip Person/Organization triples (auto-generated from config creator/publisher)
            if (s, RDF.type, SDO.Organization) in g or (s, RDF.type, SDO.Person) in g:
                continue
            filtered.add((s, p, o))
        return filtered

    original_filtered = filter_for_comparison(original)
    roundtrip_filtered = filter_for_comparison(roundtrip)

    # Compare graphs
    assert rdf_compare.isomorphic(original_filtered, roundtrip_filtered), (
        "Graphs not isomorphic (comprehensive vocabulary roundtrip)"
    )
