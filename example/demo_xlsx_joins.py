#!/usr/bin/env python3
"""
Demo: Joined Models for XLSX Unified Processor

This demo specifically showcases the joined models functionality for vocabulary
management, demonstrating how to handle related Pydantic models in a unified
table format.

Features demonstrated:
- Joined table format for related models
- Configuration for model relationships
- Custom styling and formatting
- Round-trip data integrity verification
- Vocabulary management use cases
"""

import sys
from pathlib import Path

from pydantic import BaseModel, Field

from voc4cat.xlsx_api import XLSXProcessorFactory
from voc4cat.xlsx_table import JoinConfiguration, XLSXTableConfig


def demo_joined_models(demo_file: Path):
    """Demonstrate joined models functionality for vocabulary management."""

    print("\n" + "=" * 60)
    print("DEMO: Joined Models for Vocabulary Management")
    print("=" * 60)

    # Define models for vocabulary management (similar to xlsx_connector.py)
    class ConceptTranslation(BaseModel):
        """Represents a translation of a concept in a specific language."""

        concept_uri: str
        language_code: str
        pref_label: str | None = None
        alt_labels: list[str] = Field(default_factory=list)
        definition: str | None = None

    class Concept(BaseModel):
        """Represents a concept in a vocabulary."""

        concept_uri: str
        translations: list[ConceptTranslation] = Field(default_factory=list)
        children: list[str] = Field(default_factory=list)
        provenance: str | None = None
        source_vocab: str | None = None

    # 1. Create sample vocabulary data
    print("\n1. Creating Sample Vocabulary Data")
    print("-" * 40)

    concept1 = Concept(
        concept_uri="http://example.org/vocab/concept1",
        children=["http://example.org/vocab/concept2"],
        provenance="Created by expert",
        source_vocab="example_vocab",
        translations=[
            ConceptTranslation(
                concept_uri="http://example.org/vocab/concept1",
                language_code="en",
                pref_label="First Concept",
                alt_labels=["Primary Concept", "Main Concept"],
                definition="This is the first concept",
            ),
            ConceptTranslation(
                concept_uri="http://example.org/vocab/concept1",
                language_code="de",
                pref_label="Erstes Konzept",
                alt_labels=["Primäres Konzept"],
                definition="Dies ist das erste Konzept",
            ),
        ],
    )

    concept2 = Concept(
        concept_uri="http://example.org/vocab/concept2",
        children=[],
        provenance="Created by expert",
        source_vocab="example_vocab",
        translations=[
            ConceptTranslation(
                concept_uri="http://example.org/vocab/concept2",
                language_code="en",
                pref_label="Second Concept",
                alt_labels=["Secondary Concept"],
                definition="This is the second concept",
            )
        ],
    )

    vocabulary_concepts = [concept1, concept2]
    print(f"✓ Created {len(vocabulary_concepts)} concepts with translations")

    # 2. Create join configuration
    print("\n2. Creating Join Configuration")
    print("-" * 40)

    join_config = JoinConfiguration(
        primary_model=Concept,
        related_models={"translations": ConceptTranslation},
        join_keys={"translations": "concept_uri"},
        flattened_fields=[
            "concept_uri",
            "language_code",
            "pref_label",
            "alt_labels",
            "definition",
            "children",
            "provenance",
            "source_vocab",
        ],
        field_mappings={
            "concept_uri": ("primary", "concept_uri"),
            "language_code": ("related", "language_code"),
            "pref_label": ("related", "pref_label"),
            "alt_labels": ("related", "alt_labels"),
            "definition": ("related", "definition"),
            "children": ("primary", "children"),
            "provenance": ("primary", "provenance"),
            "source_vocab": ("primary", "source_vocab"),
        },
        list_fields={"alt_labels", "children"},
    )
    print("✓ Created join configuration for Concept ↔ ConceptTranslation")

    # 3. Create joined table processor and export
    print("\n3. Export with Joined Table Processor")
    print("-" * 40)

    processor = XLSXProcessorFactory.create_joined_table_processor(join_config)
    sheet_name = "Vocabulary_Joined"

    processor.export(vocabulary_concepts, demo_file, sheet_name)
    print(f"✓ Exported vocabulary to sheet '{sheet_name}' using joined table format")

    # 4. Import vocabulary back from Excel
    print("\n4. Import and Verify Round-trip Consistency")
    print("-" * 40)

    try:
        imported_concepts = processor.import_data(demo_file, sheet_name=sheet_name)
        print(f"✓ Imported {len(imported_concepts)} concepts from Excel")

        # Display imported data
        for concept in imported_concepts:
            print(f"  Concept: {concept.concept_uri}")
            print(f"    Children: {concept.children}")
            print(f"    Provenance: {concept.provenance}")
            for translation in concept.translations:
                print(
                    f"    Translation ({translation.language_code}): {translation.pref_label}"
                )
                print(f"      Alt labels: {translation.alt_labels}")
                print(f"      Definition: {translation.definition}")

        # Verify round-trip consistency
        print("\n  Verifying round-trip consistency...")
        original_data = {
            concept.concept_uri: {
                "children": concept.children,
                "provenance": concept.provenance,
                "translations": len(concept.translations),
            }
            for concept in vocabulary_concepts
        }

        imported_data = {
            concept.concept_uri: {
                "children": concept.children,
                "provenance": concept.provenance,
                "translations": len(concept.translations),
            }
            for concept in imported_concepts
        }

        if original_data == imported_data:
            print("  ✓ Round-trip consistency verified!")
        else:
            print("  ✗ Round-trip consistency failed!")
            print(f"  Original: {original_data}")
            print(f"  Imported: {imported_data}")

    except Exception as e:
        print(f"  ✗ Import error: {e}")

    # 5. Example with custom configuration
    print("\n5. Custom Configuration Example")
    print("-" * 40)

    custom_config = XLSXTableConfig(
        title="Custom Vocabulary Export",
        table_style="TableStyleLight10",
    )

    custom_processor = XLSXProcessorFactory.create_joined_table_processor(
        join_config, custom_config
    )

    custom_sheet_name = "Vocabulary_Custom_Joined"
    custom_processor.export(vocabulary_concepts, demo_file, custom_sheet_name)
    print(f"✓ Exported vocabulary with custom styling to sheet '{custom_sheet_name}'")

    print("\n✓ Joined models demonstration complete!")
    print("Key features demonstrated:")
    print("  - Clean architecture with formatters and processors")
    print("  - Reuses existing serialization engine")
    print("  - Supports field metadata (descriptions, units, meanings)")
    print("  - Configurable styling and layout")
    print("  - Round-trip consistency (export → import → export)")


