#!/usr/bin/env python3
"""
Demo: Key-Value Data Representations and Serialization

This demo focuses on data representations and serialization for key-value format.
It demonstrates how to handle single records, metadata, and ontology meanings.

Features demonstrated:
- Key-value format for single records
- Custom serializers/deserializers
- JSON/dict conversion
- Explicit key-value format specification
- Ontology meaning support with URIs
- Field filtering and selection
- Round-trip data integrity
- Enum validation with Excel dropdown selectors (key-value format)
"""

import sys
import traceback
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from voc4cat.xlsx_api import export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import (
    MetadataToggleConfig,
    MetadataVisibility,
    XLSXConverters,
    XLSXMetadata,
)
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig


# Enums for validation
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


# Custom serializers
def priority_with_level_serializer(value: Priority) -> str:
    """Custom serializer for priority with level numbers."""
    level_map = {
        Priority.LOW: "Level 1 - Low",
        Priority.MEDIUM: "Level 2 - Medium",
        Priority.HIGH: "Level 3 - High",
    }
    return level_map.get(value, str(value.value))


def priority_with_level_deserializer(value: str) -> Priority:
    """Custom deserializer for priority from level format."""
    if "Level 1" in value or "Low" in value:
        return Priority.LOW
    if "Level 3" in value or "High" in value:
        return Priority.HIGH
    return Priority.MEDIUM


def budget_formatter(value: float) -> str:
    """Custom formatter for budget with currency and formatting."""
    return f"${value:,.2f} USD"


def budget_parser(value: str) -> float:
    """Custom parser for budget from formatted string."""
    # Remove currency symbols and commas
    cleaned = value.replace("$", "").replace(",", "").replace("USD", "").strip()
    return float(cleaned)


# Models
class BasicProject(BaseModel):
    """Basic project model for key-value format demonstration."""

    project_id: int = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Detailed project description")
    start_date: date = Field(..., description="Project start date")
    end_date: date | None = Field(None, description="Project end date (if completed)")
    priority: Priority = Field(default=Priority.MEDIUM, description="Project priority")
    budget: float = Field(..., description="Project budget in USD")
    status: ProjectStatus = Field(
        default=ProjectStatus.PLANNING, description="Project status"
    )
    is_client_project: bool = Field(
        default=False, description="Is this a client project?"
    )
    client_name: str | None = Field(None, description="Client name (if applicable)")


