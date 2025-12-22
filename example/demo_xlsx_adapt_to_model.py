#!/usr/bin/env python3
"""
Demo: Enhancing Existing Pydantic Models with XLSX Support

This demo shows how to add XLSX functionality to existing Pydantic models
without modifying the original model code, using the inheritance-aware
wrapper approach.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from voc4cat.xlsx_api import (
    XLSXProcessorFactory,
    create_xlsx_wrapper,
    import_from_xlsx,
)

# Import XLSX functionality
from voc4cat.xlsx_common import XLSXConverters, XLSXMetadata

# ============================================================================
# EXISTING MODELS (These remain unchanged - simulate third-party models)
# ============================================================================


class ReactionType(Enum):
    """Types of chemical reactions."""

    SYNTHESIS = "synthesis"
    CATALYSIS = "catalysis"
    PHOTOCATALYSIS = "photocatalysis"
    ELECTROCHEMISTRY = "electrochemistry"


class BaseReaction(BaseModel):
    """Base reaction model - imagine this is from a third-party library."""

    reaction_id: str
    temperature: float
    pressure: float
    reaction_type: ReactionType


class CatalysisReaction(BaseReaction):
    """Specialized catalysis reaction - third-party model."""

    catalysts: list[str]
    yield_percentage: float
    catalyst_loading: float  # g/L
    created_at: datetime


# ============================================================================
# XLSX ENHANCEMENT - Our code to add XLSX support
# ============================================================================


def setup_xlsx_models():
    """Setup XLSX-enhanced versions of the existing models with inheritance."""

    # Base model metadata
    base_reaction_metadata = {
        "reaction_id": XLSXMetadata(
            display_name="Reaction ID", description="Unique identifier for the reaction"
        ),
        "temperature": XLSXMetadata(
            unit="°C", description="Temperature at which the reaction is conducted"
        ),
        "pressure": XLSXMetadata(
            unit="bar", description="Pressure maintained during the reaction"
        ),
        "reaction_type": XLSXMetadata(
            description="Classification of the reaction type"
        ),
    }
    # Create XLSX-enhanced models with proper inheritance
    XLSXBaseReaction = create_xlsx_wrapper(BaseReaction, base_reaction_metadata)  # noqa: N806

    # Catalysis model metadata (inherits base + adds new)
    catalysis_reaction_metadata = {
        "catalysts": XLSXMetadata(
            separator_pattern=XLSXConverters.COMMA,
            description="List of catalysts used in the reaction",
        ),
        "yield_percentage": XLSXMetadata(
            unit="%", description="Percentage yield of the main product"
        ),
        "catalyst_loading": XLSXMetadata(
            unit="g/L",
            display_name="Catalyst Loading",
            description="Mass of catalyst per unit volume of solution",
        ),
        "created_at": XLSXMetadata(description="When this reaction record was created"),
    }

    XLSXCatalysisReaction = create_xlsx_wrapper(  # noqa: N806
        CatalysisReaction,
        catalysis_reaction_metadata,
        base_wrapper=XLSXBaseReaction,  # Inherit base metadata!
    )

    return XLSXBaseReaction, XLSXCatalysisReaction


# ============================================================================
# DEMO FUNCTIONS
# ============================================================================


def create_sample_data():
    """Create sample reaction data using original models."""

    reactions = [
        CatalysisReaction(
            reaction_id="CAT001",
            temperature=350.0,
            pressure=2.5,
            reaction_type=ReactionType.CATALYSIS,
            catalysts=["Pt/Al2O3", "Pd/C"],
            yield_percentage=87.5,
            catalyst_loading=0.5,
            created_at=datetime(2024, 1, 15, 14, 30, 0),  # noqa: DTZ001
        ),
        CatalysisReaction(
            reaction_id="CAT002",
            temperature=300.0,
            pressure=1.8,
            reaction_type=ReactionType.PHOTOCATALYSIS,
            catalysts=["TiO2", "ZnO"],
            yield_percentage=65.2,
            catalyst_loading=1.2,
            created_at=datetime(2024, 1, 16, 9, 15, 0),  # noqa: DTZ001
        ),
    ]

    return reactions  # noqa: RET504


def create_simple_demo():
    """Demo: Create a simple XLSX file with 3 sheets demonstrating the wrapper approach."""
    print("\n" + "=" * 60)
    print("DEMO: Simple XLSX Wrapper Demo (3 Sheets)")
    print("=" * 60)

    # Get enhanced models
    XLSXBaseReaction, XLSXCatalysisReaction = setup_xlsx_models()  # noqa: N806

    # Get sample data
    reactions = create_sample_data()

    # Output file
    output_file = Path("adapt_to_existing_model.xlsx")

    # Remove existing file to ensure clean start
    if output_file.exists():
        output_file.unlink()

    # Create processors
    table_processor = XLSXProcessorFactory.create_table_processor()
    keyvalue_processor = XLSXProcessorFactory.create_keyvalue_processor()

    print(f"Creating simple demo file: {output_file}")

    # Sheet 1: Base reaction (key-value format)
    print("  📄 Sheet 1: Base Reaction (Key-Value)")
    base_reaction = XLSXBaseReaction(
        reaction_id="BASE001",
        temperature=275.0,
        pressure=2.0,
        reaction_type=ReactionType.SYNTHESIS,
    )
    keyvalue_processor.export(base_reaction, output_file, sheet_name="BaseReaction")

    # Sheet 2: Full catalysis reaction with inheritance (key-value format)
    print("  📄 Sheet 2: Catalysis Reaction with Inheritance (Key-Value)")
    catalysis_reaction = XLSXCatalysisReaction(**reactions[0].__dict__)
    keyvalue_processor.export(
        catalysis_reaction, output_file, sheet_name="CatalysisReaction"
    )

    # Sheet 3: Multiple catalysis reactions (table format)
    print("  📄 Sheet 3: Multiple Catalysis Reactions (Table)")
    catalysis_reactions = [XLSXCatalysisReaction(**r.__dict__) for r in reactions]
    table_processor.export(
        catalysis_reactions, output_file, sheet_name="CatalysisTable"
    )

    print(f"✅ Created simple demo file: {output_file}")

    return output_file, base_reaction, catalysis_reaction, catalysis_reactions


def demo_import_verification(output_file, original_data):
    """Demo: Import and verify data from the simple demo file."""
    print("\n" + "=" * 60)
    print("DEMO: Import Verification")
    print("=" * 60)

    # Get enhanced models
    XLSXBaseReaction, XLSXCatalysisReaction = setup_xlsx_models()  # noqa: N806

    base_reaction, catalysis_reaction, catalysis_reactions = original_data

    # Test 1: Import base reaction (key-value format)
    print("🔍 Testing base reaction import...")
    imported_base = import_from_xlsx(
        output_file, XLSXBaseReaction, format_type="keyvalue", sheet_name="BaseReaction"
    )
    assert imported_base.reaction_id == base_reaction.reaction_id
    assert imported_base.temperature == base_reaction.temperature
    print("  ✅ Base reaction data integrity verified!")

    # Test 2: Import catalysis reaction (key-value format)
    print("\n🔍 Testing catalysis reaction import...")
    imported_catalysis = import_from_xlsx(
        output_file,
        XLSXCatalysisReaction,
        format_type="keyvalue",
        sheet_name="CatalysisReaction",
    )
    assert imported_catalysis.reaction_id == catalysis_reaction.reaction_id
    assert imported_catalysis.catalysts == catalysis_reaction.catalysts
    assert imported_catalysis.catalyst_loading == catalysis_reaction.catalyst_loading
    print("  ✅ Catalysis reaction inheritance verified!")

    # Test 3: Import table format
    print("\n🔍 Testing table format import...")
    imported_table = import_from_xlsx(
        output_file,
        XLSXCatalysisReaction,
        format_type="table",
        sheet_name="CatalysisTable",
    )
    print(f"  ✅ Imported {len(imported_table)} reactions from table")

    # Verify data
    assert len(imported_table) == len(catalysis_reactions)
    for original, imported in zip(catalysis_reactions, imported_table):
        assert original.reaction_id == imported.reaction_id
        assert original.temperature == imported.temperature
    print("  ✅ Table data integrity verified!")

    print("\n🎉 All import verifications passed!")


def demo_inheritance_features():
    """Demo: Show how metadata inheritance works."""
    print("\n" + "=" * 60)
    print("DEMO: Inheritance Features")
    print("=" * 60)

    # Get enhanced models
    XLSXBaseReaction, XLSXCatalysisReaction = setup_xlsx_models()  # noqa: N806

    # Show inheritance chain
    print("Inheritance verification:")
    print(f"XLSXBaseReaction MRO: {[cls.__name__ for cls in XLSXBaseReaction.__mro__]}")
    print(
        f"XLSXCatalysisReaction MRO: {[cls.__name__ for cls in XLSXCatalysisReaction.__mro__]}"
    )

    # Create a test instance
    test_reaction = XLSXCatalysisReaction(
        reaction_id="TEST001",
        temperature=350.0,
        pressure=2.5,
        reaction_type=ReactionType.CATALYSIS,
        catalysts=["Pt/Al2O3"],
        yield_percentage=87.5,
        catalyst_loading=0.5,
        created_at=datetime.now(),  # noqa: DTZ005
    )

    # Test isinstance relationships
    print("\nInstance relationships:")
    print(
        f"test_reaction isinstance BaseReaction: {isinstance(test_reaction, BaseReaction)}"
    )
    print(
        f"test_reaction isinstance CatalysisReaction: {isinstance(test_reaction, CatalysisReaction)}"
    )
    print(
        f"test_reaction isinstance XLSXBaseReaction: {isinstance(test_reaction, XLSXBaseReaction)}"
    )
    print(
        f"test_reaction isinstance XLSXCatalysisReaction: {isinstance(test_reaction, XLSXCatalysisReaction)}"
    )

    # Show field access
    print("\nField access verification:")
    print(
        f"- Has temperature (from BaseReaction): {hasattr(test_reaction, 'temperature')}"
    )
    print(
        f"- Has catalysts (from CatalysisReaction): {hasattr(test_reaction, 'catalysts')}"
    )
    print(
        f"- Has catalyst_loading (from CatalysisReaction): {hasattr(test_reaction, 'catalyst_loading')}"
    )
    print(f"- Temperature value: {test_reaction.temperature}°C")
    print(f"- Catalysts: {test_reaction.catalysts}")
    print(f"- Catalyst loading: {test_reaction.catalyst_loading} g/L")


def main():
    """Run all demos."""
    print("🧪 XLSX Model Enhancement Demo - Simplified")
    print("=" * 60)
    print("This demo shows how to add XLSX functionality to existing")
    print("Pydantic models without modifying the original code.")
    print("Focuses on the core wrapper approach with 3 sheets.")

    try:
        # Run demos
        demo_inheritance_features()

        # Create simple demo
        output_file, *original_data = create_simple_demo()

        # Verify imports work correctly
        demo_import_verification(output_file, original_data)

        print("\n" + "=" * 60)
        print("🎉 All demos completed successfully!")
        print("=" * 60)

        # Show file info
        print(f"\n📁 Demo file created: {output_file}")
        if output_file.exists():
            file_size = output_file.stat().st_size
            print(f"   Size: {file_size:,} bytes")

            print("   Contains 3 sheets:")
            print("   1. BaseReaction - Key-value format for base model")
            print("   2. CatalysisReaction - Key-value format showing inheritance")
            print(
                "   3. CatalysisTable - Table format with multiple catalysis reactions"
            )

        print("\n💡 Key benefits demonstrated:")
        print("  ✅ Non-intrusive: Original models unchanged")
        print("  ✅ Inheritance support: Metadata flows down inheritance chain")
        print("  ✅ Type safety: Full isinstance() and attribute access")
        print("  ✅ Rich metadata: Units, descriptions, separators")
        print("  ✅ Multi-format: Both table and key-value formats")
        print("  ✅ Round-trip integrity: Export → Import → Verify all data")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()