def run_joins_demo():
    """Run all joined models demonstrations."""

    print("XLSX UNIFIED PROCESSOR - JOINED MODELS DEMO")
    print("=" * 60)
    print("This demo specifically showcases the joined models functionality")
    print("for handling related Pydantic models in Excel format.")

    # Demo file for joined models
    demo_file = Path("xlsx_unified_joins_demo.xlsx")

    try:
        demo_joined_models(demo_file)

        print("\n" + "=" * 60)
        print("✅ ALL JOINED MODELS DEMONSTRATIONS COMPLETED!")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("• Basic joined table format for related models")
        print("• Custom join configurations")
        print("• Custom styling and formatting")
        print("• Round-trip data integrity verification")
        print("• Vocabulary management use cases")

        print(f"\nGenerated Demo File: {demo_file.absolute()}")
        print("\nWorkbook Sheets:")
        print("• Vocabulary_Joined - Basic joined models demonstration")
        print("• Vocabulary_Custom_Joined - Custom styling example")

        print("\nTotal: 2 Excel sheets demonstrating joined models functionality")
        print("\nThe joined models feature is ready for vocabulary management!")

    except Exception as e:
        print(f"\n❌ Joined models demo failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


def main():
    """Run the joined models demonstration."""
    return run_joins_demo()


if __name__ == "__main__":
    sys.exit(main())
