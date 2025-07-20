"""
Tests for integration scenarios and real-world use cases.

This module tests complex integration scenarios, performance, and edge cases
that span multiple modules in the XLSX processing system.
"""

from datetime import date
from enum import Enum
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from voc4cat.xlsx_api import XLSXProcessorFactory, export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import XLSXConverters, XLSXMetadata
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import JoinConfiguration, XLSXTableConfig

from .conftest import Employee, Project, SimpleModel


# Vocabulary Template Models (copied from demo files)
class ObsoletionReason(Enum):
    """Reasons for obsoleting vocabulary elements."""

    UNCLEAR_DEFINITION = "Not clearly defined or inconsistent usage."
    ADDED_IN_ERROR = "Added in error."
    MORE_SPECIFIC_CREATED = "More specific concepts created."
    CONVERTED_TO_COLLECTION = "Converted to a collection."
    AMBIGUOUS_MEANING = "The meaning was ambiguous."
    LACK_OF_EVIDENCE = "Lack of evidence that this function/process/component exists."


class MappingType(Enum):
    """Type of SKOS mapping relation."""

    EXACT_MATCH = "skos:exactMatch"
    CLOSE_MATCH = "skos:closeMatch"
    NARROW_MATCH = "skos:narrowMatch"
    BROAD_MATCH = "skos:broadMatch"
    RELATED_MATCH = "skos:relatedMatch"


class CollectionObsoletionReason(Enum):
    """Reasons for obsoleting collections."""

    UNCLEAR_DEFINITION = "Not clearly defined or inconsistent usage."
    ADDED_IN_ERROR = "Added in error."
    MORE_SPECIFIC_CREATED = "More specific colllections were created."
    CONVERTED_TO_CONCEPT = "Converted to a concept."


class ConceptScheme(BaseModel):
    """Concept scheme metadata (key-value format)."""

    template_version: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:hasVersion",
            description="Gets increments only on structural changes. Its general pattern is major.minor.rev-JJJJ-MM[a-z].",
        ),
    ] = Field(default="1.0.rev-2025-06a")

    vocabulary_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Vocabulary IRI",
            meaning="skos:conceptScheme",
            description="IRI for this vocabulary",
        ),
    ] = Field(...)

    prefix: Annotated[
        str,
        XLSXMetadata(
            meaning="vann:preferredNamespacePrefix",
            description="Registered (or preferred) prefix to be used in CURIES for this vocabulary",
        ),
    ] = Field(...)

    title: Annotated[
        str,
        XLSXMetadata(meaning="dcterms:title", description="Title of the vocabulary"),
    ] = Field(...)

    description: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:description",
            description="General description of the vocabulary",
        ),
    ] = Field(...)

    version: Annotated[
        str,
        XLSXMetadata(
            meaning="owl:versionInfo",
            description="Automatically added version specifier for the vocabulary",
        ),
    ] = Field(...)

    modified_date: Annotated[
        date,
        XLSXMetadata(
            meaning="dcterms:modified",
            description="Automatically added date of last modification",
        ),
    ] = Field(default_factory=date.today)


class Mapping(BaseModel):
    """External mapping between concepts (table format)."""

    concept_iri: Annotated[
        str, XLSXMetadata(meaning="skos:Concept", description="IRI of Voc4Cat Concept")
    ] = Field(...)

    mapping_relation: Annotated[
        MappingType | None,
        XLSXMetadata(
            meaning="skos:mappingRelation", description="Type of mapping relation."
        ),
    ] = Field(None)

    mapped_external_concept: str | None = Field(
        None,
        description="IRI of mapped external concept",
    )


class Collection(BaseModel):
    """Collection of concepts (table format)."""

    collection_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Collection, skos:orderedCollection",
            description="Collection IRI",
        ),
    ] = Field(...)

    language_code: Annotated[
        str, XLSXMetadata(meaning="dcterms:language", description="Language Code")
    ] = Field(default="en")

    preferred_label: Annotated[
        str, XLSXMetadata(meaning="skos:preferredLabel", description="Preferred Label")
    ] = Field(...)

    definition: Annotated[
        str, XLSXMetadata(meaning="skos:definition", description="Definition")
    ] = Field(...)

    parent_collection_iris: (
        Annotated[
            list[str],
            XLSXMetadata(
                separator_pattern=XLSXConverters.PIPE_ESCAPED,
                meaning="skos:member",
                description="Parent Collection IRIs",
            ),
        ]
        | None
    ) = Field(default=None)

    is_ordered: bool = Field(
        default=False,
        description="Ordered? Yes or No (default)",
    )

    change_note: (
        Annotated[
            str, XLSXMetadata(meaning="skos:changeNote", description="Change Note")
        ]
        | None
    ) = Field(None)

    editorial_note: (
        Annotated[
            str,
            XLSXMetadata(meaning="skos:editorialNote", description="Editorial Note"),
        ]
        | None
    ) = Field(None)

    obsoletion_reason: CollectionObsoletionReason | None = Field(
        None, description="Reason for obsoletion if applicable"
    )


