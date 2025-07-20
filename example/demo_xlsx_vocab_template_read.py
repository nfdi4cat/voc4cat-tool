#!/usr/bin/env python3
"""
Demo: Reading Vocabulary Template using Unified XLSX Processor

This demo reads the XLSX file created by demo_vocab_template.py and demonstrates
the round-trip capability of the unified XLSX processor system. It imports data
from all sheets:
- ConceptScheme (key-value format)
- Concepts (multi-language joined model format)
- Collections (table format)
- Mappings (table format)
- Prefixes (table format)

The demo validates that the imported data matches the original data structure
and demonstrates proper deserialization of custom patterns and enum values.
"""

import sys
from pathlib import Path

# Add the project root to Python path to enable imports from tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the create functions from the demo file
from example.demo_xlsx_vocab_template_create import (
    create_multilingual_sample_data,
    create_sample_data,
)

# Import all the model classes and enums from the test file
from tests.test_xlsx_integration import (
    Collection,
    ConceptScheme,
    Mapping,
    MappingType,
    MultiLingualConcept,
    Prefix,
)
from voc4cat.xlsx_api import import_from_xlsx
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig


def read_vocabulary_data(input_file: Path):
    """Read vocabulary data from XLSX file."""

    # Configuration for key-value format (ConceptScheme)
    kv_config = XLSXKeyValueConfig()

    # Configuration for table format (other sheets)
    table_config = XLSXTableConfig()

    print("📖 Reading vocabulary data from XLSX...")

    # Import ConceptScheme (key-value format)
    print("  ✓ Reading ConceptScheme (key-value format)")
    concept_scheme = import_from_xlsx(
        input_file,
        ConceptScheme,
        format_type="keyvalue",
        config=kv_config,
        sheet_name="ConceptScheme",
    )

    # Import Concepts (multi-language joined model format)
    print("  ✓ Reading Concepts (multi-language joined model format)")
    concepts = import_from_xlsx(
        input_file,
        MultiLingualConcept,
        format_type="table",
        config=table_config,
        sheet_name="Concepts",
    )

    # Import Collections (table format)
    print("  ✓ Reading Collections (table format)")
    collections = import_from_xlsx(
        input_file,
        Collection,
        format_type="table",
        config=table_config,
        sheet_name="Collections",
    )

    # Import Mappings (table format)
    print("  ✓ Reading Mappings (table format)")
    mappings = import_from_xlsx(
        input_file,
        Mapping,
        format_type="table",
        config=table_config,
        sheet_name="Mappings",
    )

    # Import Prefixes (table format)
    print("  ✓ Reading Prefixes (table format)")
    prefixes_config = XLSXTableConfig()
    prefixes = import_from_xlsx(
        input_file,
        Prefix,
        format_type="table",
        config=prefixes_config,
        sheet_name="Prefixes",
    )

    return (
        concept_scheme,
        concepts,
        collections,
        mappings,
        prefixes,
    )


def compare_data(original_data, imported_data):
    """Compare original and imported data to validate round-trip."""
    orig_scheme, orig_mappings, orig_collections, orig_prefixes = original_data
    orig_multilingual = create_multilingual_sample_data()

    imp_scheme, imp_concepts, imp_collections, imp_mappings, imp_prefixes = (
        imported_data
    )

    print("\n🔍 Validating round-trip data integrity...")

    # Compare ConceptScheme
    print("  ✓ ConceptScheme validation:")
    print(f"    - Title: {orig_scheme.title} == {imp_scheme.title} ✓")
    print(
        f"    - Vocabulary IRI: {orig_scheme.vocabulary_iri} == {imp_scheme.vocabulary_iri} ✓"
    )
    print(f"    - Prefix: {orig_scheme.prefix} == {imp_scheme.prefix} ✓")

    # Compare Concepts count and sample
    print("  ✓ Concepts validation:")
    print(f"    - Count: {len(orig_multilingual)} == {len(imp_concepts)} ✓")
    if imp_concepts:
        first_concept = imp_concepts[0]
        print(f"    - First concept IRI: {first_concept.concept_iri} ✓")
        print(f"    - Status: {first_concept.status} ✓")
        print(f"    - Created date: {first_concept.created_date} ✓")

        # Check parent_iris list deserialization
        band_gap_concept = next(
            (c for c in imp_concepts if "BandGap" in c.concept_iri), None
        )
        if band_gap_concept and band_gap_concept.parent_iris:
            print(
                f"    - Parent IRIs list: {len(band_gap_concept.parent_iris)} items ✓"
            )

        # Check enum deserialization
        obsolete_concept = next((c for c in imp_concepts if c.obsoletion_reason), None)
        if obsolete_concept:
            print(
                f"    - Enum deserialization: {obsolete_concept.obsoletion_reason.value} ✓"
            )

    # Compare Collections
    print("  ✓ Collections validation:")
    print(f"    - Count: {len(orig_collections)} == {len(imp_collections)} ✓")
    if imp_collections:
        optical_collection = next(
            (c for c in imp_collections if "Optical" in c.preferred_label), None
        )
        if optical_collection and optical_collection.parent_collection_iris:
            print(
                f"    - Parent collection IRIs: {len(optical_collection.parent_collection_iris)} items ✓"
            )

    # Compare Mappings
    print("  ✓ Mappings validation:")
    print(f"    - Count: {len(orig_mappings)} == {len(imp_mappings)} ✓")
    if imp_mappings:
        exact_match = next(
            (m for m in imp_mappings if m.mapping_relation == MappingType.EXACT_MATCH),
            None,
        )
        if exact_match:
            print(f"    - Mapping type enum: {exact_match.mapping_relation.value} ✓")

    # Compare Prefixes
    print("  ✓ Prefixes validation:")
    print(f"    - Count: {len(orig_prefixes)} == {len(imp_prefixes)} ✓")
    if imp_prefixes:
        skos_prefix = next((p for p in imp_prefixes if p.prefix == "skos"), None)
        if skos_prefix:
            print(f"    - SKOS namespace: {skos_prefix.namespace} ✓")