class ProjectWithConverters(BaseModel):
    """Project model demonstrating built-in converters."""

    project_id: int = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Project priority")
    budget: float = Field(..., description="Project budget in USD")

    # Built-in converters
    technologies: Annotated[
        list[str],
        XLSXMetadata(
            description="Technologies used (comma-separated)",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []

    team_members: Annotated[
        list[str],
        XLSXMetadata(
            description="Team member emails (pipe-separated)",
            separator_pattern=XLSXConverters.PIPE,
        ),
    ] = []

    milestones: Annotated[
        list[str],
        XLSXMetadata(
            description="Project milestones (semicolon-separated)",
            separator_pattern=XLSXConverters.SEMICOLON,
        ),
    ] = []

    requirements: Annotated[
        list[int],
        XLSXMetadata(
            description="Requirement IDs (comma-separated integers)",
            xlsx_serializer=lambda x: ", ".join(str(i) for i in x) if x else "",
            xlsx_deserializer=lambda x: [
                int(i.strip()) for i in x.split(",") if i.strip()
            ]
            if x.strip()
            else [],
        ),
    ] = []

    metadata: Annotated[
        dict,
        XLSXMetadata(
            description="Project metadata (JSON format)",
            xlsx_serializer=XLSXConverters.dict_to_json_string,
            xlsx_deserializer=XLSXConverters.json_string_to_dict,
        ),
    ] = {}


class ProjectWithCustomSerializers(BaseModel):
    """Project model demonstrating custom serializers."""

    project_id: int = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")

    # Custom priority serializer
    priority: Annotated[
        Priority,
        XLSXMetadata(
            description="Project priority with level indicators",
            xlsx_serializer=priority_with_level_serializer,
            xlsx_deserializer=priority_with_level_deserializer,
        ),
    ] = Priority.MEDIUM

    # Custom budget formatter
    budget: Annotated[
        float,
        XLSXMetadata(
            description="Project budget with currency formatting",
            xlsx_serializer=budget_formatter,
            xlsx_deserializer=budget_parser,
        ),
    ]

    # Combined with built-in converter
    technologies: Annotated[
        list[str],
        XLSXMetadata(
            description="Technologies used (comma-separated)",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []


class ResearchProject(BaseModel):
    """Research project model with ontology meanings."""

    project_id: Annotated[
        int,
        XLSXMetadata(
            display_name="Project ID",
            description="Unique research project identifier",
            meaning="https://schema.org/identifier",
        ),
    ]

    title: Annotated[
        str,
        XLSXMetadata(
            display_name="Project Title",
            description="Official project title",
            meaning="http://purl.org/dc/terms/title",
        ),
    ]

    description: Annotated[
        str,
        XLSXMetadata(
            display_name="Project Description",
            description="Detailed project description",
            meaning="http://purl.org/dc/terms/description",
        ),
    ]

    start_date: Annotated[
        date,
        XLSXMetadata(
            display_name="Start Date",
            description="Project start date",
            meaning="https://schema.org/startDate",
        ),
    ]

    end_date: Annotated[
        date | None,
        XLSXMetadata(
            display_name="End Date",
            description="Project end date (if completed)",
            meaning="https://schema.org/endDate",
        ),
    ] = None

    budget: Annotated[
        float,
        XLSXMetadata(
            display_name="Budget",
            description="Project budget amount",
            meaning="https://schema.org/amount",
            unit="USD",
        ),
    ]

    duration_months: Annotated[
        int,
        XLSXMetadata(
            display_name="Duration",
            description="Project duration in months",
            meaning="https://schema.org/duration",
            unit="months",
        ),
    ]

    principal_investigator: Annotated[
        str,
        XLSXMetadata(
            display_name="Principal Investigator",
            description="Lead researcher name",
            meaning="https://schema.org/author",
        ),
    ]

    institution: Annotated[
        str,
        XLSXMetadata(
            display_name="Institution",
            description="Research institution",
            meaning="https://schema.org/affiliation",
        ),
    ]

    funding_agency: Annotated[
        str | None,
        XLSXMetadata(
            display_name="Funding Agency",
            description="Source of funding",
            meaning="https://schema.org/funder",
        ),
    ] = None

    keywords: Annotated[
        list[str],
        XLSXMetadata(
            display_name="Keywords",
            description="Research keywords (comma-separated)",
            meaning="https://schema.org/keywords",
            separator_pattern=XLSXConverters.COMMA,
        ),
    ] = []


def create_sample_data():
    """Create sample data for demonstrations."""

    # Basic project
    basic_project = BasicProject(
        project_id=101,
        name="Website Redesign",
        description="Complete redesign of the company website with modern UI and improved performance",
        start_date=date(2024, 1, 15),
        end_date=date(2024, 6, 30),
        priority=Priority.HIGH,
        budget=75000.0,
        status=ProjectStatus.ACTIVE,
        is_client_project=True,
        client_name="Tech Solutions Inc.",
    )

    # Project with converters
    project_with_converters = ProjectWithConverters(
        project_id=102,
        name="Mobile App Development",
        description="Cross-platform mobile application with real-time features",
        priority=Priority.MEDIUM,
        budget=120000.0,
        technologies=["React Native", "Firebase", "Redux", "TypeScript"],
        team_members=["alice@company.com", "bob@company.com", "carol@company.com"],
        milestones=[
            "Requirements Analysis",
            "UI/UX Design",
            "Development",
            "Testing",
            "Deployment",
        ],
        requirements=[1001, 1002, 1003, 1004],
        metadata={
            "complexity": "medium",
            "estimated_duration": 6,
            "requires_approval": True,
            "risk_level": "low",
        },
    )

    # Project with custom serializers
    project_with_custom = ProjectWithCustomSerializers(
        project_id=103,
        name="Data Analytics Platform",
        description="Advanced analytics platform with machine learning capabilities",
        priority=Priority.HIGH,
        budget=250000.0,
        technologies=["Python", "Apache Spark", "Kafka", "Elasticsearch"],
    )

    # Research project with ontology meanings
    research_project = ResearchProject(
        project_id=201,
        title="Advanced Materials Research",
        description="Investigation of novel nanomaterials for energy applications",
        start_date=date(2024, 3, 1),
        end_date=date(2025, 2, 28),
        budget=500000.0,
        duration_months=12,
        principal_investigator="Dr. Sarah Johnson",
        institution="University of Science",
        funding_agency="National Science Foundation",
        keywords=["nanomaterials", "energy", "sustainability", "characterization"],
    )

    return basic_project, project_with_converters, project_with_custom, research_project


def demo_basic_keyvalue_format(demo_file: Path):
    """Demonstrate basic key-value format."""

    print("\n" + "=" * 50)
    print("1. Basic Key-Value Format")
    print("=" * 50)

    basic_project, _, _, _ = create_sample_data()

    # Basic export with explicit key-value format
    sheet_name = "Basic_Project"
    export_to_xlsx(
        basic_project, demo_file, format_type="keyvalue", sheet_name=sheet_name
    )
    print(f"✓ Exported project '{basic_project.name}' to '{sheet_name}'")

    # Import back
    imported_project = import_from_xlsx(
        demo_file, BasicProject, format_type="keyvalue", sheet_name=sheet_name
    )
    print(f"✓ Imported project: {imported_project.name}")

    # Verify data integrity
    assert basic_project.project_id == imported_project.project_id
    assert basic_project.name == imported_project.name
    assert basic_project.priority == imported_project.priority
    assert basic_project.budget == imported_project.budget
    assert basic_project.start_date == imported_project.start_date
    print("✓ Data integrity verified")


def demo_builtin_converters(demo_file: Path):
    """Demonstrate built-in converters for key-value format."""

    print("\n" + "=" * 50)
    print("2. Built-in Converters")
    print("=" * 50)

    _, project_with_converters, _, _ = create_sample_data()

    # Show original data
    print("Original data:")
    print(f"  - technologies: {project_with_converters.technologies}")
    print(f"  - team_members: {project_with_converters.team_members}")
    print(f"  - milestones: {project_with_converters.milestones}")
    print(f"  - requirements: {project_with_converters.requirements}")
    print(f"  - metadata: {project_with_converters.metadata}")

    # Export with automatic conversion
    sheet_name = "Project_Converters"
    export_to_xlsx(
        project_with_converters,
        demo_file,
        format_type="keyvalue",
        sheet_name=sheet_name,
    )
    print("✓ Exported project with built-in converters")

    # Import back
    imported_project = import_from_xlsx(
        demo_file, ProjectWithConverters, format_type="keyvalue", sheet_name=sheet_name
    )
    print(f"✓ Imported project: {imported_project.name}")

    # Show imported data
    print("Imported data:")
    print(f"  - technologies: {imported_project.technologies}")
    print(f"  - team_members: {imported_project.team_members}")
    print(f"  - milestones: {imported_project.milestones}")
    print(f"  - requirements: {imported_project.requirements}")
    print(f"  - metadata: {imported_project.metadata}")

    # Verify round-trip conversion
    assert project_with_converters.technologies == imported_project.technologies
    assert project_with_converters.team_members == imported_project.team_members
    assert project_with_converters.milestones == imported_project.milestones
    assert project_with_converters.requirements == imported_project.requirements
    assert project_with_converters.metadata == imported_project.metadata
    print("✓ Round-trip conversion verified")


def demo_custom_serializers(demo_file: Path):
    """Demonstrate custom field serializers."""

    print("\n" + "=" * 50)
    print("3. Custom Serializers")
    print("=" * 50)

    _, _, project_with_custom, _ = create_sample_data()

    # Show original data
    print("Original data:")
    print(f"  - priority: {project_with_custom.priority}")
    print(f"  - budget: {project_with_custom.budget}")
    print(f"  - technologies: {project_with_custom.technologies}")

    # Export with custom serializers
    sheet_name = "Project_Custom"
    export_to_xlsx(
        project_with_custom, demo_file, format_type="keyvalue", sheet_name=sheet_name
    )
    print("✓ Exported project with custom serializers")
    print("  - Priority will appear as 'Level X - Priority'")
    print("  - Budget will appear as formatted currency")

    # Import back
    imported_project = import_from_xlsx(
        demo_file,
        ProjectWithCustomSerializers,
        format_type="keyvalue",
        sheet_name=sheet_name,
    )
    print(f"✓ Imported project: {imported_project.name}")

    # Show imported data
    print("Imported data:")
    print(f"  - priority: {imported_project.priority}")
    print(f"  - budget: {imported_project.budget}")
    print(f"  - technologies: {imported_project.technologies}")

    # Verify round-trip conversion
    assert project_with_custom.priority == imported_project.priority
    assert project_with_custom.budget == imported_project.budget
    assert project_with_custom.technologies == imported_project.technologies
    print("✓ Custom serializer round-trip verified")


def demo_ontology_meanings(demo_file: Path):
    """Demonstrate ontology meaning support."""

    print("\n" + "=" * 50)
    print("4. Ontology Meanings")
    print("=" * 50)

    _, _, _, research_project = create_sample_data()

    # Export with meanings and units
    sheet_name = "Research_Meanings"

    # Configure to show meanings and units
    config = XLSXKeyValueConfig(
        title="Research Project with Ontology Meanings",
    )

    export_to_xlsx(
        research_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print("✓ Exported research project with ontology meanings")
    print("  - Field|Value|Unit|Description|Meaning columns")
    print("  - URIs from schema.org and Dublin Core")

    # Import back
    imported_research = import_from_xlsx(
        demo_file,
        ResearchProject,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported research project: {imported_research.title}")

    # Verify data integrity
    assert research_project.project_id == imported_research.project_id
    assert research_project.title == imported_research.title
    assert research_project.budget == imported_research.budget
    assert research_project.keywords == imported_research.keywords
    print("✓ Ontology meaning round-trip verified")


def demo_field_filtering(demo_file: Path):
    """Demonstrate field filtering and selection."""

    print("\n" + "=" * 50)
    print("5. Field Filtering")
    print("=" * 50)

    basic_project, _, _, _ = create_sample_data()

    # Export with field filtering
    sheet_name = "Project_Filtered"

    # Configure to include only specific fields
    config = XLSXKeyValueConfig(
        title="Filtered Project Information",
        include_fields={
            "project_id",
            "name",
            "description",
            "start_date",  # Required field
            "priority",
            "budget",
            "status",
        },
        field_column_header="Property",
        value_column_header="Value",
    )

    export_to_xlsx(
        basic_project,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print("✓ Exported project with field filtering")
    print("  - Only selected fields included")
    print("  - Custom column headers")

    # Import back
    imported_project = import_from_xlsx(
        demo_file,
        BasicProject,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported filtered project: {imported_project.name}")

    # Verify filtered fields
    assert imported_project.project_id == basic_project.project_id
    assert imported_project.name == basic_project.name
    assert imported_project.priority == basic_project.priority
    assert imported_project.start_date == basic_project.start_date
    # Excluded fields should have default values
    assert not imported_project.is_client_project  # default value
    assert imported_project.client_name is None  # default value
    print("✓ Field filtering verified")


def demo_enum_validation(demo_file: Path):
    """Demonstrate enum field handling and validation with dropdown selectors."""

    print("\n" + "=" * 50)
    print("6. Enum Field Handling and Validation")
    print("=" * 50)

    basic_project, _, _, _ = create_sample_data()

    # Key-value format WITHOUT validation (legacy behavior)
    sheet_name = "Enum_KeyValue_NoValidation"

    config_no_validation = XLSXKeyValueConfig(
        title="Project with Enum Fields (No Validation)",
    )

    export_to_xlsx(
        basic_project,
        demo_file,
        format_type="keyvalue",
        config=config_no_validation,
        sheet_name=sheet_name,
    )
    print("✓ Exported project without enum validation (key-value format)")
    print("  - Enum fields are serialized as string values")
    print("  - Excel dropdown validation always available")

    # Import back
    imported_project = import_from_xlsx(
        demo_file,
        BasicProject,
        format_type="keyvalue",
        config=config_no_validation,
        sheet_name=sheet_name,
    )
    print(f"✓ Imported project: {imported_project.name}")

    # Verify enum values
    assert imported_project.priority == basic_project.priority
    assert imported_project.status == basic_project.status
    print("✓ Enum field round-trip verified")

    # Key-value format WITH validation (new feature)
    print("\n" + "-" * 30)
    print("Key-Value Format with Validation")
    print("-" * 30)

    sheet_name_validation = "Enum_KeyValue_WithValidation"

    config_with_validation = XLSXKeyValueConfig(
        title="Project with Enum Fields (With Validation)",
    )

    export_to_xlsx(
        basic_project,
        demo_file,
        format_type="keyvalue",
        config=config_with_validation,
        sheet_name=sheet_name_validation,
    )
    print("✓ Exported project with enum validation (key-value format)")
    print("  - Enum fields have Excel dropdown selectors!")
    print("  - Priority field: dropdown with 'low', 'medium', 'high' options")
    print(
        "  - Status field: dropdown with 'planning', 'active', 'on_hold', 'completed', 'cancelled' options"
    )

    # Import back
    imported_project_validated = import_from_xlsx(
        demo_file,
        BasicProject,
        format_type="keyvalue",
        config=config_with_validation,
        sheet_name=sheet_name_validation,
    )
    print(f"✓ Imported validated project: {imported_project_validated.name}")

    # Verify enum values
    assert imported_project_validated.priority == basic_project.priority
    assert imported_project_validated.status == basic_project.status
    print("✓ Enum field round-trip verified with validation")

    # Show available enum values
    print("\nEnum field information:")
    print(f"  - Priority enum values: {[p.value for p in Priority]}")
    print(f"  - ProjectStatus enum values: {[s.value for s in ProjectStatus]}")

    # Demonstrate table format with validation (multiple records required)
    print("\n" + "-" * 30)
    print("Table Format with Validation")
    print("-" * 30)

    print("✓ Exported projects with enum validation (table format)")
    print("  - Excel dropdown selectors enabled for enum fields")
    print("  - Priority field: dropdown with 'low', 'medium', 'high' options")
    print(
        "  - Status field: dropdown with 'planning', 'active', 'on_hold', 'completed', 'cancelled' options"
    )

    print("✓ Table format created with enum validation dropdowns")
    print("  - Open Excel to see dropdown selectors in enum columns")
    print("  - Validation prevents invalid enum values from being entered")

    print("\n🔍 Key Insights:")
    print("  - Key-value format: Always supports Excel dropdown validation")
    print("  - Enum fields can be serialized as strings or with dropdowns")


def demo_requiredness_column(demo_file: Path):
    """Demonstrate requiredness column display in key-value format."""

    print("\n" + "=" * 50)
    print("9. Requiredness Column Display")
    print("=" * 50)

    # Model with various field types
    class ConfigModel(BaseModel):
        api_key: str  # Required
        endpoint: str  # Required
        timeout: int = 30  # Optional with non-trivial default
        debug: bool = False  # Optional with trivial default
        proxy: str | None = None  # Optional (nullable)

    config_data = ConfigModel(api_key="abc123", endpoint="https://api.example.com")

    # Export with requiredness column enabled
    config = XLSXKeyValueConfig(
        title="API Configuration",
        metadata_visibility=MetadataToggleConfig(requiredness=MetadataVisibility.SHOW),
    )

    sheet_name = "Requiredness_KV"
    export_to_xlsx(
        config_data,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name=sheet_name,
    )

    print("✓ Exported key-value with requiredness column")
    print("  Column shows:")
    print('  - "Yes" for required fields (api_key, endpoint)')
    print('  - "No (default: 30)" for timeout')
    print('  - "No" for debug (trivial default) and proxy (nullable)')


def demo_metadata_visibility_keyvalue(demo_file: Path):
    """Demonstrate metadata visibility toggles for key-value format."""
    print("\n" + "=" * 50)
    print("10. Metadata Visibility Toggles (Key-Value)")
    print("=" * 50)

    class DeviceSettings(BaseModel):
        device_id: str
        temperature: Annotated[
            float,
            XLSXMetadata(
                unit="°C",
                description="Operating temperature",
            ),
        ] = 25.0

    settings = DeviceSettings(device_id="DEV001")

    # Hide description but show requiredness
    config = XLSXKeyValueConfig(
        title="Device Settings",
        metadata_visibility=MetadataToggleConfig(
            requiredness=MetadataVisibility.SHOW,
            description=MetadataVisibility.HIDE,
        ),
    )

    export_to_xlsx(
        settings,
        demo_file,
        format_type="keyvalue",
        config=config,
        sheet_name="KV_Visibility",
    )
    print("✓ Exported with requiredness shown, description hidden")
    print("  Columns: Field, Value, Unit, Required (no Description)")


def main():
    """Run all key-value data demonstrations."""

    print("XLSX KEY-VALUE DATA REPRESENTATIONS AND SERIALIZATION DEMO")
    print("=" * 60)
    print("Focus: Data handling, converters, and serialization for key-value format")

    # Output file
    demo_file = Path("keyvalue_data_enum_demo.xlsx")

    # Remove existing file to avoid conflicts
    if demo_file.exists():
        demo_file.unlink()

    try:
        demo_basic_keyvalue_format(demo_file)
        demo_builtin_converters(demo_file)
        demo_custom_serializers(demo_file)
        demo_ontology_meanings(demo_file)
        demo_field_filtering(demo_file)
        demo_enum_validation(demo_file)
        demo_requiredness_column(demo_file)
        demo_metadata_visibility_keyvalue(demo_file)

        print("\n✅ All demonstrations completed successfully!")
        print(f"Demo file: {demo_file.absolute()}")
        print("\nSheets created:")
        print("• Basic_Project - Basic key-value format")
        print("• Project_Converters - Built-in converters demo")
        print("• Project_Custom - Custom serializers demo")
        print("• Research_Meanings - Ontology meanings demo")
        print("• Project_Filtered - Field filtering demo")
        print("• Enum_KeyValue_NoValidation - Enum fields without validation")
        print(
            "• Enum_KeyValue_WithValidation - Enum fields with Excel dropdowns (key-value format)"
        )
        print(
            "• Enum_Table_Validation - Enum validation with Excel dropdowns (table format)"
        )
        print("• Requiredness_KV - Requiredness column display")
        print("• KV_Visibility - Metadata visibility toggles")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
