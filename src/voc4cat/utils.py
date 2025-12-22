import glob
import logging
import os
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.table import Table

from voc4cat.checks import Voc4catError
from voc4cat.models_v1 import (
    COLLECTIONS_SHEET_NAME,
    CONCEPT_SCHEME_SHEET_NAME,
    CONCEPTS_SHEET_NAME,
    ID_RANGES_SHEET_NAME,
    MAPPINGS_SHEET_NAME,
    PREFIXES_SHEET_NAME,
    RESERVED_SHEET_NAMES,
)

logger = logging.getLogger(__name__)

EXCEL_FILE_ENDINGS = [".xlsx"]
RDF_FILE_ENDINGS = {
    ".ttl": "ttl",
    ".rdf": "xml",
    ".xml": "xml",
    ".json-ld": "json-ld",
    ".json": "json-ld",
    ".nt": "nt",
    ".n3": "n3",
}
KNOWN_FILE_ENDINGS = [str(x) for x in RDF_FILE_ENDINGS] + EXCEL_FILE_ENDINGS


class ConversionError(Exception):
    pass


class RowsPreAllocatedTypeError(TypeError):
    def __init__(self):
        super().__init__("rows_pre_allocated must be an int or a dict")


def split_and_tidy(cell_value: str):
    # note this may not work in list of things that contain commas. Need to consider revising
    # to allow comma-separated values where it'll split in commas but not in things enclosed in quotes.
    if cell_value == "" or cell_value is None:
        return []
    entries = [x.strip() for x in cell_value.strip().split(",")]
    return [x for x in entries if x]


def has_file_in_multiple_formats(dir_):
    files = [
        os.path.normcase(f)
        for f in glob.glob(os.path.join(dir_, "*.*"))
        if f.endswith(tuple(KNOWN_FILE_ENDINGS))
    ]
    file_names = [os.path.splitext(f)[0] for f in files]
    unique_file_names = set(file_names)
    if len(file_names) == len(unique_file_names):
        return False
    seen = set()
    return [x for x in file_names if x in seen or seen.add(x)]


def adjust_length_of_tables(
    wb_path: Path, rows_pre_allocated: dict[str, int] | int = 0, copy_style: bool = True
) -> None:
    """Expand length of all tables in workbook to include all filled rows

    For all tables in the workbook the table is expanded to include the last
    row with from a block of content plus a number of <rows_pre_allocated>
    additional rows. The number can be set for each sheet individually by
    using a dictionary with sheet names as keys and the number of rows as
    values. If a sheet is not in the dictionary, the default value is used.

    Note that tables are not shrunk by this method if they contain empty
    rows at the end.

    If copy_style is True, the style of the first row in the table is copied
    to all following rows.
    """
    if isinstance(rows_pre_allocated, int):
        rows_pre_allocated = dict.fromkeys(
            load_workbook(wb_path).sheetnames, rows_pre_allocated
        )
    elif isinstance(rows_pre_allocated, dict):
        for sheet_name in load_workbook(wb_path).sheetnames:
            if sheet_name not in rows_pre_allocated:
                rows_pre_allocated[sheet_name] = (
                    0  # set default value for missing sheets
                )
    else:
        raise RowsPreAllocatedTypeError()

    wb = load_workbook(wb_path)

    for ws in wb.sheetnames:
        for t_name in list(wb[ws].tables):
            old_range = wb[ws].tables[t_name].ref  # "A2:I20"
            start_col, start_row, end_col, end_row = range_boundaries(old_range)
            start = old_range.split(":")[0]

            # find last row with content in table
            for row in range(1, end_row + 1):
                row_has_content = any(
                    wb[ws].cell(row=row, column=col).value
                    for col in range(start_col, end_col + 1)
                )
                if not row_has_content:
                    break

            new_last_row = max(row - 1 + rows_pre_allocated[ws], wb[ws].max_row)
            adjusted = f"{start}:{get_column_letter(end_col)}{new_last_row}"

            if adjusted != old_range:
                # Expanding the table is not possible with openpyxl. Instead a too
                # short table is removed, and a new adjusted table is created.
                style = copy(wb[ws].tables[t_name].tableStyleInfo)
                del wb[ws].tables[t_name]
                newtab = Table(displayName=t_name, ref=adjusted)
                newtab.tableStyleInfo = style
                wb[ws].add_table(newtab)
                logger.debug(
                    'Adjusted table "%s" in sheet "%s" from {%s} to {%s}.',
                    t_name,
                    wb[ws].title,
                    old_range,
                    adjusted,
                )
            # Skip copy_style for key-value tables (they have heterogeneous rows)
            if copy_style and not t_name.startswith("KeyValue_"):
                # Read styles from first row
                styles_in_row = []
                for col in range(start_col, end_col + 1):
                    cell = wb[ws].cell(row=start_row + 1, column=col)
                    cell_styles = {}
                    for attr in ["alignment", "border", "font", "fill"]:
                        cell_styles[attr] = copy(getattr(cell, attr))
                    styles_in_row.append(cell_styles)

                # Apply styles to all following rows
                for row in range(start_row + 2, new_last_row + 1):
                    for col, cell_styles in enumerate(styles_in_row):
                        cell = wb[ws].cell(row=row, column=start_col + col)
                        for style, styles_obj in cell_styles.items():
                            # Store indentation for sheet "Concepts", pref.label column
                            keep_indent = (
                                col == 1 and ws == "Concepts" and style == "alignment"
                            )
                            if keep_indent and cell.alignment.indent:
                                indent = cell.alignment.indent
                                cell_alignment = copy(styles_obj)
                                cell_alignment.indent = indent
                                setattr(cell, style, cell_alignment)
                            else:
                                # set style
                                setattr(cell, style, styles_obj)

            # reset row height for all table rows including header to default
            for row in range(start_row, new_last_row + 1):
                wb[ws].row_dimensions[row].height = None

    wb.save(wb_path)
    wb.close()


