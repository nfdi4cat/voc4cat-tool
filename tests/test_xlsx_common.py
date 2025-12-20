"""
Tests for the xlsx_common module.

This module tests the common functionality used across the XLSX processing system,
including field analysis, serialization engine, metadata handling, and converters.
"""

from datetime import date, datetime
from typing import Annotated, Optional, Union

import pytest
from openpyxl import load_workbook
from pydantic import BaseModel, Field, HttpUrl

from voc4cat.fields import ORCIDIdentifier, RORIdentifier
from voc4cat.xlsx_api import export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_common import (
    FieldAnalysis,
    XLSXConfig,
    XLSXConverters,
    XLSXDeserializationError,
    XLSXFieldAnalyzer,
    XLSXMetadata,
    XLSXSerializationEngine,
    XLSXSerializationError,
    _validate_unit_usage,
)

from .conftest import DemoModelWithMetadata, Priority, SimpleModel, Status


# ORCID/ROR Test Model (only used in this file)
class ResearcherModel(BaseModel):
    """Test model for ORCID/ROR identifiers."""

    name: str
    orcid: ORCIDIdentifier
    home_organization: RORIdentifier | None = None


@pytest.fixture
def sample_researcher():
    """Sample researcher with ORCID and ROR for testing."""
    return ResearcherModel(
        name="Dr. Jane Smith",
        orcid="https://orcid.org/0000-0002-1825-0097",
        home_organization="https://ror.org/02y72wh86",
    )


@pytest.fixture
def sample_researchers():
    """Sample researcher list for table testing."""
    return [
        ResearcherModel(
            name="Dr. Jane Smith",
            orcid="https://orcid.org/0000-0002-1825-0097",
            home_organization="https://ror.org/02y72wh86",
        ),
        ResearcherModel(
            name="Dr. John Doe",
            orcid="0000-0002-1694-233X",  # Test ID-only format
            home_organization=None,
        ),
    ]


# Tests for XLSXMetadata
class TestXLSXMetadata:
    """Tests for XLSXMetadata and Annotated field handling."""

    def test_xlsx_metadata_basic(self):
        """Test basic XLSXMetadata functionality."""
        metadata = XLSXMetadata(unit="kg")
        assert metadata.unit == "kg"
        assert metadata.meaning is None
        assert metadata.display_name is None
        assert metadata.description is None

    def test_xlsx_metadata_with_all_fields(self):
        """Test XLSXMetadata with all fields."""
        metadata = XLSXMetadata(
            unit="kg",
            meaning="http://example.org/weight",
            display_name="Weight",
            description="Weight measurement",
        )
        assert metadata.unit == "kg"
        assert metadata.meaning == "http://example.org/weight"
        assert metadata.display_name == "Weight"
        assert metadata.description == "Weight measurement"

    def test_annotated_field_extraction(self):
        """Test extraction of metadata from Annotated fields."""
        fields = XLSXFieldAnalyzer.analyze_model(DemoModelWithMetadata)
        temp_field = next(f for f in fields.values() if f.name == "temp")
        assert temp_field.xlsx_metadata is not None
        assert temp_field.xlsx_metadata.unit == "°C"
        assert temp_field.xlsx_metadata.meaning == "Temperature measurement"


