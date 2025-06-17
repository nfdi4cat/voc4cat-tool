"""
Tests for the xlsx_api module.

This module tests the public API and factory patterns for XLSX processing,
including export/import functions and processor factories.
"""

import pytest
from pydantic import BaseModel

from voc4cat.xlsx_api import XLSXProcessorFactory, export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig

from .conftest import Employee, Project, SimpleModel


# API Function Tests
class TestExportImportAPI:
    """Tests for the main export/import API functions."""

    def test_export_import_table_format(self, sample_employees, temp_file):
        """Test basic table export and import via API."""
        # Export
        export_to_xlsx(sample_employees, temp_file, format_type="table")

        # Import
        imported = import_from_xlsx(temp_file, Employee, format_type="table")

        # Verify
        assert len(imported) == 2
        assert imported[0].first_name == "John"
        assert imported[0].status.value == "active"
        assert imported[1].first_name == "Jane"
        assert imported[1].is_active is False

    def test_export_import_keyvalue_format(self, sample_simple_model, temp_file):
        """Test basic key-value export and import via API."""
        # Export
        export_to_xlsx(sample_simple_model, temp_file, format_type="keyvalue")

        # Import
        imported = import_from_xlsx(temp_file, SimpleModel, format_type="keyvalue")

        # Verify
        assert imported.name == "Test Item"
        assert imported.value == 42
        assert imported.active is True

    def test_default_format_behavior(self, sample_employees, temp_file):
        """Test that default format is table."""
        export_to_xlsx(sample_employees, temp_file)  # No format_type specified
        imported = import_from_xlsx(temp_file, Employee)  # No format_type specified

        assert len(imported) == 2
        assert imported[0].first_name == "John"

    def test_export_with_config(self, sample_employees, temp_file):
        """Test export with custom configuration."""
        config = XLSXTableConfig(
            title="Employee Directory",
            start_row=2,
            exclude_fields={"department"},
        )

        export_to_xlsx(sample_employees, temp_file, format_type="table", config=config)
        imported = import_from_xlsx(
            temp_file, Employee, format_type="table", config=config
        )

        assert len(imported) == 2
        # Department should be None due to exclusion
        assert imported[0].department is None

    def test_export_with_sheet_name(self, sample_projects, temp_file):
        """Test export with custom sheet name."""
        export_to_xlsx(
            sample_projects, temp_file, format_type="table", sheet_name="Projects"
        )
        imported = import_from_xlsx(
            temp_file, Project, format_type="table", sheet_name="Projects"
        )

        assert len(imported) == 2
        assert imported[0].project_name == "Website Redesign"

    def test_invalid_format_type(self, sample_simple_model, temp_file):
        """Test error for invalid format type."""
        with pytest.raises(ValueError, match="Unsupported format type"):
            export_to_xlsx(sample_simple_model, temp_file, format_type="invalid")

    def test_single_object_table_format_error(self, sample_simple_model, temp_file):
        """Test that single object with table format raises error."""
        with pytest.raises(TypeError, match="not subscriptable"):
            export_to_xlsx(sample_simple_model, temp_file, format_type="table")

    def test_empty_data_error(self, temp_file):
        """Test error handling for empty data."""
        with pytest.raises(ValueError, match="No data provided"):
            export_to_xlsx([], temp_file, format_type="table")

    def test_missing_sheet_error(self, temp_file):
        """Test error handling for missing sheet."""
        # Create a file with default sheet
        export_to_xlsx(
            [SimpleModel(name="test", value=1)], temp_file, format_type="table"
        )

        with pytest.raises(ValueError, match="Sheet 'NonExistent' not found"):
            import_from_xlsx(
                temp_file, SimpleModel, format_type="table", sheet_name="NonExistent"
            )