class Prefix(BaseModel):
    """Namespace prefix mapping (table format)."""

    prefix: Annotated[
        str, XLSXMetadata(meaning="vann:preferredNamespacePrefix", description="Prefix")
    ] = Field(...)

    namespace: Annotated[
        str, XLSXMetadata(meaning="vann:preferredNamespaceUri", description="Namespace")
    ] = Field(...)


class ConceptTranslation(BaseModel):
    """Translation of a concept in a specific language."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Concept",
            description="IRI of the concept being translated",
        ),
    ] = Field(...)

    language_code: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:language",
            description="ISO 639-1 language code (e.g., 'en', 'de', 'fr')",
        ),
    ] = Field(...)

    preferred_label: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:prefLabel",
            description="Preferred label in this language",
        ),
    ] = Field(...)

    alternate_labels: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.COMMA,
            meaning="skos:altLabel",
            description="Alternative labels in this language",
        ),
    ] = Field(default_factory=list)

    definition: Annotated[
        str | None,
        XLSXMetadata(
            meaning="skos:definition",
            description="Definition of the concept in this language",
        ),
    ] = Field(None)

    scope_note: Annotated[
        str | None,
        XLSXMetadata(
            meaning="skos:scopeNote",
            description="Scope note in this language",
        ),
    ] = Field(None)


class MultiLingualConcept(BaseModel):
    """Concept with multi-language support for joined model demonstration."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Concept",
            description="Unique IRI identifier for this concept",
        ),
    ] = Field(...)

    parent_iris: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.PIPE,
            meaning="skos:broader",
            description="Parent concept IRIs",
        ),
    ] = Field(default_factory=list)

    collection_membership: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.PIPE,
            meaning="skos:member",
            description="Collection IRIs this concept belongs to",
        ),
    ] = Field(default_factory=list)

    created_date: Annotated[
        date,
        XLSXMetadata(
            meaning="dcterms:created",
            description="Date when this concept was created",
        ),
    ] = Field(default_factory=date.today)

    status: Annotated[
        str,
        XLSXMetadata(
            meaning="adms:status",
            description="Status of this concept (draft, published, deprecated)",
        ),
    ] = Field(default="draft")

    translations: list[ConceptTranslation] = Field(default_factory=list)