# Tests for XLSXConverters
class TestXLSXConverters:
    """Tests for XLSXConverters utility class."""

    def test_comma_pattern_converters(self):
        """Test comma pattern string converters."""
        to_comma, from_comma = XLSXConverters.comma_converters()

        assert to_comma(["a", "b", "c"]) == "a, b, c"
        assert to_comma([1, 2, 3]) == "1, 2, 3"
        assert to_comma([]) == ""
        assert to_comma(None) == ""

        assert from_comma("a, b, c") == ["a", "b", "c"]
        assert from_comma("a,b,c") == ["a,b,c"]  # No spaces, so treated as one item
        assert from_comma("") == []
        assert from_comma("   ") == []
        assert from_comma("a, , c") == ["a", "", "c"]  # Empty strings are preserved

    def test_pipe_pattern_converters(self):
        """Test pipe pattern string converters."""
        to_pipe, from_pipe = XLSXConverters.pipe_converters()

        assert to_pipe(["a", "b", "c"]) == "a | b | c"
        assert to_pipe([1, 2, 3]) == "1 | 2 | 3"
        assert to_pipe([]) == ""
        assert to_pipe(None) == ""

        assert from_pipe("a | b | c") == ["a", "b", "c"]
        assert from_pipe("a|b|c") == ["a|b|c"]  # No spaces, so treated as one item
        assert from_pipe("") == []
        assert from_pipe("   ") == []
        assert from_pipe("a |  | c") == [
            "a",
            "",
            "c",
        ]  # Empty strings are preserved (two spaces)

    def test_semicolon_pattern_converters(self):
        """Test semicolon pattern string converters."""
        to_semi, from_semi = XLSXConverters.semicolon_converters()

        assert to_semi(["a", "b", "c"]) == "a; b; c"
        assert to_semi([1, 2, 3]) == "1; 2; 3"
        assert to_semi([]) == ""
        assert to_semi(None) == ""

        assert from_semi("a; b; c") == ["a", "b", "c"]
        assert from_semi("a;b;c") == ["a;b;c"]  # No spaces, so treated as one item
        assert from_semi("") == []
        assert from_semi("   ") == []
        assert from_semi("a; ; c") == ["a", "", "c"]  # Empty strings are preserved

    def test_integer_pattern_converters(self):
        """Test integer list converters."""
        to_int, from_int = XLSXConverters.create_int_separated_converters(
            XLSXConverters.COMMA
        )

        assert to_int([1, 2, 3]) == "1, 2, 3"  # COMMA pattern includes space
        assert to_int([]) == ""
        assert to_int(None) == ""

        assert from_int("1, 2, 3") == [1, 2, 3]
        assert from_int("") == []
        assert from_int("   ") == []
        # Test that empty strings in integer lists raise ValueError
        with pytest.raises(ValueError, match=r"Cannot convert.*to list of integers"):
            from_int("1, , 3")

    def test_integer_conversion_error(self):
        """Test error handling in integer list conversion."""
        _, from_int = XLSXConverters.create_int_separated_converters(",")
        with pytest.raises(ValueError, match=r"Cannot convert.*to list of integers"):
            from_int("1, abc, 3")

    def test_escaped_pattern_converters(self):
        """Test escaped pattern converters."""
        to_escaped, from_escaped = XLSXConverters.comma_escaped_converters()

        # Test with embedded commas
        data = ["item1", "item2, with comma", "item3"]
        escaped = to_escaped(data)
        assert "item2\\, with comma" in escaped
        assert from_escaped(escaped) == data

    def test_dict_to_json_string(self):
        """Test dictionary to JSON string conversion."""
        assert (
            XLSXConverters.dict_to_json_string({"key": "value"}) == '{"key": "value"}'
        )
        assert XLSXConverters.dict_to_json_string({}) == "{}"
        assert XLSXConverters.dict_to_json_string(None) == ""

    def test_json_string_to_dict(self):
        """Test JSON string to dictionary conversion."""
        assert XLSXConverters.json_string_to_dict('{"key": "value"}') == {
            "key": "value"
        }
        assert XLSXConverters.json_string_to_dict("{}") == {}
        assert XLSXConverters.json_string_to_dict("") == {}
        assert XLSXConverters.json_string_to_dict("   ") == {}

    def test_json_string_to_dict_error(self):
        """Test error handling in JSON string to dictionary conversion."""
        with pytest.raises(ValueError, match=r"Cannot parse.*as JSON"):
            XLSXConverters.json_string_to_dict("invalid json")