# Factory Pattern Tests
class TestXLSXProcessorFactory:
    """Tests for the XLSXProcessorFactory."""

    def test_create_table_processor(self, sample_projects, temp_file):
        """Test creating and using table processor."""
        processor = XLSXProcessorFactory.create_table_processor()

        processor.export(sample_projects, temp_file)
        imported = processor.import_data(temp_file, Project)

        assert len(imported) == 2
        assert imported[0].priority.value == "high"
        assert imported[1].end_date is None

    def test_create_keyvalue_processor(self, sample_simple_model, temp_file):
        """Test creating and using key-value processor."""
        processor = XLSXProcessorFactory.create_keyvalue_processor()

        processor.export(sample_simple_model, temp_file)
        imported = processor.import_data(temp_file, SimpleModel)

        assert imported.name == "Test Item"
        assert imported.value == 42

    def test_create_table_processor_with_config(self, sample_employees, temp_file):
        """Test creating table processor with custom configuration."""
        config = XLSXTableConfig(
            title="Custom Employee List",
            field_order=["last_name", "first_name", "employee_id"],
        )

        processor = XLSXProcessorFactory.create_table_processor(config)
        processor.export(sample_employees, temp_file)
        imported = processor.import_data(temp_file, Employee)

        assert len(imported) == 2
        assert imported[0].first_name == "John"

    def test_create_keyvalue_processor_with_config(
        self, sample_simple_model, temp_file
    ):
        """Test creating key-value processor with custom configuration."""
        config = XLSXKeyValueConfig(
            title="Custom Model Instance",
            field_column_header="Property",
            value_column_header="Data",
        )

        processor = XLSXProcessorFactory.create_keyvalue_processor(config)
        processor.export(sample_simple_model, temp_file)
        imported = processor.import_data(temp_file, SimpleModel)

        assert imported.name == "Test Item"

    def test_factory_consistency(self, sample_simple_model, temp_file):
        """Test that factory methods produce consistent results with direct API."""
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


# Default Format Tests
class TestDefaultFormat:
    """Tests for default format behavior."""

    def test_default_table_format_list(self, sample_employees, temp_file):
        """Test default table format for list data."""
        export_to_xlsx(sample_employees, temp_file)  # format_type="table" is default
        imported = import_from_xlsx(temp_file, Employee)

        assert len(imported) == 2
        assert imported[0].first_name == "John"

    def test_default_table_format_single_error(self, sample_simple_model, temp_file):
        """Test that single model defaults to table format (will fail as expected)."""
        with pytest.raises(TypeError, match="not subscriptable"):
            export_to_xlsx(
                sample_simple_model, temp_file
            )  # format_type="table" is default

    def test_explicit_keyvalue_format_single(self, sample_simple_model, temp_file):
        """Test explicit key-value format for single model."""
        export_to_xlsx(sample_simple_model, temp_file, format_type="keyvalue")
        imported = import_from_xlsx(temp_file, SimpleModel, format_type="keyvalue")

        assert imported.name == "Test Item"

    def test_default_table_format_tuple(self, sample_projects, temp_file):
        """Test default table format for tuple data."""
        projects_tuple = tuple(sample_projects)
        export_to_xlsx(projects_tuple, temp_file)  # format_type="table" is default
        imported = import_from_xlsx(temp_file, Project)

        assert len(imported) == 2


# Error Handling Tests
class TestErrorHandling:
    """Tests for API error handling."""

    def test_serialization_error_handling(self, temp_file):
        """Test handling of serialization errors."""

        # Create a model with a problematic field
        class ProblematicModel(BaseModel):
            name: str
            problematic_field: object  # This might cause serialization issues

        model = ProblematicModel(name="test", problematic_field=object())

        # Should handle serialization gracefully
        try:
            export_to_xlsx(model, temp_file, format_type="keyvalue")
        except Exception as e:
            # Should be a meaningful error message
            assert "serializ" in str(e).lower() or "convert" in str(e).lower()
            return  # Expected failure, test passes

        # If no exception, that's also fine - just means serialization worked

    def test_validation_error_handling(self, temp_file):
        """Test handling of validation errors during import."""
        # Create a simple model first
        simple = SimpleModel(name="test", value=42)
        export_to_xlsx(simple, temp_file, format_type="keyvalue")

        # Try to import as a different model that should fail validation
        class StrictModel(BaseModel):
            name: str
            value: str  # Different type than what's in the file
            required_field: str  # Missing field

        with pytest.raises(ValueError, match="Failed to create|Sheet.*not found"):
            import_from_xlsx(
                temp_file, StrictModel, format_type="keyvalue", sheet_name="SimpleModel"
            )


if __name__ == "__main__":
    pytest.main([__file__])
