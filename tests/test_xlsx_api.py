"""
Tests for the xlsx_api module.

This module tests the public API and factory patterns for XLSX processing,
including export/import functions and processor factories.
"""

from datetime import date

import pytest
from pydantic import BaseModel

from voc4cat.xlsx_api import (
    XLSXProcessorFactory,
    create_xlsx_wrapper,
    export_to_xlsx,
    import_from_xlsx,
)
from voc4cat.xlsx_common import XLSXMetadata
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig

from .conftest import (
    DemoModelWithMetadata,
    Employee,
    Project,
    SimpleModel,
    Status,
)


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

        with pytest.raises(ValueError, match=r"Failed to create|Sheet.*not found"):
            import_from_xlsx(
                temp_file, StrictModel, format_type="keyvalue", sheet_name="SimpleModel"
            )


# XLSX Wrapper Tests
class TestCreateXLSXWrapper:
    """Tests for the create_xlsx_wrapper function."""

    def test_simple_wrapper_creation(self):
        """Test basic wrapper creation with metadata."""

        # Create metadata for SimpleModel
        metadata_map = {
            "value": XLSXMetadata(unit="count", description="Item count"),
            "name": XLSXMetadata(description="Item identifier"),
        }

        # Create wrapper
        XLSXSimpleModel = create_xlsx_wrapper(SimpleModel, metadata_map)

        # Test wrapper properties
        assert XLSXSimpleModel.__name__ == "XLSXSimpleModel"
        assert issubclass(XLSXSimpleModel, SimpleModel)

        # Test instance creation
        item = XLSXSimpleModel(name="TestItem", value=42, active=True)
        assert item.name == "TestItem"
        assert item.value == 42
        assert item.active is True

    def test_wrapper_inheritance_chain(self):
        """Test wrapper creation with inheritance."""

        # Create base wrapper for Employee
        base_metadata = {
            "salary": XLSXMetadata(unit="USD", description="Base salary info"),
            "email": XLSXMetadata(description="Base email info"),
        }
        XLSXBaseEmployee = create_xlsx_wrapper(Employee, base_metadata)

        # Create enhanced wrapper that builds on the base wrapper
        enhanced_metadata = {
            "hire_date": XLSXMetadata(description="Date of hire"),
            "department": XLSXMetadata(description="Employee department"),
        }
        XLSXEnhancedEmployee = create_xlsx_wrapper(
            Employee, enhanced_metadata, base_wrapper=XLSXBaseEmployee
        )

        # Test inheritance relationships
        assert XLSXEnhancedEmployee.__name__ == "XLSXEmployee"
        assert issubclass(XLSXEnhancedEmployee, XLSXBaseEmployee)

        # Test instance creation and field access
        employee = XLSXEnhancedEmployee(
            employee_id=1,
            first_name="John",
            last_name="Doe",
            email="john@company.com",
            hire_date=date(2023, 1, 15),
            salary=75000.0,
            status=Status.ACTIVE,
            department="Engineering",
            is_active=True,
        )

        assert employee.employee_id == 1
        assert employee.first_name == "John"
        assert employee.salary == 75000.0
        assert employee.status == Status.ACTIVE
        assert employee.department == "Engineering"

    def test_wrapper_isinstance_relationships(self):
        """Test that isinstance relationships work correctly."""

        # Create wrapper for Employee
        employee_metadata = {"salary": XLSXMetadata(unit="USD")}
        XLSXEmployee = create_xlsx_wrapper(Employee, employee_metadata)

        # Create second wrapper that inherits from the first
        enhanced_metadata = {"hire_date": XLSXMetadata(description="Hire date")}
        XLSXEnhancedEmployee = create_xlsx_wrapper(
            Employee, enhanced_metadata, base_wrapper=XLSXEmployee
        )

        instance = XLSXEnhancedEmployee(
            employee_id=1,
            first_name="John",
            last_name="Doe",
            email="john@test.com",
            hire_date=date(2023, 1, 1),
            salary=50000.0,
            status=Status.ACTIVE,
            department="Engineering",
            is_active=True,
        )

        # Test isinstance relationships
        assert isinstance(instance, Employee)  # Original model
        assert isinstance(instance, XLSXEmployee)  # Base wrapper
        assert isinstance(instance, XLSXEnhancedEmployee)  # Enhanced wrapper

    def test_wrapper_round_trip_keyvalue(self, temp_file, sample_project):
        """Test wrapper with xlsx round-trip in key-value format."""

        # Create wrapper with metadata for Project model
        metadata_map = {
            "budget": XLSXMetadata(unit="USD", description="Project budget"),
            "project_name": XLSXMetadata(description="Project identifier"),
            "priority": XLSXMetadata(description="Project priority level"),
        }

        XLSXProject = create_xlsx_wrapper(Project, metadata_map)

        # Use sample project data
        project = XLSXProject(**sample_project.__dict__)

        # Export to XLSX
        export_to_xlsx(project, temp_file, format_type="keyvalue")

        # Import from XLSX
        imported = import_from_xlsx(temp_file, XLSXProject, format_type="keyvalue")

        # Verify data integrity
        assert imported.project_id == sample_project.project_id
        assert imported.project_name == sample_project.project_name
        assert imported.priority == sample_project.priority
        assert imported.budget == sample_project.budget
        assert imported.description == sample_project.description

        # Verify types are preserved
        assert isinstance(imported, XLSXProject)
        assert isinstance(imported, Project)

    def test_wrapper_round_trip_table(
        self, temp_file, sample_employees, xlsx_metadata_map
    ):
        """Test wrapper with xlsx round-trip in table format."""

        XLSXEmployee = create_xlsx_wrapper(Employee, xlsx_metadata_map)

        # Use sample employee data
        employees = [XLSXEmployee(**emp.__dict__) for emp in sample_employees]

        # Export to XLSX
        export_to_xlsx(employees, temp_file, format_type="table")

        # Import from XLSX
        imported = import_from_xlsx(temp_file, XLSXEmployee, format_type="table")

        # Verify data integrity
        assert len(imported) == len(sample_employees)
        assert imported[0].first_name == sample_employees[0].first_name
        assert imported[0].salary == sample_employees[0].salary
        assert imported[0].department == sample_employees[0].department
        assert imported[1].first_name == sample_employees[1].first_name
        assert imported[1].salary == sample_employees[1].salary

        # Verify types
        assert all(isinstance(emp, XLSXEmployee) for emp in imported)
        assert all(isinstance(emp, Employee) for emp in imported)

    def test_wrapper_preserves_field_defaults(self):
        """Test that wrapper preserves field defaults from original model."""

        metadata_map = {
            "salary": XLSXMetadata(unit="USD", description="Annual salary"),
            "first_name": XLSXMetadata(description="Employee first name"),
        }

        XLSXEmployee = create_xlsx_wrapper(Employee, metadata_map)

        # Test instance creation with explicit values for fields with defaults
        # (Employee has defaults: department=None, is_active=True)
        instance = XLSXEmployee(
            employee_id=1,
            first_name="John",
            last_name="Doe",
            email="john@test.com",
            hire_date=date(2023, 1, 1),
            salary=50000.0,
            status=Status.ACTIVE,
            department=None,  # default
            is_active=True,  # default
        )
        assert instance.first_name == "John"
        assert instance.department is None  # default value
        assert instance.is_active is True  # default value

        # Test with explicit non-default values
        instance2 = XLSXEmployee(
            employee_id=2,
            first_name="Jane",
            last_name="Smith",
            email="jane@test.com",
            hire_date=date(2023, 2, 1),
            salary=60000.0,
            status=Status.INACTIVE,
            department="Engineering",  # non-default
            is_active=False,  # non-default
        )
        assert instance2.department == "Engineering"
        assert instance2.is_active is False

    def test_wrapper_error_handling(self):
        """Test wrapper creation error handling."""

        # Test empty metadata
        XLSXSimpleModel = create_xlsx_wrapper(SimpleModel, {})
        instance = XLSXSimpleModel(name="test", value=42, active=True)
        assert instance.name == "test"
        assert instance.value == 42
        assert instance.active is True

        # Test metadata for non-existent field (should not cause error)
        metadata_map = {
            "name": XLSXMetadata(description="Item name"),
            "non_existent_field": XLSXMetadata(description="This field doesn't exist"),
        }
        XLSXSimpleModel2 = create_xlsx_wrapper(SimpleModel, metadata_map)
        instance2 = XLSXSimpleModel2(name="test", value=123, active=False)
        assert instance2.name == "test"
        assert instance2.value == 123
        assert instance2.active is False

    def test_import_from_xlsx_with_full_metadata(
        self, temp_file, sample_model_with_metadata
    ):
        """Test import_from_xlsx with key-value format containing all metadata fields."""

        # Export to XLSX (this will create a KV format with all metadata columns)
        export_to_xlsx(sample_model_with_metadata, temp_file, format_type="keyvalue")

        # Import from XLSX - this is the key test to ensure all metadata is handled
        imported = import_from_xlsx(
            temp_file, DemoModelWithMetadata, format_type="keyvalue"
        )

        # Verify data integrity
        assert imported.temp == sample_model_with_metadata.temp
        assert imported.name == sample_model_with_metadata.name

        # Verify types are preserved
        assert isinstance(imported, DemoModelWithMetadata)

        # Test that the import correctly handles all metadata columns:
        # - Unit column (°C for temp field)
        # - Meaning column (Temperature measurement, Sample name)
        # - Description column (Temperature reading, Sample identifier)
        # This validates that import_from_xlsx can parse KV tables with all extra fields

    def test_import_from_xlsx_kv_with_custom_config(self, temp_file, sample_employee):
        """Test import_from_xlsx with custom key-value configuration and full metadata."""

        # Create wrapper for Employee with comprehensive metadata
        metadata_map = {
            "salary": XLSXMetadata(
                unit="USD",
                meaning="Annual compensation",
                description="Employee annual salary in US dollars",
            ),
            "first_name": XLSXMetadata(
                meaning="Given name",
                description="Employee's first or given name",
            ),
            "hire_date": XLSXMetadata(
                meaning="Employment start date",
                description="Date when employee was hired",
            ),
        }

        XLSXEmployee = create_xlsx_wrapper(Employee, metadata_map)

        # Use sample employee data
        employee = XLSXEmployee(**sample_employee.__dict__)

        # Custom config with different column headers
        config = XLSXKeyValueConfig(
            title="Employee Data with Full Metadata",
            field_column_header="Property",
            value_column_header="Data",
            description_column_header="Info",
            meaning_column_header="Semantic Meaning",
            unit_column_header="Unit of Measure",
        )

        # Export to XLSX with custom config
        export_to_xlsx(employee, temp_file, format_type="keyvalue", config=config)

        # Import from XLSX with same custom config
        imported = import_from_xlsx(
            temp_file, XLSXEmployee, format_type="keyvalue", config=config
        )

        # Verify data integrity
        assert imported.employee_id == sample_employee.employee_id
        assert imported.first_name == sample_employee.first_name
        assert imported.salary == sample_employee.salary
        assert imported.hire_date == sample_employee.hire_date

        # Verify types are preserved
        assert isinstance(imported, XLSXEmployee)
        assert isinstance(imported, Employee)

    def test_import_from_xlsx_auto_detection_kv_with_metadata(
        self, temp_file, sample_model_with_metadata
    ):
        """Test auto format detection for key-value tables with all metadata columns."""

        # Export to XLSX in key-value format with all metadata columns
        export_to_xlsx(sample_model_with_metadata, temp_file, format_type="keyvalue")

        # Import using "auto" format detection - should detect key-value format
        # because the sheet will have "Field", "Value", "Unit", "Meaning", "Description" columns
        imported = import_from_xlsx(
            temp_file, DemoModelWithMetadata, format_type="auto"
        )

        # Verify data integrity - auto-detection should work correctly
        assert imported.temp == sample_model_with_metadata.temp
        assert imported.name == sample_model_with_metadata.name

        # Verify types are preserved
        assert isinstance(imported, DemoModelWithMetadata)

        # Test that auto-detection correctly identified this as key-value format
        # by verifying that it imported a single instance (not a list)
        assert not isinstance(imported, list)

    def test_import_from_xlsx_auto_detection_table_fallback(
        self, temp_file, sample_employees
    ):
        """Test auto format detection falls back to table format for list data."""

        # Export as table format
        export_to_xlsx(sample_employees, temp_file, format_type="table")

        # Import using "auto" format detection - should detect table format
        imported = import_from_xlsx(temp_file, Employee, format_type="auto")

        # Verify data integrity - auto-detection should work correctly
        assert len(imported) == len(sample_employees)
        assert imported[0].first_name == sample_employees[0].first_name
        assert imported[1].first_name == sample_employees[1].first_name

        # Test that auto-detection correctly identified this as table format
        # by verifying that it returned a list
        assert isinstance(imported, list)


if __name__ == "__main__":
    pytest.main([__file__])