# =============================================================================
# Shared Template Utilities
# =============================================================================


def validate_template_sheets(template_path: Path) -> None:
    """Validate that template doesn't contain reserved sheet names.

    Args:
        template_path: Path to the template xlsx file.

    Raises:
        Voc4catError: If template contains any reserved sheet names.
    """
    wb = load_workbook(template_path, read_only=True)
    template_sheets = set(wb.sheetnames)
    wb.close()

    conflicting = template_sheets & RESERVED_SHEET_NAMES
    if conflicting:
        msg = (
            f"Template contains reserved sheet names that will be auto-created: "
            f'"{", ".join(sorted(conflicting))}". '
            f"Please remove or rename these sheets in the template."
        )
        logger.error(msg)
        raise Voc4catError(msg)


def get_template_sheet_names(template_path: Path) -> list[str]:
    """Get the list of sheet names from a template file.

    Args:
        template_path: Path to the template xlsx file.

    Returns:
        List of sheet names in the template, in their original order.
    """
    wb = load_workbook(template_path, read_only=True)
    sheet_names = list(wb.sheetnames)
    wb.close()
    return sheet_names


def reorder_sheets_with_template(
    wb, template_sheet_names: list[str] | None = None
) -> None:
    """Reorder sheets: template sheets first (if any), then auto-created sheets.

    Args:
        wb: Workbook to reorder.
        template_sheet_names: List of sheet names from template (in order).
                             If provided, these sheets are placed first,
                             followed by auto-created sheets.
    """
    auto_created_order = [
        CONCEPT_SCHEME_SHEET_NAME,
        CONCEPTS_SHEET_NAME,
        COLLECTIONS_SHEET_NAME,
        MAPPINGS_SHEET_NAME,
        ID_RANGES_SHEET_NAME,
        PREFIXES_SHEET_NAME,
    ]

    current_sheets = wb.sheetnames

    if template_sheet_names is not None:
        # Template sheets first (in original order), then auto-created
        new_order = []
        # First: template sheets in their original order
        for sheet_name in template_sheet_names:
            if sheet_name in current_sheets:
                new_order.append(sheet_name)
        # Second: auto-created sheets in expected order
        for sheet_name in auto_created_order:
            if sheet_name in current_sheets and sheet_name not in new_order:
                new_order.append(sheet_name)
        # Third: any remaining sheets (shouldn't happen, but defensive)
        for sheet_name in current_sheets:
            if sheet_name not in new_order:
                new_order.append(sheet_name)
    else:
        # No template: auto-created first, then others
        new_order = []
        for sheet_name in auto_created_order:
            if sheet_name in current_sheets:
                new_order.append(sheet_name)
        for sheet_name in current_sheets:
            if sheet_name not in new_order:
                new_order.append(sheet_name)

    for idx, sheet_name in enumerate(new_order):
        wb.move_sheet(sheet_name, offset=idx - wb.sheetnames.index(sheet_name))