# Tests for XLSXFieldAnalyzer
class TestXLSXFieldAnalyzer:
    """Tests for XLSXFieldAnalyzer functionality."""

    def test_analyze_simple_model(self):
        """Test field analysis for simple model."""
        fields = XLSXFieldAnalyzer.analyze_model(SimpleModel)
        assert len(fields) == 3

        name_field = next(f for f in fields.values() if f.name == "name")
        assert name_field.field_type is str
        assert not name_field.is_optional
        assert name_field.enum_values == []

    def test_analyze_optional_fields(self):
        """Test field analysis for optional fields."""

        class ModelWithOptional(BaseModel):
            required_field: str
            optional_field: str | None = None

        fields = XLSXFieldAnalyzer.analyze_model(ModelWithOptional)

        required_field = next(f for f in fields.values() if f.name == "required_field")
        assert not required_field.is_optional

        optional_field = next(f for f in fields.values() if f.name == "optional_field")
        assert optional_field.is_optional
        # The actual field_type for optional fields varies by Python version
        field_type_str = str(optional_field.field_type)
        assert (
            field_type_str.startswith("typing.Optional")
            or field_type_str.startswith("typing.Union")
            or "| None" in field_type_str
        )

    def test_analyze_enum_fields(self):
        """Test field analysis for enum fields."""

        class ModelWithEnum(BaseModel):
            status: Status
            priority: Priority | None = None

        fields = XLSXFieldAnalyzer.analyze_model(ModelWithEnum)

        status_field = next(f for f in fields.values() if f.name == "status")
        assert status_field.field_type == Status  # Field type is the actual enum type
        assert status_field.enum_values == ["active", "inactive", "pending"]

        priority_field = next(f for f in fields.values() if f.name == "priority")
        assert priority_field.is_optional
        # The actual field_type for optional enums varies by Python version
        field_type_str = str(priority_field.field_type)
        assert (
            field_type_str.startswith("typing.Optional")
            or field_type_str.startswith("typing.Union")
            or "| None" in field_type_str
        )
        assert priority_field.enum_values == ["low", "medium", "high"]

    def test_analyze_fields_with_converters(self):
        """Test field analysis with pattern converters."""

        class ModelWithConverters(BaseModel):
            tags: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.COMMA)
            ] = Field(default=[])

        fields = XLSXFieldAnalyzer.analyze_model(ModelWithConverters)

        tags_field = next(f for f in fields.values() if f.name == "tags")
        assert tags_field.xlsx_metadata is not None
        # The serializer/deserializer are None because they're not automatically created
        # The separator_pattern is stored but converters are created when needed
        assert tags_field.xlsx_metadata.separator_pattern == XLSXConverters.COMMA

    def test_analyze_fields_with_unit_and_meaning(self):
        """Test field analysis with unit and meaning."""
        fields = XLSXFieldAnalyzer.analyze_model(DemoModelWithMetadata)

        temp_field = next(f for f in fields.values() if f.name == "temp")
        assert temp_field.xlsx_metadata is not None
        assert temp_field.xlsx_metadata.unit == "°C"
        assert temp_field.xlsx_metadata.meaning == "Temperature measurement"

    def test_validate_unit_usage_valid(self):
        """Test valid unit usage validation."""
        # Should not raise for numeric types
        _validate_unit_usage("weight", float, "kg")
        _validate_unit_usage("count", int, "units")
        _validate_unit_usage("complex_num", complex, "units")

    def test_validate_unit_usage_optional_numeric(self):
        """Test unit validation with optional numeric types."""
        # Should not raise for Optional numeric types
        _validate_unit_usage("weight", Optional[float], "kg")
        _validate_unit_usage("count", Optional[int], "units")

    def test_validate_unit_usage_invalid(self):
        """Test invalid unit usage validation."""
        with pytest.raises(ValueError, match="Units are only valid for numeric fields"):
            _validate_unit_usage("name", str, "kg")

        with pytest.raises(ValueError, match="Units are only valid for numeric fields"):
            _validate_unit_usage("active", bool, "units")

    def test_validate_unit_usage_optional_non_numeric(self):
        """Test unit validation with optional non-numeric types."""
        with pytest.raises(ValueError, match="Units are only valid for numeric fields"):
            _validate_unit_usage("name", Optional[str], "kg")

    def test_is_optional_type(self):
        """Test optional type detection."""
        assert XLSXFieldAnalyzer.is_optional_type(Optional[str]) is True
        assert XLSXFieldAnalyzer.is_optional_type(Union[str, None]) is True
        assert XLSXFieldAnalyzer.is_optional_type(str | None) is True
        assert XLSXFieldAnalyzer.is_optional_type(str) is False
        assert XLSXFieldAnalyzer.is_optional_type(Union[str, int]) is False


