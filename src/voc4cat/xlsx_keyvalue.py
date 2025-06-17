"""
Key-value format implementation for single records with field/value pairs.

This module contains all key-value-specific functionality including:
- Key-value configuration with column customization
- Key-value formatter for field/value layout
- Key-value processor for import/export operations
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, ValidationError

from .xlsx_common import (
    MAX_SHEETNAME_LENGTH,
    FieldAnalysis,
    XLSXConfig,
    XLSXDeserializationError,
    XLSXFormatter,
    XLSXProcessor,
    XLSXSerializationError,
)


# Key-value specific configuration
@dataclass
class XLSXKeyValueConfig(XLSXConfig):
    """Configuration for key-value format (single record)."""

    field_column_header: str = "Field"
    value_column_header: str = "Value"
    unit_column_header: str = "Unit"
    description_column_header: str = "Description"
    meaning_column_header: str = "Meaning"
    field_column_width: int = 25
    value_column_width: int = 30
    unit_column_width: int = 10
    description_column_width: int = 50
    meaning_column_width: int = 40


# Key-value formatter
class XLSXKeyValueFormatter(XLSXFormatter):
    """Handles key-value format with field names and values."""

    def format_export(
        self, worksheet: Worksheet, data: BaseModel, fields: list[FieldAnalysis]
    ) -> None:
        """Format data as key-value pairs."""
        config = self.config
        if not isinstance(config, XLSXKeyValueConfig):
            msg = "XLSXKeyValueFormatter requires XLSXKeyValueConfig"
            raise TypeError(msg)

        # Add title at row 1 (if present)
        title = config.title
        if title == "Data Export":  # Default title
            title = f"{data.__class__.__name__} Instance"

        if title:
            self._add_kv_title(worksheet, title, config)

        # Add headers starting at row 3 (leaving row 2 empty)
        self._add_kv_headers(worksheet, config, fields)

        # Write field data
        self._write_field_data(worksheet, data, fields, config)

        # Create and add Excel table
        table = self._create_kv_table(worksheet, len(fields), config, fields)
        worksheet.add_table(table)

        # Add validation (always enabled)
        self._add_data_validation(worksheet, fields, config)

        # Auto-adjust columns - all columns always shown
        num_columns = 5  # Field + Value + Unit + Description + Meaning
        self._auto_adjust_columns(worksheet, num_columns)

    def _add_kv_title(
        self, worksheet: Worksheet, title: str, config: XLSXKeyValueConfig
    ) -> None:
        """Add title to worksheet at configured start row."""
        if title:
            title_row = self.row_calculator.get_title_row()
            cell = worksheet.cell(row=title_row, column=1)
            cell.value = title
            cell.font = Font(size=14, bold=True)
            cell.alignment = Alignment(horizontal="left")

    def _add_kv_headers(
        self,
        worksheet: Worksheet,
        config: XLSXKeyValueConfig,
        fields: list[FieldAnalysis],
    ) -> None:
        """Add field/value/description/meaning/unit headers with dynamic positioning."""
        header_row = self.row_calculator.get_first_content_row()
        worksheet[f"A{header_row}"] = config.field_column_header
        worksheet[f"B{header_row}"] = config.value_column_header

        # Build headers - all columns always shown
        # Order: Field | Value | Unit | Description | Meaning
        worksheet[f"C{header_row}"] = config.unit_column_header
        worksheet[f"D{header_row}"] = config.description_column_header
        worksheet[f"E{header_row}"] = config.meaning_column_header

    def _write_field_data(
        self,
        worksheet: Worksheet,
        data: BaseModel,
        fields: list[FieldAnalysis],
        config: XLSXKeyValueConfig,
    ) -> None:
        """Write field data in key-value format."""
        row = self.row_calculator.get_first_content_row() + 1

        for field_analysis in fields:
            value = getattr(data, field_analysis.name, None)

            # Write field name
            display_name = self._get_field_display_name(field_analysis)
            field_name_cell = worksheet[f"A{row}"]
            field_name_cell.value = display_name
            # Apply formatting to field name cell (treat as text field)
            text_field_analysis = FieldAnalysis(name="field_name", field_type=str)
            self._apply_data_cell_formatting(field_name_cell, text_field_analysis)

            # Write field value
            try:
                formatted_value = self.serialization_engine.serialize_value(
                    value, field_analysis
                )
                value_cell = worksheet[f"B{row}"]
                value_cell.value = formatted_value
                # Apply special formatting for Value column (always left-aligned)
                # Skip formatting if disabled in configuration
                if not (
                    hasattr(self.config, "enable_cell_formatting")
                    and not self.config.enable_cell_formatting
                ):
                    # Value column gets left alignment regardless of data type
                    wrap_text = self._should_wrap_text(field_analysis.field_type)

                    value_cell.alignment = Alignment(
                        horizontal="left",  # Always left-align Value column
                        vertical="center",
                        wrap_text=wrap_text,
                    )
            except Exception as e:
                raise XLSXSerializationError(field_analysis.name, value, e) from e

            # Write additional columns - all columns always shown
            # Order: Field | Value | Unit | Description | Meaning

            # Unit column (C)
            unit_value = (
                field_analysis.xlsx_metadata.unit
                if field_analysis.xlsx_metadata and field_analysis.xlsx_metadata.unit
                else ""
            )
            unit_cell = worksheet[f"C{row}"]
            unit_cell.value = unit_value
            # Apply formatting to unit cell (treat as text field)
            text_field_analysis = FieldAnalysis(name="unit", field_type=str)
            self._apply_data_cell_formatting(unit_cell, text_field_analysis)

            # Description column (D)
            description = (
                field_analysis.xlsx_metadata.description
                if field_analysis.xlsx_metadata
                and field_analysis.xlsx_metadata.description
                else ""
            )
            description_cell = worksheet[f"D{row}"]
            description_cell.value = description
            # Apply formatting to description cell (treat as text field)
            text_field_analysis = FieldAnalysis(name="description", field_type=str)
            self._apply_data_cell_formatting(description_cell, text_field_analysis)

            # Meaning column (E)
            meaning_value = (
                field_analysis.xlsx_metadata.meaning
                if field_analysis.xlsx_metadata and field_analysis.xlsx_metadata.meaning
                else ""
            )
            meaning_cell = worksheet[f"E{row}"]
            meaning_cell.value = meaning_value
            # Apply formatting to meaning cell (treat as text field)
            text_field_analysis = FieldAnalysis(name="meaning", field_type=str)
            self._apply_data_cell_formatting(meaning_cell, text_field_analysis)

            row += 1

    def _create_kv_table(
        self,
        worksheet: Worksheet,
        num_fields: int,
        config: XLSXKeyValueConfig,
        fields: list[FieldAnalysis],
    ) -> Table:
        """Create Excel table for key-value data."""
        # All columns always present
        num_columns = 5  # Field + Value + Unit + Description + Meaning

        # Calculate table range - headers start at dynamic position
        start_row = self.row_calculator.get_first_content_row()
        end_row = start_row + num_fields  # header row + data rows
        end_col_letter = get_column_letter(num_columns)

        table_range = f"A{start_row}:{end_col_letter}{end_row}"

        # Create table name (clean and unique)
        table_name = f"KeyValue_{worksheet.title.replace(' ', '_')}"
        table_name = re.sub(r"[^a-zA-Z0-9_]", "_", table_name)
        if len(table_name) > MAX_SHEETNAME_LENGTH:
            table_name = table_name[:MAX_SHEETNAME_LENGTH]

        # Create table object
        table = Table(displayName=table_name, ref=table_range)
        table.tableStyleInfo = TableStyleInfo(
            name=getattr(config, "table_style", "TableStyleMedium9"),
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        return table

    def _add_data_validation(
        self,
        worksheet: Worksheet,
        fields: list[FieldAnalysis],
        config: XLSXKeyValueConfig,
    ) -> None:
        """Add data validation for enum fields in key-value format."""
        # Calculate data start row - where the values column starts
        data_start_row = self.row_calculator.get_first_content_row() + 1

        # Go through each field and add validation if it's an enum
        for i, field_analysis in enumerate(fields):
            if field_analysis.enum_values:
                # Calculate the row for this specific field
                field_row = data_start_row + i

                # Value column is always column B
                validation_range = f"B{field_row}"

                dv = DataValidation(
                    type="list",
                    formula1=f'"{",".join(field_analysis.enum_values)}"',
                    allow_blank=field_analysis.is_optional,
                )
                dv.error = f"Invalid value. Must be one of: {', '.join(field_analysis.enum_values)}"
                dv.errorTitle = "Invalid Input"

                worksheet.add_data_validation(dv)
                dv.add(validation_range)

    def parse_import(
        self,
        worksheet: Worksheet,
        fields: list[FieldAnalysis],
        model_class: type[BaseModel],
    ) -> BaseModel:
        """Parse key-value data from worksheet."""
        config = self.config
        if not isinstance(config, XLSXKeyValueConfig):
            msg = "XLSXKeyValueFormatter requires XLSXKeyValueConfig"
            raise TypeError(msg)

        field_dict = {field.name: field for field in fields}
        field_data = self._read_field_data(worksheet, field_dict, model_class, config)

        try:
            return model_class(**field_data)
        except ValidationError as e:
            msg = f"Failed to create {model_class.__name__} instance: {e}"
            raise ValueError(msg) from e

    def _read_field_data(
        self,
        worksheet: Worksheet,
        field_dict: dict[str, FieldAnalysis],
        model_class: type[BaseModel],
        config: XLSXKeyValueConfig,
    ) -> dict[str, Any]:
        """Read field data from worksheet."""
        field_data = {}

        # Note: For reading data, we need to pass the fields but we don't have direct access here
        # The fields list needs to be passed through from the calling method
        fields_list = list(field_dict.values()) if field_dict else []
        start_row = self.row_calculator.get_first_content_row() + 1
        for row in range(start_row, worksheet.max_row + 1):
            field_name_cell = worksheet[f"A{row}"]
            value_cell = worksheet[f"B{row}"]

            # Read unit and meaning - all columns always present
            # Order: Field | Value | Unit | Description | Meaning

            # Read unit (column C)
            unit_cell = worksheet[f"C{row}"]
            worksheet_unit = unit_cell.value
            worksheet_unit = worksheet_unit.strip() if worksheet_unit else ""

            # Read meaning (column E)
            meaning_cell = worksheet[f"E{row}"]
            worksheet_meaning = meaning_cell.value
            worksheet_meaning = worksheet_meaning.strip() if worksheet_meaning else ""

            if not field_name_cell.value:
                continue

            # Convert display name back to field name
            display_name = str(field_name_cell.value)
            field_name = self._find_field_name_from_display(
                display_name, field_dict, config
            )

            if field_name and field_name in field_dict:
                field_analysis = field_dict[field_name]
                raw_value = value_cell.value

                # Validate unit consistency (if field has unit defined)
                expected_unit = (
                    field_analysis.xlsx_metadata.unit
                    if field_analysis.xlsx_metadata
                    else None
                )
                if expected_unit and worksheet_unit and worksheet_unit != expected_unit:
                    raise ValueError(
                        f"Unit mismatch for field '{field_name}': "
                        f"expected '{expected_unit}', found '{worksheet_unit}'"
                    )

                # Validate meaning consistency (if field has meaning defined)
                expected_meaning = (
                    field_analysis.xlsx_metadata.meaning
                    if field_analysis.xlsx_metadata
                    else None
                )
                if (
                    expected_meaning
                    and worksheet_meaning
                    and worksheet_meaning != expected_meaning
                ):
                    raise ValueError(
                        f"Meaning mismatch for field '{field_name}': "
                        f"expected '{expected_meaning}', found '{worksheet_meaning}'"
                    )

                try:
                    converted_value = self.serialization_engine.deserialize_value(
                        raw_value, field_analysis, model_class
                    )
                    field_data[field_name] = converted_value
                except Exception as e:
                    raise XLSXDeserializationError(field_name, raw_value, e) from e

        return field_data

    def _find_field_name_from_display(
        self,
        display_name: str,
        field_dict: dict[str, FieldAnalysis],
        config: XLSXKeyValueConfig,
    ) -> str | None:
        """Find the actual field name from the display name."""
        # Check against field display names (either custom or auto-generated)
        for field_name, field_analysis in field_dict.items():
            expected_display = self._get_field_display_name(field_analysis)
            if expected_display == display_name:
                return field_name

        return None


# Key-value processor
class XLSXKeyValueProcessor(XLSXProcessor):
    """Processor for key-value format."""

    def export(
        self, data: BaseModel, filepath: Path, sheet_name: str | None = None
    ) -> None:
        """Export single model to XLSX file."""
        model_class = data.__class__
        sheet_name = sheet_name or model_class.__name__

        # Analyze fields
        field_analyses = self.field_analyzer.analyze_model(model_class)
        fields = list(field_analyses.values())
        filtered_fields = self._filter_and_order_fields(fields)

        # Create or load workbook and worksheet
        if filepath.exists() and filepath.stat().st_size > 0:
            try:
                workbook = load_workbook(filepath)
            except Exception:
                # If file exists but is not a valid Excel file, create new workbook
                workbook = Workbook()
                if "Sheet" in workbook.sheetnames:
                    workbook.remove(workbook["Sheet"])
        else:
            workbook = Workbook()
            if "Sheet" in workbook.sheetnames:
                workbook.remove(workbook["Sheet"])

        # Remove existing sheet with same name if it exists
        if sheet_name in workbook.sheetnames:
            workbook.remove(workbook[sheet_name])

        worksheet = workbook.create_sheet(title=sheet_name)

        # Format export
        self.formatter.format_export(worksheet, data, filtered_fields)

        # Save workbook
        workbook.save(filepath)

    def import_data(
        self,
        filepath: Path,
        model_class: type[BaseModel],
        sheet_name: str | None = None,
    ) -> BaseModel:
        """Import single model from XLSX file."""
        sheet_name = sheet_name or model_class.__name__

        workbook = load_workbook(filepath, data_only=True)

        if sheet_name not in workbook.sheetnames:
            msg = f"Sheet '{sheet_name}' not found in workbook"
            raise ValueError(msg)

        worksheet = workbook[sheet_name]

        # Analyze fields
        field_analyses = self.field_analyzer.analyze_model(model_class)
        fields = list(field_analyses.values())
        filtered_fields = self._filter_and_order_fields(fields)

        # Parse import
        return self.formatter.parse_import(worksheet, filtered_fields, model_class)
