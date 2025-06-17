"""
Tests for integration scenarios and real-world use cases.

This module tests complex integration scenarios, performance, and edge cases
that span multiple modules in the XLSX processing system.
"""

from datetime import date
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from voc4cat.xlsx_api import XLSXProcessorFactory, export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import XLSXConverters, XLSXMetadata
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig

from .conftest import Employee, Project, SimpleModel


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


if __name__ == "__main__":
    pytest.main([__file__])