# Tests for FieldAnalysis
class TestFieldAnalysis:
    """Tests for FieldAnalysis dataclass."""

    def test_field_analysis_creation(self):
        """Test FieldAnalysis creation with all parameters."""
        metadata = XLSXMetadata(
            unit="kg",
            meaning="http://example.org/test",
            display_name="Test Field",
            description="A test field",
        )
        field_analysis = FieldAnalysis(
            name="test_field",
            field_type=str,
            is_optional=True,
            enum_values=["a", "b", "c"],
            xlsx_metadata=metadata,
        )

        assert field_analysis.name == "test_field"
        assert field_analysis.field_type is str
        assert field_analysis.is_optional is True
        assert field_analysis.enum_values == ["a", "b", "c"]
        assert field_analysis.xlsx_metadata == metadata
        assert field_analysis.xlsx_metadata.unit == "kg"
        assert field_analysis.xlsx_metadata.meaning == "http://example.org/test"

    def test_field_analysis_defaults(self):
        """Test FieldAnalysis with default values."""
        field_analysis = FieldAnalysis(name="test", field_type=int)

        assert field_analysis.name == "test"
        assert field_analysis.field_type is int
        assert field_analysis.is_optional is False
        assert field_analysis.enum_values == []
        assert field_analysis.xlsx_metadata is None