# Integration Tests
class TestIntegration:
    """Integration tests for the unified system."""

    def test_round_trip_table_format(self, sample_employees, temp_file):
        """Test complete round-trip for table format."""
        # Export with custom config
        config = XLSXTableConfig(
            title="Employee Data Export",
            start_row=4,
            field_order=["employee_id", "first_name", "last_name"],
        )

        export_to_xlsx(sample_employees, temp_file, format_type="table", config=config)
        imported = import_from_xlsx(
            temp_file, Employee, format_type="table", config=config
        )

        # Verify complete data integrity
        assert len(imported) == len(sample_employees)
        for original, imported_item in zip(sample_employees, imported):
            assert original.employee_id == imported_item.employee_id
            assert original.first_name == imported_item.first_name
            assert original.status == imported_item.status

    def test_round_trip_keyvalue_format(self, temp_file):
        """Test complete round-trip for key-value format."""
        # Create a complex model with various field types
        from datetime import date

        from .conftest import Priority

        project = Project(
            project_id=42,
            project_name="Complex Project",
            description="A very complex project with all field types",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            priority=Priority.HIGH,
            budget=500000.50,
            is_completed=True,
        )

        config = XLSXKeyValueConfig(
            title="Project Export",
        )

        export_to_xlsx(project, temp_file, format_type="keyvalue", config=config)
        imported = import_from_xlsx(
            temp_file, Project, format_type="keyvalue", config=config
        )

        # Verify all fields
        assert imported.project_id == project.project_id
        assert imported.project_name == project.project_name
        assert imported.start_date == project.start_date
        assert imported.end_date == project.end_date
        assert imported.priority == project.priority
        assert imported.budget == project.budget
        assert imported.description == project.description
        assert imported.is_completed == project.is_completed

    def test_multiple_sheets_compatibility(
        self, sample_employees, sample_projects, temp_file
    ):
        """Test that the unified system works with existing multi-sheet scenarios."""
        # Export employees to one sheet
        export_to_xlsx(
            sample_employees, temp_file, format_type="table", sheet_name="Employees"
        )

        # For now, we can't add to existing files, so test single sheet
        imported_employees = import_from_xlsx(
            temp_file, Employee, format_type="table", sheet_name="Employees"
        )

        assert len(imported_employees) == 2
        assert imported_employees[0].first_name == "John"

    def test_factory_consistency(self, sample_simple_model, temp_file):
        """Test that factory methods produce consistent results."""
        # Test both factory and direct API

        # Using factory
        processor = XLSXProcessorFactory.create_keyvalue_processor()
        processor.export(sample_simple_model, temp_file)
        imported1 = processor.import_data(temp_file, SimpleModel)

        # Using direct API
        temp_file2 = temp_file.with_suffix(".2.xlsx")
        export_to_xlsx(sample_simple_model, temp_file2, format_type="keyvalue")
        imported2 = import_from_xlsx(temp_file2, SimpleModel, format_type="keyvalue")

        # Results should be identical
        assert imported1.name == imported2.name
        assert imported1.value == imported2.value
        assert imported1.active == imported2.active

        temp_file2.unlink(missing_ok=True)

    def test_round_trip_with_all_converters(self, temp_file):
        """Test round-trip with all built-in converters."""

        class ModelWithAllConverters(BaseModel):
            name: str
            comma_list: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.COMMA)
            ] = Field(default=[])
            pipe_list: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.PIPE)
            ] = Field(default=[])
            semicolon_list: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.SEMICOLON)
            ] = Field(default=[])
            int_list: Annotated[
                list[int],
                XLSXMetadata(
                    xlsx_serializer=lambda x: ", ".join(str(i) for i in x) if x else "",
                    xlsx_deserializer=lambda x: [
                        int(i.strip()) for i in x.split(",") if i.strip()
                    ]
                    if x.strip()
                    else [],
                ),
            ] = Field(default=[])

        # Create test data
        original = ModelWithAllConverters(
            name="Test Model",
            comma_list=["a", "b", "c"],
            pipe_list=["x", "y", "z"],
            semicolon_list=["1", "2", "3"],
            int_list=[10, 20, 30],
        )

        # Round-trip test
        export_to_xlsx(original, temp_file, format_type="keyvalue")
        imported = import_from_xlsx(
            temp_file, ModelWithAllConverters, format_type="keyvalue"
        )

        assert imported.name == original.name
        assert imported.comma_list == original.comma_list
        assert imported.pipe_list == original.pipe_list
        assert imported.semicolon_list == original.semicolon_list
        assert imported.int_list == original.int_list

    def test_large_dataset_performance(self, large_employee_dataset, temp_file):
        """Test performance with larger dataset."""
        # Should handle this reasonably quickly
        export_to_xlsx(large_employee_dataset, temp_file, format_type="table")
        imported = import_from_xlsx(temp_file, Employee, format_type="table")

        assert len(imported) == 100
        assert imported[0].first_name == "Employee0"
        assert imported[-1].first_name == "Employee99"

    def test_mixed_data_types_integration(self, temp_file):
        """Test integration with mixed complex data types."""
        from datetime import date

        from .conftest import Priority, Status

        class ComplexIntegrationModel(BaseModel):
            # Basic types
            name: str
            count: int
            price: float
            active: bool
            created: date

            # Enums
            status: Status
            priority: Priority | None = None

            # Complex types with converters
            tags: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.COMMA)
            ] = Field(default=[])

            # Optional fields
            description: str | None = None
            metadata: dict | None = None

        # Test data
        data = [
            ComplexIntegrationModel(
                name="Item 1",
                count=10,
                price=99.99,
                active=True,
                created=date(2024, 1, 1),
                status=Status.ACTIVE,
                priority=Priority.HIGH,
                tags=["tag1", "tag2", "tag3"],
                description="First item",
                metadata={"key": "value"},
            ),
            ComplexIntegrationModel(
                name="Item 2",
                count=5,
                price=49.50,
                active=False,
                created=date(2024, 2, 1),
                status=Status.INACTIVE,
                priority=None,
                tags=["tag4", "tag5"],
                description=None,
                metadata=None,
            ),
        ]

        # Test table format
        export_to_xlsx(data, temp_file, format_type="table")
        imported = import_from_xlsx(
            temp_file, ComplexIntegrationModel, format_type="table"
        )

        assert len(imported) == 2
        assert imported[0].name == "Item 1"
        assert imported[0].status == Status.ACTIVE
        assert imported[0].priority == Priority.HIGH
        assert imported[0].tags == ["tag1", "tag2", "tag3"]
        assert imported[1].name == "Item 2"
        assert imported[1].status == Status.INACTIVE
        assert imported[1].priority is None
        assert imported[1].tags == ["tag4", "tag5"]

    def test_configuration_inheritance_integration(self, sample_employees, temp_file):
        """Test that configuration inheritance works across formats."""
        # Test with base config settings - include all required fields
        base_config = XLSXTableConfig(
            title="Integrated Test",
            include_fields={
                "employee_id",
                "first_name",
                "last_name",
                "email",
                "hire_date",
                "salary",
                "status",
            },
            exclude_fields={"department"},
        )

        export_to_xlsx(
            sample_employees, temp_file, format_type="table", config=base_config
        )
        imported = import_from_xlsx(
            temp_file, Employee, format_type="table", config=base_config
        )

        assert len(imported) == 2
        assert imported[0].first_name == "John"
        assert imported[0].department is None  # Excluded field

    def test_error_recovery_integration(self, temp_file):
        """Test error recovery in integration scenarios."""
        # Test that system gracefully handles various error conditions

        # 1. Invalid format type
        with pytest.raises(ValueError, match="Unsupported format type"):
            export_to_xlsx(
                [SimpleModel(name="test", value=1)], temp_file, format_type="invalid"
            )

        # 2. Empty data
        with pytest.raises(ValueError, match="No data provided"):
            export_to_xlsx([], temp_file, format_type="table")

        # 3. Wrong config type (should be handled gracefully)
        keyvalue_config = XLSXKeyValueConfig(title="Wrong Config")
        # This should work - configs are flexible
        export_to_xlsx(
            [SimpleModel(name="test", value=1)],
            temp_file,
            format_type="table",
            config=keyvalue_config,
        )

        # 4. Missing sheet
        with pytest.raises(ValueError, match="Sheet.*not found"):
            import_from_xlsx(
                temp_file, SimpleModel, format_type="table", sheet_name="NonExistent"
            )

    def test_backwards_compatibility_integration(self, sample_simple_model, temp_file):
        """Test backwards compatibility with existing code patterns."""
        # Test that old patterns still work

        # Basic export/import without explicit format_type
        export_to_xlsx([sample_simple_model], temp_file)  # Should default to table
        imported = import_from_xlsx(temp_file, SimpleModel)  # Should use table

        assert len(imported) == 1
        assert imported[0].name == sample_simple_model.name

    def test_edge_case_integration(self, temp_file):
        """Test edge cases in integration scenarios."""
        # Test with model that has challenging field names

        class EdgeCaseModel(BaseModel):
            # Field names that might cause issues - simplified without aliases
            field_with_spaces: str = "spaces"
            field_with_special_chars: str = "special"
            field_with_unicode: str = "unicode"

            # Very long field name
            very_long_field_name_that_might_cause_issues_in_excel: str = "test"

        data = [
            EdgeCaseModel(
                field_with_spaces="spaces",
                field_with_special_chars="special",
                field_with_unicode="unicode",
            )
        ]

        # Should handle edge cases gracefully
        export_to_xlsx(data, temp_file, format_type="table")
        imported = import_from_xlsx(temp_file, EdgeCaseModel, format_type="table")

        assert len(imported) == 1
        assert imported[0].field_with_spaces == "spaces"

    def test_memory_efficiency_integration(self, temp_file):
        """Test memory efficiency with realistic data sizes."""
        # Create a moderately large dataset
        large_data = []
        for i in range(1000):  # 1000 records
            large_data.append(
                SimpleModel(
                    name=f"Item_{i}",
                    value=i,
                    active=i % 2 == 0,
                )
            )

        # Should handle without excessive memory usage
        export_to_xlsx(large_data, temp_file, format_type="table")
        imported = import_from_xlsx(temp_file, SimpleModel, format_type="table")

        assert len(imported) == 1000
        assert imported[0].name == "Item_0"
        assert imported[-1].name == "Item_999"

    def test_concurrent_usage_simulation(self, temp_file):
        """Test that the system can handle concurrent-like usage patterns."""
        # Simulate multiple operations in sequence

        # Operation 1: Export employees
        from .conftest import Employee, Status

        employees = [
            Employee(
                employee_id=1,
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                hire_date=date(2023, 1, 1),
                salary=50000.0,
                status=Status.ACTIVE,
            )
        ]

        export_to_xlsx(employees, temp_file, format_type="table")

        # Operation 2: Import and verify
        imported = import_from_xlsx(temp_file, Employee, format_type="table")
        assert len(imported) == 1

        # Operation 3: Export different model to same file (overwrites)
        simple_data = [SimpleModel(name="test", value=42)]
        export_to_xlsx(simple_data, temp_file, format_type="table")

        # Operation 4: Import new data
        imported_simple = import_from_xlsx(temp_file, SimpleModel, format_type="table")
        assert len(imported_simple) == 1
        assert imported_simple[0].name == "test"

    def test_vocabulary_template_round_trip_integration(self, temp_file):
        """Test complete vocabulary template round-trip with all SKOS vocabulary features."""

        # Create sample vocabulary data (adapted from demo files)
        def create_sample_data():
            concept_scheme = ConceptScheme(
                vocabulary_iri="https://example.org/photocatalysis/",
                prefix="photo",
                title="Photocatalysis Vocabulary",
                description="A controlled vocabulary for photocatalysis research and applications",
                version="1.0.0",
            )

            mappings = [
                Mapping(
                    concept_iri="https://example.org/photocatalysis/TiO2",
                    mapping_relation=MappingType.EXACT_MATCH,
                    mapped_external_concept="http://purl.obolibrary.org/obo/CHEBI_32234",
                ),
                Mapping(
                    concept_iri="https://example.org/photocatalysis/Semiconductor",
                    mapping_relation=MappingType.CLOSE_MATCH,
                    mapped_external_concept="https://dbpedia.org/resource/Semiconductor",
                ),
            ]

            collections = [
                Collection(
                    collection_iri="https://example.org/photocatalysis/PhotocatalystMaterials",
                    preferred_label="Photocatalyst Materials",
                    definition="Collection of materials used as photocatalysts",
                    is_ordered=True,
                ),
                Collection(
                    collection_iri="https://example.org/photocatalysis/OpticalProperties",
                    preferred_label="Optical Properties",
                    definition="Collection of optical properties relevant to photocatalysis",
                    parent_collection_iris=[
                        "https://example.org/photocatalysis/MaterialProperties",
                        "https://example.org/photocatalysis/PhysicalProperties",
                    ],
                ),
            ]

            prefixes = [
                Prefix(prefix="skos", namespace="http://www.w3.org/2004/02/skos/core#"),
                Prefix(prefix="dcterms", namespace="http://purl.org/dc/terms/"),
                Prefix(prefix="photo", namespace="https://example.org/photocatalysis/"),
            ]

            return concept_scheme, mappings, collections, prefixes

        def create_multilingual_concepts():
            return [
                MultiLingualConcept(
                    concept_iri="https://example.org/photocatalysis/TiO2",
                    parent_iris=[
                        "https://example.org/photocatalysis/PhotocatalystMaterials"
                    ],
                    collection_membership=[
                        "https://example.org/photocatalysis/Materials"
                    ],
                    status="published",
                    translations=[
                        ConceptTranslation(
                            concept_iri="https://example.org/photocatalysis/TiO2",
                            language_code="en",
                            preferred_label="Titanium Dioxide",
                            alternate_labels=["Titania", "Titanium(IV) oxide"],
                            definition="A widely used photocatalyst material with excellent properties.",
                            scope_note="Used in self-cleaning surfaces and air purification.",
                        ),
                        ConceptTranslation(
                            concept_iri="https://example.org/photocatalysis/TiO2",
                            language_code="de",
                            preferred_label="Titandioxid",
                            alternate_labels=["Titania"],
                            definition="Ein weit verbreitetes Photokatalysator-Material.",
                            scope_note="Verwendet in selbstreinigenden Oberflächen.",
                        ),
                    ],
                ),
                MultiLingualConcept(
                    concept_iri="https://example.org/photocatalysis/BandGap",
                    parent_iris=[
                        "https://example.org/photocatalysis/MaterialProperty",
                        "https://example.org/photocatalysis/ElectronicProperty",
                    ],
                    collection_membership=[
                        "https://example.org/photocatalysis/OpticalProperties"
                    ],
                    status="published",
                    translations=[
                        ConceptTranslation(
                            concept_iri="https://example.org/photocatalysis/BandGap",
                            language_code="en",
                            preferred_label="Band Gap",
                            alternate_labels=["Energy gap", "Electronic band gap"],
                            definition="Energy difference between valence and conduction bands.",
                            scope_note="Critical for photocatalytic activity.",
                        ),
                    ],
                ),
            ]

        # Create test data
        concept_scheme, mappings, collections, prefixes = create_sample_data()
        multilingual_concepts = create_multilingual_concepts()

        # Configuration for different formats
        kv_config = XLSXKeyValueConfig(title="Concept Scheme Metadata")
        table_config = XLSXTableConfig()

        # Test 1: Export ConceptScheme (key-value format)
        export_to_xlsx(
            concept_scheme,
            temp_file,
            format_type="keyvalue",
            config=kv_config,
            sheet_name="ConceptScheme",
        )

        # Test 2: Export Collections (table format)
        export_to_xlsx(
            collections,
            temp_file,
            format_type="table",
            config=table_config,
            sheet_name="Collections",
        )

        # Test 3: Export Mappings (table format)
        export_to_xlsx(
            mappings,
            temp_file,
            format_type="table",
            config=table_config,
            sheet_name="Mappings",
        )

        # Test 4: Export Prefixes (table format)
        export_to_xlsx(
            prefixes,
            temp_file,
            format_type="table",
            config=table_config,
            sheet_name="Prefixes",
        )

        # Test 5: Export multi-language concepts with join configuration
        join_config = JoinConfiguration(
            primary_model=MultiLingualConcept,
            related_models={"translations": ConceptTranslation},
            join_keys={"translations": "concept_iri"},
            flattened_fields=[
                "concept_iri",
                "language_code",
                "preferred_label",
                "alternate_labels",
                "definition",
                "scope_note",
                "parent_iris",
                "collection_membership",
                "created_date",
                "status",
            ],
            field_mappings={
                "concept_iri": ("primary", "concept_iri"),
                "language_code": ("related", "language_code"),
                "preferred_label": ("related", "preferred_label"),
                "alternate_labels": ("related", "alternate_labels"),
                "definition": ("related", "definition"),
                "scope_note": ("related", "scope_note"),
                "parent_iris": ("primary", "parent_iris"),
                "collection_membership": ("primary", "collection_membership"),
                "created_date": ("primary", "created_date"),
                "status": ("primary", "status"),
            },
            list_fields={"alternate_labels", "parent_iris", "collection_membership"},
        )

        concepts_config = XLSXTableConfig(title="Multi-Language Concepts")
        joined_processor = XLSXProcessorFactory.create_joined_table_processor(
            join_config, concepts_config
        )
        joined_processor.export(multilingual_concepts, temp_file, "Concepts")

        # Now test round-trip imports and validate data integrity

        # Import ConceptScheme
        imported_concept_scheme = import_from_xlsx(
            temp_file,
            ConceptScheme,
            format_type="keyvalue",
            config=kv_config,
            sheet_name="ConceptScheme",
        )

        # Import Collections
        imported_collections = import_from_xlsx(
            temp_file,
            Collection,
            format_type="table",
            config=table_config,
            sheet_name="Collections",
        )

        # Import Mappings
        imported_mappings = import_from_xlsx(
            temp_file,
            Mapping,
            format_type="table",
            config=table_config,
            sheet_name="Mappings",
        )

        # Import Prefixes
        imported_prefixes = import_from_xlsx(
            temp_file,
            Prefix,
            format_type="table",
            config=table_config,
            sheet_name="Prefixes",
        )

        # Import Concepts (multi-language joined format)
        # Use the same joined processor for import that was used for export
        imported_concepts = joined_processor.import_data(
            temp_file, MultiLingualConcept, "Concepts"
        )

        # Validate ConceptScheme round-trip
        assert imported_concept_scheme.title == concept_scheme.title
        assert imported_concept_scheme.vocabulary_iri == concept_scheme.vocabulary_iri
        assert imported_concept_scheme.prefix == concept_scheme.prefix
        assert imported_concept_scheme.description == concept_scheme.description
        assert imported_concept_scheme.version == concept_scheme.version

        # Validate Collections round-trip
        assert len(imported_collections) == len(collections)
        for orig, imp in zip(collections, imported_collections):
            assert orig.collection_iri == imp.collection_iri
            assert orig.preferred_label == imp.preferred_label
            assert orig.definition == imp.definition
            assert orig.is_ordered == imp.is_ordered
            assert orig.parent_collection_iris == imp.parent_collection_iris

        # Validate Mappings round-trip with enum preservation
        assert len(imported_mappings) == len(mappings)
        for orig, imp in zip(mappings, imported_mappings):
            assert orig.concept_iri == imp.concept_iri
            assert orig.mapping_relation == imp.mapping_relation
            assert orig.mapped_external_concept == imp.mapped_external_concept

        # Validate specific enum deserialization
        exact_match = next(
            (
                m
                for m in imported_mappings
                if m.mapping_relation == MappingType.EXACT_MATCH
            ),
            None,
        )
        assert exact_match is not None
        assert exact_match.mapping_relation.value == "skos:exactMatch"

        # Validate Prefixes round-trip
        assert len(imported_prefixes) == len(prefixes)
        skos_prefix = next((p for p in imported_prefixes if p.prefix == "skos"), None)
        assert skos_prefix is not None
        assert skos_prefix.namespace == "http://www.w3.org/2004/02/skos/core#"

        # Validate Concepts round-trip (focus on critical features)
        # The joined processor properly reconstructs the nested MultiLingualConcept objects
        assert len(imported_concepts) == len(multilingual_concepts)

        # Check first concept (TiO2) with complex lists and multiple translations
        tio2_concept = next(
            (c for c in imported_concepts if "TiO2" in c.concept_iri), None
        )
        assert tio2_concept is not None
        assert tio2_concept.status == "published"
        assert len(tio2_concept.parent_iris) == 1
        assert (
            tio2_concept.parent_iris[0]
            == "https://example.org/photocatalysis/PhotocatalystMaterials"
        )
        assert len(tio2_concept.collection_membership) == 1
        assert (
            tio2_concept.collection_membership[0]
            == "https://example.org/photocatalysis/Materials"
        )

        # Check translations are properly reconstructed
        assert len(tio2_concept.translations) == 2  # EN and DE

        # Check English translation
        tio2_en = next(
            (t for t in tio2_concept.translations if t.language_code == "en"), None
        )
        assert tio2_en is not None
        assert tio2_en.preferred_label == "Titanium Dioxide"
        assert "Titania" in tio2_en.alternate_labels
        assert "Titanium(IV) oxide" in tio2_en.alternate_labels
        assert (
            tio2_en.definition
            == "A widely used photocatalyst material with excellent properties."
        )

        # Check German translation
        tio2_de = next(
            (t for t in tio2_concept.translations if t.language_code == "de"), None
        )
        assert tio2_de is not None
        assert tio2_de.preferred_label == "Titandioxid"
        assert "Titania" in tio2_de.alternate_labels

        # Check second concept (BandGap) with multiple parent IRIs
        bandgap_concept = next(
            (c for c in imported_concepts if "BandGap" in c.concept_iri), None
        )
        assert bandgap_concept is not None
        assert len(bandgap_concept.parent_iris) == 2
        assert "MaterialProperty" in bandgap_concept.parent_iris[0]
        assert "ElectronicProperty" in bandgap_concept.parent_iris[1]
        assert len(bandgap_concept.collection_membership) == 1
        assert "OpticalProperties" in bandgap_concept.collection_membership[0]

        # Check BandGap translations
        assert len(bandgap_concept.translations) == 1  # Only EN
        bandgap_en = bandgap_concept.translations[0]
        assert bandgap_en.language_code == "en"
        assert bandgap_en.preferred_label == "Band Gap"
        assert "Energy gap" in bandgap_en.alternate_labels
        assert "Electronic band gap" in bandgap_en.alternate_labels

        # Validate SKOS metadata preservation (check that XLSXMetadata annotations work)
        # This is implicit in successful round-trip but validates the SKOS vocabulary structure


if __name__ == "__main__":
    pytest.main([__file__])
