#!/usr/bin/env python3
"""
Demo: Key-Value Visual Formatting and Styling

This demo focuses on visual presentation, formatting, and styling for key-value format.
It demonstrates how to customize the appearance and layout of xlsx key-value sheets.

Features demonstrated:
- Custom sheet titles and headers
- Field descriptions and units display
- Ontology meanings visualization
- Field filtering and selection
- Custom column headers
- Professional presentation layout
- Different styling approaches
"""

import sys
import traceback
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from voc4cat.xlsx_api import export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import XLSXConverters, XLSXMetadata
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig


# Enums
class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProjectStatus(Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResearchType(Enum):
    BASIC = "basic_research"
    APPLIED = "applied_research"
    EXPERIMENTAL = "experimental"
    THEORETICAL = "theoretical"


# Models
class StyledProject(BaseModel):
    """Project model with extensive styling metadata."""

    project_id: Annotated[
        int,
        XLSXMetadata(
            display_name="Project ID",
            description="Unique project identifier",
            meaning="https://schema.org/identifier",
        ),
    ] = Field(..., description="Unique project identifier")

    name: Annotated[
        str,
        XLSXMetadata(
            display_name="Project Name",
            description="Official project name",
            meaning="http://purl.org/dc/terms/title",
        ),
    ] = Field(..., description="Project name")

    description: Annotated[
        str,
        XLSXMetadata(
            display_name="Description",
            description="Detailed project description",
            meaning="http://purl.org/dc/terms/description",
        ),
    ] = Field(..., description="Project description")

    start_date: Annotated[
        date,
        XLSXMetadata(
            display_name="Start Date",
            description="Project start date",
            meaning="https://schema.org/startDate",
        ),
    ] = Field(..., description="Project start date")

    end_date: Annotated[
        date | None,
        XLSXMetadata(
            display_name="End Date",
            description="Project end date (if completed)",
            meaning="https://schema.org/endDate",
        ),
    ] = Field(None, description="Project end date")

    priority: Annotated[
        Priority,
        XLSXMetadata(
            display_name="Priority Level",
            description="Project priority level",
            meaning="https://schema.org/priority",
        ),
    ] = Field(default=Priority.MEDIUM, description="Project priority")

    budget: Annotated[
        float,
        XLSXMetadata(
            display_name="Budget",
            description="Total project budget",
            meaning="https://schema.org/amount",
            unit="USD",
        ),
    ] = Field(..., description="Project budget")

    duration_months: Annotated[
        int,
        XLSXMetadata(
            display_name="Duration",
            description="Project duration in months",
            meaning="https://schema.org/duration",
            unit="months",
        ),
    ] = Field(..., description="Project duration")

    status: Annotated[
        ProjectStatus,
        XLSXMetadata(
            display_name="Current Status",
            description="Current project status",
            meaning="https://schema.org/status",
        ),
    ] = Field(default=ProjectStatus.PLANNING, description="Project status")

    team_size: Annotated[
        int,
        XLSXMetadata(
            display_name="Team Size",
            description="Number of team members",
            meaning="https://schema.org/numberOfEmployees",
            unit="people",
        ),
    ] = Field(..., description="Team size")

    completion_percentage: Annotated[
        float,
        XLSXMetadata(
            display_name="Completion",
            description="Project completion percentage",
            meaning="https://schema.org/percentage",
            unit="%",
        ),
    ] = Field(default=0.0, description="Completion percentage")

    technologies: Annotated[
        list[str],
        XLSXMetadata(
            display_name="Technologies",
            description="Technologies used (comma-separated)",
            meaning="https://schema.org/technology",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []

    client_contact: Annotated[
        str | None,
        XLSXMetadata(
            display_name="Client Contact",
            description="Main client contact person",
            meaning="https://schema.org/contactPoint",
        ),
    ] = Field(None, description="Client contact")

    risk_level: Annotated[
        Priority,
        XLSXMetadata(
            display_name="Risk Level",
            description="Project risk assessment",
            meaning="https://schema.org/riskLevel",
        ),
    ] = Field(default=Priority.MEDIUM, description="Risk level")


class ResearchProject(BaseModel):
    """Research project model with comprehensive metadata."""

    project_id: Annotated[
        int,
        XLSXMetadata(
            display_name="Research Project ID",
            description="Unique research project identifier",
            meaning="https://schema.org/identifier",
        ),
    ] = Field(..., description="Unique project identifier")

    title: Annotated[
        str,
        XLSXMetadata(
            display_name="Research Title",
            description="Official research project title",
            meaning="http://purl.org/dc/terms/title",
        ),
    ] = Field(..., description="Research title")

    abstract: Annotated[
        str,
        XLSXMetadata(
            display_name="Abstract",
            description="Research abstract/summary",
            meaning="http://purl.org/dc/terms/abstract",
        ),
    ] = Field(..., description="Research abstract")

    research_type: Annotated[
        ResearchType,
        XLSXMetadata(
            display_name="Research Type",
            description="Type of research being conducted",
            meaning="https://schema.org/researchType",
        ),
    ] = Field(..., description="Type of research")

    start_date: Annotated[
        date,
        XLSXMetadata(
            display_name="Start Date",
            description="Research start date",
            meaning="https://schema.org/startDate",
        ),
    ] = Field(..., description="Research start date")

    end_date: Annotated[
        date | None,
        XLSXMetadata(
            display_name="End Date",
            description="Research end date (if completed)",
            meaning="https://schema.org/endDate",
        ),
    ] = Field(None, description="Research end date")

    principal_investigator: Annotated[
        str,
        XLSXMetadata(
            display_name="Principal Investigator",
            description="Lead researcher name",
            meaning="https://schema.org/author",
        ),
    ] = Field(..., description="Principal investigator")

    institution: Annotated[
        str,
        XLSXMetadata(
            display_name="Institution",
            description="Research institution",
            meaning="https://schema.org/affiliation",
        ),
    ] = Field(..., description="Research institution")

    funding_amount: Annotated[
        float,
        XLSXMetadata(
            display_name="Funding Amount",
            description="Total funding amount",
            meaning="https://schema.org/amount",
            unit="USD",
        ),
    ] = Field(..., description="Funding amount")

    funding_agency: Annotated[
        str | None,
        XLSXMetadata(
            display_name="Funding Agency",
            description="Primary funding source",
            meaning="https://schema.org/funder",
        ),
    ] = Field(None, description="Funding agency")

    keywords: Annotated[
        list[str],
        XLSXMetadata(
            display_name="Keywords",
            description="Research keywords (comma-separated)",
            meaning="https://schema.org/keywords",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []

    expected_outputs: Annotated[
        list[str],
        XLSXMetadata(
            display_name="Expected Outputs",
            description="Expected research outputs (pipe-separated)",
            meaning="https://schema.org/expectedOutput",
            separator_pattern=XLSXConverters.PIPE,
        ),
    ] = []


class SimpleRecord(BaseModel):
    """Simple record for minimal styling demonstration."""

    record_id: int = Field(..., description="Unique record identifier")
    name: str = Field(..., description="Record name")
    value: str = Field(..., description="Record value")
    status: str = Field(default="active", description="Record status")
    created_date: date = Field(..., description="Creation date")


def create_sample_data():
    """Create sample data for styling demonstrations."""

    # Styled project
    styled_project = StyledProject(
        project_id=1001,
        name="Advanced Web Platform",
        description="Next-generation web platform with AI integration and real-time analytics",
        start_date=date(2024, 1, 15),
        end_date=date(2024, 12, 31),
        priority=Priority.HIGH,
        budget=750000.0,
        duration_months=12,
        status=ProjectStatus.ACTIVE,
        team_size=8,
        completion_percentage=35.5,
        technologies=[
            "React",
            "Node.js",
            "Python",
            "TensorFlow",
            "PostgreSQL",
            "Redis",
        ],
        client_contact="Dr. Sarah Johnson",
        risk_level=Priority.MEDIUM,
    )

    # Research project
    research_project = ResearchProject(
        project_id=2001,
        title="Quantum Computing Applications in Materials Science",
        abstract="Investigation of quantum computing algorithms for accelerating materials discovery and characterization processes",
        research_type=ResearchType.APPLIED,
        start_date=date(2024, 3, 1),
        end_date=date(2025, 2, 28),
        principal_investigator="Prof. Michael Chen",
        institution="Institute for Advanced Materials Research",
        funding_amount=950000.0,
        funding_agency="National Science Foundation",
        keywords=[
            "quantum computing",
            "materials science",
            "algorithms",
            "characterization",
        ],
        expected_outputs=[
            "Research papers",
            "Software tools",
            "Patent applications",
            "Conference presentations",
        ],
    )

    # Simple record
    simple_record = SimpleRecord(
        record_id=3001,
        name="Configuration Entry",
        value="production_database_url",
        status="active",
        created_date=date(2024, 1, 10),
    )

    return styled_project, research_project, simple_record


def demo_basic_keyvalue_styling(demo_file: Path):
    """Demonstrate basic key-value styling options."""

    print("\n" + "=" * 50)
    print("1. Basic Key-Value Styling")
    print("=" * 50)

    styled_project, _, _ = create_sample_data()

    # Basic styling with title
    sheet_name = "Basic_KV_Styling"

    config = XLSXKeyValueConfig(
        title="Project Information",
        field_column_header="Property",
        value_column_header="Value",
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported project with basic styling to '{sheet_name}'")
    print("  - Custom title and column headers")
    print("  - Field descriptions displayed")

    # Import back to verify
    imported_project = import_from_xlsx(
        demo_file,
        StyledProject,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported project: {imported_project.name}")


def demo_comprehensive_metadata(demo_file: Path):
    """Demonstrate comprehensive metadata display."""

    print("\n" + "=" * 50)
    print("2. Comprehensive Metadata Display")
    print("=" * 50)

    styled_project, _, _ = create_sample_data()

    # Show all metadata types
    sheet_name = "Comprehensive_Metadata"

    config = XLSXKeyValueConfig(
        title="Project Details (All Metadata)",
        field_column_header="Field",
        value_column_header="Value",
        unit_column_header="Unit",
        description_column_header="Description",
        meaning_column_header="Ontology URI",
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported project with comprehensive metadata to '{sheet_name}'")
    print("  - Field|Value|Unit|Description|Meaning columns")
    print("  - Complete ontology URI information")
    print("  - Unit information for numeric fields")

    # Import back
    imported_project = import_from_xlsx(
        demo_file,
        StyledProject,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported project with all metadata: {imported_project.name}")


def demo_field_filtering_and_selection(demo_file: Path):
    """Demonstrate field filtering and selection for presentation."""

    print("\n" + "=" * 50)
    print("3. Field Filtering and Selection")
    print("=" * 50)

    styled_project, _, _ = create_sample_data()

    # Executive summary - key fields only
    sheet_name = "Executive_Summary"

    config = XLSXKeyValueConfig(
        title="Executive Summary",
        include_fields={
            "project_id",
            "name",
            "priority",
            "budget",
            "duration_months",
            "status",
            "completion_percentage",
            "team_size",
        },
        field_column_header="Key Metric",
        value_column_header="Value",
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported executive summary to '{sheet_name}'")
    print("  - Key metrics only")
    print("  - Professional presentation")

    # Technical details - different field set
    sheet_name = "Technical_Details"

    tech_config = XLSXKeyValueConfig(
        title="Technical Project Details",
        include_fields={
            "project_id",
            "name",
            "description",
            "technologies",
            "start_date",
            "end_date",
            "risk_level",
        },
        field_column_header="Technical Aspect",
        value_column_header="Details",
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=tech_config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported technical details to '{sheet_name}'")
    print("  - Technical fields focus")
    print("  - Ontology meanings for context")


def demo_research_project_styling(demo_file: Path):
    """Demonstrate research project styling with academic focus."""

    print("\n" + "=" * 50)
    print("4. Research Project Styling")
    print("=" * 50)

    _, research_project, _ = create_sample_data()

    # Academic presentation style
    sheet_name = "Research_Academic_Style"

    config = XLSXKeyValueConfig(
        title="Research Project Profile",
        field_column_header="Research Attribute",
        value_column_header="Information",
        description_column_header="Details",
        meaning_column_header="Semantic Reference",
    )

    export_to_xlsx(
        research_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported research project to '{sheet_name}'")
    print("  - Academic presentation style")
    print("  - Semantic references for research context")
    print("  - Comprehensive metadata display")

    # Import back
    imported_research = import_from_xlsx(
        demo_file,
        ResearchProject,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported research project: {imported_research.title}")


def demo_custom_column_headers(demo_file: Path):
    """Demonstrate custom column headers for different contexts."""

    print("\n" + "=" * 50)
    print("5. Custom Column Headers")
    print("=" * 50)

    simple_record = create_sample_data()[2]

    # Different header styles for different audiences
    contexts = [
        {
            "name": "Technical_Context",
            "title": "System Configuration Record",
            "field_header": "Parameter",
            "value_header": "Setting",
            "desc_header": "Purpose",
        },
        {
            "name": "Business_Context",
            "title": "Business Record Summary",
            "field_header": "Attribute",
            "value_header": "Information",
            "desc_header": "Business Purpose",
        },
        {
            "name": "User_Context",
            "title": "User-Friendly Record View",
            "field_header": "Property",
            "value_header": "Value",
            "desc_header": "What This Means",
        },
    ]

    for context in contexts:
        sheet_name = context["name"]

        config = XLSXKeyValueConfig(
            title=context["title"],
            field_column_header=context["field_header"],
            value_column_header=context["value_header"],
            description_column_header=context["desc_header"],
        )

        export_to_xlsx(
            simple_record,
            demo_file,
            format_type="keyvalue",
            config=config,
            sheet_name=sheet_name,
        )
        print(f"✓ Exported {context['name'].lower()} to '{sheet_name}'")

    print("  - Same data, different presentations")
    print("  - Context-appropriate headers")


def demo_minimal_vs_detailed_styling(demo_file: Path):
    """Demonstrate minimal vs detailed styling approaches."""

    print("\n" + "=" * 50)
    print("6. Minimal vs Detailed Styling")
    print("=" * 50)

    styled_project, _, _ = create_sample_data()

    # Minimal styling
    sheet_name = "Minimal_Styling"

    minimal_config = XLSXKeyValueConfig(
        title="Project Info",
        include_fields={
            "project_id",
            "name",
            "status",
            "budget",
        },
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=minimal_config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported minimal styling to '{sheet_name}'")
    print("  - Essential fields only")
    print("  - Clean, simple presentation")

    # Detailed styling
    sheet_name = "Detailed_Styling"

    detailed_config = XLSXKeyValueConfig(
        title="Complete Project Analysis",
        field_column_header="Project Attribute",
        value_column_header="Current Value",
        unit_column_header="Unit of Measure",
        description_column_header="Detailed Description",
        meaning_column_header="Ontological Definition",
    )

    export_to_xlsx(
        styled_project,
        demo_file,
        format_type="keyvalue",
        config=detailed_config,
        sheet_name=sheet_name,
    )
    print(f"✓ Exported detailed styling to '{sheet_name}'")
    print("  - All available metadata")
    print("  - Comprehensive documentation")


def demo_comparison_layouts(demo_file: Path):
    """Demonstrate different layout approaches for comparison."""

    print("\n" + "=" * 50)
    print("7. Layout Comparison")
    print("=" * 50)

    styled_project, _, _ = create_sample_data()

    # Create different layouts for the same data
    layouts = [
        {
            "name": "Compact_Layout",
            "title": "Project Overview",
            "config": XLSXKeyValueConfig(
                title="Project Overview",
                field_column_header="Item",
                value_column_header="Value",
                include_fields={
                    "name",
                    "priority",
                    "budget",
                    "status",
                    "completion_percentage",
                },
            ),
        },
        {
            "name": "Detailed_Layout",
            "title": "Project Analysis",
            "config": XLSXKeyValueConfig(
                title="Comprehensive Project Analysis",
                field_column_header="Analysis Parameter",
                value_column_header="Current State",
                description_column_header="Parameter Description",
            ),
        },
        {
            "name": "Semantic_Layout",
            "title": "Semantic Project View",
            "config": XLSXKeyValueConfig(
                title="Semantic Project Representation",
                field_column_header="Concept",
                value_column_header="Instance",
                meaning_column_header="Ontology URI",
            ),
        },
    ]

    for layout in layouts:
        sheet_name = layout["name"]

        export_to_xlsx(
            styled_project,
            demo_file,
            format_type="keyvalue",
            config=layout["config"],
            sheet_name=sheet_name,
        )
        print(f"✓ Exported {layout['name'].lower()} to '{sheet_name}'")

    print("  - Same data, different layout strategies")
    print("  - Compact: Essential info only")
    print("  - Detailed: Full metadata")
    print("  - Semantic: Ontology focus")


def main():
    """Run all key-value styling demonstrations."""

    print("XLSX KEY-VALUE VISUAL FORMATTING AND STYLING DEMO")
    print("=" * 60)
    print("Focus: Visual presentation, formatting, and styling for key-value format")

    # Output file
    demo_file = Path("keyvalue_styling_demo.xlsx")

    # Remove existing file to avoid conflicts
    if demo_file.exists():
        demo_file.unlink()

    try:
        demo_basic_keyvalue_styling(demo_file)
        demo_comprehensive_metadata(demo_file)
        demo_field_filtering_and_selection(demo_file)
        demo_research_project_styling(demo_file)
        demo_custom_column_headers(demo_file)
        demo_minimal_vs_detailed_styling(demo_file)
        demo_comparison_layouts(demo_file)

        print("\n✅ All demonstrations completed successfully!")
        print(f"Demo file: {demo_file.absolute()}")
        print("\nSheets created:")
        print("• Basic_KV_Styling - Basic key-value styling")
        print("• Comprehensive_Metadata - All metadata types")
        print("• Executive_Summary - Key metrics only")
        print("• Technical_Details - Technical focus")
        print("• Research_Academic_Style - Academic presentation")
        print("• Technical_Context - Technical headers")
        print("• Business_Context - Business headers")
        print("• User_Context - User-friendly headers")
        print("• Minimal_Styling - Clean, simple layout")
        print("• Detailed_Styling - Complete metadata")
        print("• Compact_Layout - Essential info")
        print("• Detailed_Layout - Full analysis")
        print("• Semantic_Layout - Ontology focus")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