# Tests for XLSXSerializationEngine
class TestXLSXSerializationEngine:
    """Tests for XLSXSerializationEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = XLSXSerializationEngine()

    def test_serialize_value_none(self):
        """Test serialization of None values."""
        field_analysis = FieldAnalysis(name="test", field_type=str)
        result = self.engine.serialize_value(None, field_analysis)
        assert result == ""

    def test_serialize_value_basic_types(self):
        """Test serialization of basic types."""
        field_analysis = FieldAnalysis(name="test", field_type=str)

        # Test basic types
        assert self.engine.serialize_value("hello", field_analysis) == "hello"
        assert self.engine.serialize_value(42, field_analysis) == 42
        assert self.engine.serialize_value(3.14, field_analysis) == 3.14
        assert self.engine.serialize_value(True, field_analysis) is True

        # Test date
        test_date = date(2024, 1, 1)
        assert self.engine.serialize_value(test_date, field_analysis) == test_date

    def test_serialize_value_enum(self):
        """Test serialization of enum values."""
        field_analysis = FieldAnalysis(name="status", field_type=str)
        result = self.engine.serialize_value(Status.ACTIVE, field_analysis)
        assert result == "active"

    def test_serialize_value_with_custom_serializer(self):
        """Test serialization with custom serializer."""
        serializer = lambda x: f"custom_{x}"
        metadata = XLSXMetadata(xlsx_serializer=serializer)
        field_analysis = FieldAnalysis(
            name="test", field_type=str, xlsx_metadata=metadata
        )
        result = self.engine.serialize_value("hello", field_analysis)
        assert result == "custom_hello"

    def test_serialize_value_complex_types(self):
        """Test serialization of complex types."""
        field_analysis = FieldAnalysis(name="test", field_type=str)

        # Test list
        result = self.engine.serialize_value(["a", "b", "c"], field_analysis)
        assert result == '["a", "b", "c"]'

        # Test dict
        result = self.engine.serialize_value({"key": "value"}, field_analysis)
        assert result == '{"key": "value"}'

    def test_deserialize_value_none_empty(self):
        """Test deserialization of None/empty values."""
        field_analysis = FieldAnalysis(name="test", field_type=str)

        assert self.engine.deserialize_value(None, field_analysis, SimpleModel) is None
        assert self.engine.deserialize_value("", field_analysis, SimpleModel) is None

    def test_deserialize_value_with_custom_deserializer(self):
        """Test deserialization with custom deserializer."""
        deserializer = lambda x: int(x) * 2
        metadata = XLSXMetadata(xlsx_deserializer=deserializer)
        field_analysis = FieldAnalysis(
            name="test", field_type=int, xlsx_metadata=metadata
        )
        result = self.engine.deserialize_value("5", field_analysis, SimpleModel)
        assert result == 10

    def test_deserialize_value_enum(self):
        """Test deserialization of enum values."""
        field_analysis = FieldAnalysis(
            name="status", field_type=str, enum_values=["active", "inactive", "pending"]
        )

        class TestModel(BaseModel):
            status: Status

        result = self.engine.deserialize_value("active", field_analysis, TestModel)
        assert result == Status.ACTIVE

    def test_deserialize_value_enum_invalid(self):
        """Test deserialization of invalid enum values."""
        field_analysis = FieldAnalysis(
            name="status", field_type=str, enum_values=["active", "inactive", "pending"]
        )

        class TestModel(BaseModel):
            status: Status

        with pytest.raises(ValueError, match="Invalid enum value"):
            self.engine.deserialize_value("invalid", field_analysis, TestModel)

    def test_convert_basic_types(self):
        """Test basic type conversion."""
        # String
        assert self.engine._convert_basic_types("hello", str) == "hello"

        # Integer
        assert self.engine._convert_basic_types("42", int) == 42
        assert self.engine._convert_basic_types(42, int) == 42

        # Float
        assert self.engine._convert_basic_types("3.14", float) == 3.14
        assert self.engine._convert_basic_types(3.14, float) == 3.14

        # Boolean
        assert self.engine._convert_basic_types("true", bool) is True
        assert self.engine._convert_basic_types("false", bool) is False
        assert self.engine._convert_basic_types("1", bool) is True
        assert self.engine._convert_basic_types("0", bool) is False

    def test_convert_bool(self):
        """Test boolean conversion."""
        assert self.engine._convert_bool(True) is True
        assert self.engine._convert_bool(False) is False
        assert self.engine._convert_bool("true") is True
        assert self.engine._convert_bool("True") is True
        assert self.engine._convert_bool("1") is True
        assert self.engine._convert_bool("yes") is True
        assert self.engine._convert_bool("on") is True
        assert self.engine._convert_bool("false") is False
        assert self.engine._convert_bool("0") is False
        assert self.engine._convert_bool("no") is False

    def test_convert_datetime(self):
        """Test date/datetime conversion."""
        # Date conversion
        date_str = "2024-01-01"
        result = self.engine._convert_datetime(date_str, date)
        assert result == date(2024, 1, 1)
        assert isinstance(result, date)

        # Datetime conversion
        datetime_str = "2024-01-01T12:00:00"
        result = self.engine._convert_datetime(datetime_str, datetime)
        assert isinstance(result, datetime)

    def test_convert_json_types(self):
        """Test JSON type conversion."""
        # When field_type is None, it returns string
        result = self.engine._convert_basic_types('["a", "b", "c"]', None)
        assert result == '["a", "b", "c"]'

        # Test that JSON parsing works when string contains valid JSON
        # The method checks if raw_value is string and tries to parse it
        result = self.engine._convert_basic_types('{"key": "value"}', str)
        # Since field_type is str, it uses the string converter which just returns str(x)
        assert result == '{"key": "value"}'

        # Test unsupported type defaults to string
        result = self.engine._convert_basic_types("test", object)
        assert result == "test"


# Tests for Custom Exceptions
class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_xlsx_serialization_error(self):
        """Test XLSXSerializationError exception."""
        original_error = ValueError("Test error")
        error = XLSXSerializationError("test_field", "test_value", original_error)

        assert error.field_name == "test_field"
        assert error.value == "test_value"
        assert error.original_error == original_error
        assert "Error serializing field 'test_field' with value 'test_value'" in str(
            error
        )

    def test_xlsx_deserialization_error(self):
        """Test XLSXDeserializationError exception."""
        original_error = ValueError("Test error")
        error = XLSXDeserializationError("test_field", "test_value", original_error)

        assert error.field_name == "test_field"
        assert error.value == "test_value"
        assert error.original_error == original_error
        assert "Error deserializing field 'test_field' with value 'test_value'" in str(
            error
        )


# Tests for Configuration
class TestConfiguration:
    """Tests for configuration system."""

    def test_base_config_inheritance(self):
        """Test configuration inheritance."""
        config = XLSXConfig(
            title="Test",
            include_fields={"field1", "field2"},
            exclude_fields={"field3"},
        )

        assert config.title == "Test"
        assert config.should_include_field("field1") is True
        assert config.should_include_field("field2") is True
        assert config.should_include_field("field3") is False
        assert config.should_include_field("field4") is False  # not in include list

    def test_config_field_filtering(self):
        """Test field filtering logic."""
        config = XLSXConfig(
            include_fields={"field1", "field2"},
            exclude_fields={"field3"},
        )

        assert config.should_include_field("field1") is True
        assert config.should_include_field("field2") is True
        assert config.should_include_field("field3") is False
        assert config.should_include_field("field4") is False  # not in include list

    def test_config_field_filtering_edge_cases(self):
        """Test edge cases in field filtering."""
        # Test with both include and exclude (include takes precedence)
        config = XLSXConfig(
            include_fields={"field1", "field2", "field3"}, exclude_fields={"field2"}
        )

        assert config.should_include_field("field1") is True
        assert config.should_include_field("field2") is True  # Include takes precedence
        assert config.should_include_field("field3") is True
        assert config.should_include_field("field4") is False  # Not in include

        # Test with no restrictions
        config_open = XLSXConfig()
        assert config_open.should_include_field("any_field") is True


# Tests for Advanced Field Analysis and Edge Cases
class TestAdvancedFieldAnalysis:
    """Tests for advanced field analysis scenarios."""

    def test_analyze_model_with_all_features(self):
        """Test analysis of model with all supported features."""

        class ComplexModel(BaseModel):
            # Basic types
            name: str
            age: int
            weight: Annotated[
                float, XLSXMetadata(unit="kg", meaning="http://example.org/weight")
            ]
            active: bool = True

            # Optional types
            email: str | None = None
            birth_date: date | None = None

            # Enum types
            status: Status
            priority: Priority | None = None

            # Complex types with converters
            tags: Annotated[
                list[str], XLSXMetadata(separator_pattern=XLSXConverters.COMMA)
            ] = Field(default=[])

        fields = XLSXFieldAnalyzer.analyze_model(ComplexModel)
        assert len(fields) == 9

        # Check specific fields
        weight_field = next(f for f in fields.values() if f.name == "weight")
        assert weight_field.xlsx_metadata is not None
        assert weight_field.xlsx_metadata.unit == "kg"
        assert weight_field.xlsx_metadata.meaning == "http://example.org/weight"

        tags_field = next(f for f in fields.values() if f.name == "tags")
        assert tags_field.xlsx_metadata is not None
        assert tags_field.xlsx_metadata.separator_pattern == XLSXConverters.COMMA

    def test_field_analysis_edge_cases(self):
        """Test FieldAnalysis edge cases."""
        # Test with None field type
        field_analysis = FieldAnalysis(name="test", field_type=None)
        assert field_analysis.field_type is None
        assert not field_analysis.is_optional

    def test_unit_validation_complex_union_types(self):
        """Test unit validation with complex Union types."""
        # Union with no numeric types should raise error
        with pytest.raises(ValueError, match="Units are only valid for numeric fields"):
            _validate_unit_usage("field", Union[str, bool], "kg")

        # Union with more than 2 types (non-Optional) should raise error
        with pytest.raises(ValueError, match="Units are only valid for numeric fields"):
            _validate_unit_usage("field", Union[str, int], "kg")


# Tests for ORCID and ROR Field Types in XLSX
class TestORCIDRORXLSXIntegration:
    """Tests for ORCID and ROR field types in XLSX import/export."""

    def test_orcid_ror_field_analysis(self):
        """Test field analysis for ORCID and ROR field types."""

        fields = XLSXFieldAnalyzer.analyze_model(ResearcherModel)
        assert len(fields) == 3

        # Check ORCID field - ORCIDIdentifier resolves to HttpUrl during field analysis
        orcid_field = next(f for f in fields.values() if f.name == "orcid")
        assert orcid_field.field_type == HttpUrl
        assert not orcid_field.is_optional

        # Check ROR field - RORIdentifier also resolves to HttpUrl during field analysis
        ror_field = next(f for f in fields.values() if f.name == "home_organization")
        assert ror_field.is_optional
        # The actual field_type for optional fields varies by Python version
        field_type_str = str(ror_field.field_type)
        assert (
            field_type_str.startswith(("typing.Optional", "typing.Union"))
            or "| None" in field_type_str
        )

    def test_orcid_ror_xlsx_round_trip_keyvalue(self, temp_file, sample_researcher):
        """Test ORCID and ROR fields in key-value XLSX format round-trip."""

        # Export to XLSX
        export_to_xlsx(sample_researcher, temp_file, format_type="keyvalue")

        # Import from XLSX
        imported = import_from_xlsx(temp_file, ResearcherModel, format_type="keyvalue")

        # Verify data integrity
        assert imported.name == sample_researcher.name
        assert str(imported.orcid) == str(sample_researcher.orcid)
        assert str(imported.home_organization) == str(
            sample_researcher.home_organization
        )

        # Verify types are preserved
        assert isinstance(imported.orcid, type(sample_researcher.orcid))
        assert isinstance(
            imported.home_organization, type(sample_researcher.home_organization)
        )

    def test_orcid_ror_xlsx_round_trip_table(self, temp_file, sample_researchers):
        """Test ORCID and ROR fields in table XLSX format round-trip."""

        # Export to XLSX
        export_to_xlsx(sample_researchers, temp_file, format_type="table")

        # Import from XLSX
        imported = import_from_xlsx(temp_file, ResearcherModel, format_type="table")

        # Verify data integrity
        assert len(imported) == len(sample_researchers)

        # First researcher
        assert imported[0].name == sample_researchers[0].name
        assert str(imported[0].orcid) == str(sample_researchers[0].orcid)
        assert str(imported[0].home_organization) == str(
            sample_researchers[0].home_organization
        )

        # Second researcher
        assert imported[1].name == sample_researchers[1].name
        assert str(imported[1].orcid) == str(sample_researchers[1].orcid)
        assert imported[1].home_organization is None

    def test_orcid_ror_serialization_engine(self):
        """Test ORCID and ROR field serialization/deserialization."""

        class ResearcherModel(BaseModel):
            orcid: ORCIDIdentifier
            ror: RORIdentifier

        engine = XLSXSerializationEngine()

        # Test ORCID serialization
        orcid_field = FieldAnalysis(name="orcid", field_type=ORCIDIdentifier)

        orcid_value = HttpUrl("https://orcid.org/0000-0002-1825-0097")

        serialized_orcid = engine.serialize_value(orcid_value, orcid_field)
        assert serialized_orcid == "https://orcid.org/0000-0002-1825-0097"

        # Test ORCID deserialization
        deserialized_orcid = engine.deserialize_value(
            "https://orcid.org/0000-0002-1825-0097", orcid_field, ResearcherModel
        )
        assert str(deserialized_orcid) == "https://orcid.org/0000-0002-1825-0097"

        # Test ROR serialization
        ror_field = FieldAnalysis(name="ror", field_type=RORIdentifier)
        ror_value = HttpUrl("https://ror.org/02y72wh86")

        serialized_ror = engine.serialize_value(ror_value, ror_field)
        assert serialized_ror == "https://ror.org/02y72wh86"

        # Test ROR deserialization
        deserialized_ror = engine.deserialize_value(
            "https://ror.org/02y72wh86", ror_field, ResearcherModel
        )
        assert str(deserialized_ror) == "https://ror.org/02y72wh86"

    def test_orcid_ror_validation_errors_on_import(self, temp_file, sample_researcher):
        """Test that invalid ORCID/ROR values raise validation errors during import."""

        export_to_xlsx(sample_researcher, temp_file, format_type="keyvalue")

        # Now manually corrupt the Excel file by reading and modifying
        workbook = load_workbook(temp_file)
        worksheet = workbook.active

        # Find the ORCID value and corrupt it
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value == str(sample_researcher.orcid):
                    cell.value = "invalid-orcid-format"
                    break

        workbook.save(temp_file)

        # Try to import corrupted data
        with pytest.raises(ValueError, match="validation error"):
            import_from_xlsx(temp_file, ResearcherModel, format_type="keyvalue")


class TestRequirednessHelpers:
    """Tests for requiredness detection and formatting."""

    def test_get_requiredness_info_required_field(self):
        """Test detection of required field (no default, not optional)."""

        class ModelWithRequired(BaseModel):
            required_field: str

        field_info = ModelWithRequired.model_fields["required_field"]
        field_analysis = XLSXFieldAnalyzer.analyze_field(
            "required_field", field_info, ModelWithRequired
        )

        is_required, default_value = XLSXFieldAnalyzer.get_requiredness_info(
            field_info, field_analysis
        )

        assert is_required is True

    def test_get_requiredness_info_optional_field(self):
        """Test detection of optional field (Union with None)."""

        class ModelWithOptional(BaseModel):
            optional_field: str | None = None

        field_info = ModelWithOptional.model_fields["optional_field"]
        field_analysis = XLSXFieldAnalyzer.analyze_field(
            "optional_field", field_info, ModelWithOptional
        )

        is_required, default_value = XLSXFieldAnalyzer.get_requiredness_info(
            field_info, field_analysis
        )

        assert is_required is False
        assert default_value is None

    def test_get_requiredness_info_field_with_default(self):
        """Test detection of field with non-optional type but has default."""

        class ModelWithDefault(BaseModel):
            field_with_default: str = "default_value"

        field_info = ModelWithDefault.model_fields["field_with_default"]
        field_analysis = XLSXFieldAnalyzer.analyze_field(
            "field_with_default", field_info, ModelWithDefault
        )

        is_required, default_value = XLSXFieldAnalyzer.get_requiredness_info(
            field_info, field_analysis
        )

        assert is_required is False
        assert default_value == "default_value"

    def test_format_requiredness_text_required(self):
        """Test formatting of required field."""
        from pydantic_core import PydanticUndefined

        result = XLSXFieldAnalyzer.format_requiredness_text(True, PydanticUndefined)
        assert result == "Yes"

    def test_format_requiredness_text_optional_no_default(self):
        """Test formatting of optional field with no/trivial default."""
        result = XLSXFieldAnalyzer.format_requiredness_text(False, None)
        assert result == "No"

        result = XLSXFieldAnalyzer.format_requiredness_text(False, "")
        assert result == "No"

        result = XLSXFieldAnalyzer.format_requiredness_text(False, 0)
        assert result == "No"

        result = XLSXFieldAnalyzer.format_requiredness_text(False, [])
        assert result == "No"

    def test_format_requiredness_text_with_default(self):
        """Test formatting of field with non-trivial default."""
        result = XLSXFieldAnalyzer.format_requiredness_text(False, "custom_default")
        assert result == "No (default: custom_default)"

        result = XLSXFieldAnalyzer.format_requiredness_text(False, 42)
        assert result == "No (default: 42)"

    def test_format_requiredness_text_enum_default(self):
        """Test formatting of field with enum default."""
        result = XLSXFieldAnalyzer.format_requiredness_text(False, Status.ACTIVE)
        assert result == "No (default: active)"


class TestMetadataVisibilityToggle:
    """Tests for metadata visibility toggle configuration."""

    def test_metadata_visibility_enum_values(self):
        """Test MetadataVisibility enum has expected values."""
        from voc4cat.xlsx_common import MetadataVisibility

        assert MetadataVisibility.AUTO.value == "auto"
        assert MetadataVisibility.SHOW.value == "show"
        assert MetadataVisibility.HIDE.value == "hide"

    def test_metadata_toggle_config_defaults(self):
        """Test MetadataToggleConfig has correct defaults."""
        from voc4cat.xlsx_common import MetadataToggleConfig, MetadataVisibility

        config = MetadataToggleConfig()
        assert config.unit == MetadataVisibility.AUTO
        assert config.requiredness == MetadataVisibility.AUTO
        assert config.description == MetadataVisibility.AUTO
        assert config.meaning == MetadataVisibility.AUTO

    def test_xlsx_config_with_metadata_visibility(self):
        """Test XLSXConfig accepts metadata_visibility parameter."""
        from voc4cat.xlsx_common import MetadataToggleConfig, MetadataVisibility

        toggle_config = MetadataToggleConfig(
            unit=MetadataVisibility.HIDE, requiredness=MetadataVisibility.SHOW
        )

        config = XLSXConfig(metadata_visibility=toggle_config)

        assert config.metadata_visibility is not None
        assert config.metadata_visibility.unit == MetadataVisibility.HIDE
        assert config.metadata_visibility.requiredness == MetadataVisibility.SHOW


if __name__ == "__main__":
    pytest.main([__file__])