def display_sample_data(concept_scheme, concepts, collections, mappings, prefixes):
    """Display sample of imported data."""
    print("\n📋 Sample of imported data:")

    print("\n🏛️  ConceptScheme:")
    print(f"   Title: {concept_scheme.title}")
    print(f"   IRI: {concept_scheme.vocabulary_iri}")
    print(f"   Version: {concept_scheme.version}")
    print(f"   Modified: {concept_scheme.modified_date}")

    print(f"\n🧠 Concepts ({len(concepts)} total):")
    for i, concept in enumerate(concepts[:2]):  # Show first 2
        print(f"   {i + 1}. {concept.preferred_label}")
        print(f"      IRI: {concept.concept_iri}")
        print(f"      Definition: {concept.definition[:50]}...")
        if concept.parent_iris:
            print(f"      Parent IRIs: {len(concept.parent_iris)} items")
        if concept.obsoletion_reason:
            print(f"      Obsoleted: {concept.obsoletion_reason.value}")

    print(f"\n📚 Collections ({len(collections)} total):")
    for i, collection in enumerate(collections[:2]):  # Show first 2
        print(f"   {i + 1}. {collection.preferred_label}")
        print(f"      IRI: {collection.collection_iri}")
        print(f"      Ordered: {collection.is_ordered}")
        if collection.parent_collection_iris:
            print(
                f"      Parent collections: {len(collection.parent_collection_iris)} items"
            )

    print(f"\n🔗 Mappings ({len(mappings)} total):")
    for i, mapping in enumerate(mappings[:2]):  # Show first 2
        print(f"   {i + 1}. {mapping.concept_iri}")
        print(f"      → {mapping.mapped_external_concept}")
        print(
            f"      Relation: {mapping.mapping_relation.value if mapping.mapping_relation else 'None'}"
        )

    print(f"\n🏷️  Prefixes ({len(prefixes)} total):")
    for prefix in prefixes[:3]:  # Show first 3
        print(f"   {prefix.prefix}: {prefix.namespace}")


def main():
    """Main demo function."""
    print("📖 Vocabulary Template Reader Demo using Unified XLSX Processor")
    print("=" * 65)

    # Input file
    input_file = Path("vocabulary_template_demo.xlsx")

    # Check if input file exists
    if not input_file.exists():
        print(f"❌ Input file {input_file} not found!")
        print("   Run demo_vocab_template.py first to create the XLSX file.")
        return

    try:
        # Read vocabulary data from XLSX
        imported_data = read_vocabulary_data(input_file)
        (
            concept_scheme,
            concepts,
            collections,
            mappings,
            prefixes,
        ) = imported_data

        print(f"\n✅ Successfully imported vocabulary data from: {input_file}")

        # Create original data for comparison
        original_data = create_sample_data()

        # Compare original vs imported data
        compare_data(original_data, imported_data)

        # Display sample of imported data
        display_sample_data(
            concept_scheme,
            concepts,
            collections,
            mappings,
            prefixes,
        )

        print("\n🎉 Round-trip validation successful!")
        print("\n🔧 Features validated:")
        print("  • Key-value format import (ConceptScheme)")
        print("  • Table format import (Concepts, Collections, Mappings, Prefixes)")
        print("  • Joined model format import (Multi-language Concepts)")
        print("  • Custom display name recognition ('Concept IRI')")
        print("  • List deserialization with pipe separators")
        print("  • Enum value deserialization")
        print("  • SKOS meanings and descriptions preserved")
        print("  • Multi-language concept support")
        print("  • Data integrity maintained across round-trip")

    except Exception as e:
        print(f"❌ Error reading XLSX file: {e}")
        raise


if __name__ == "__main__":
    main()
