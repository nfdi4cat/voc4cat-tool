import glob
import logging
import os
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.table import Table

from voc4cat.checks import Voc4catError

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
KNOWN_TEMPLATE_VERSIONS = ["0.4.3"]
LATEST_TEMPLATE = KNOWN_TEMPLATE_VERSIONS[-1]


class ConversionError(Exception):
    pass


def load_template(file_path: Path) -> Workbook:
    if file_path.suffix.lower() not in EXCEL_FILE_ENDINGS:
        msg = "Template files for RDF-to-xlsx conversion must be xlsx files."
        raise Voc4catError(msg)
    if get_template_version(load_workbook(str(file_path))) != LATEST_TEMPLATE:
        msg = f"Template files for RDF-to-xlsx conversion must be of latest version ({LATEST_TEMPLATE})"
        raise Voc4catError(msg)
    return load_workbook(filename=str(file_path), data_only=True)


def get_template_version(wb: Workbook) -> str:
    # try 0.4.3 location
    try:
        intro_sheet = wb["Introduction"]
    except KeyError as exc:  # non-existing worksheet
        msg = "The version of the Excel template cannot be determined."
        logger.exception(msg)
        raise Voc4catError(msg) from exc
    return intro_sheet["J11"].value


def is_supported_template(wb):
    """Check if the template version is supported."""
    template_version = get_template_version(wb)
    if template_version not in KNOWN_TEMPLATE_VERSIONS:
        msg = f"Unsupported template version. Supported are {', '.join(KNOWN_TEMPLATE_VERSIONS)}, you supplied {template_version}."
        raise Voc4catError(msg)
    return True


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
        raise ValueError("rows_pre_allocated must be an int or a dict")

    wb = load_workbook(wb_path)

    for ws in wb.sheetnames:
        for t_name in list(wb[ws].tables):
            old_range = wb[ws].tables[t_name].ref  # "A2:I20"
            start, end = old_range.split(":")
            start_col_str, start_row = coordinate_from_string(start)
            start_col = column_index_from_string(start_col_str)
            end_col_str, end_row = coordinate_from_string(end)
            end_col = column_index_from_string(end_col_str)

            # find last row with content in table
            for row in range(1, end_row + 1):
                row_has_content = any(
                    wb[ws].cell(row=row, column=col).value
                    for col in range(start_col, end_col + 1)
                )
                if not row_has_content:
                    break

            new_last_row = max(row - 1 + rows_pre_allocated[ws], wb[ws].max_row)
            adjusted = f"{start}:{end_col_str}{new_last_row}"

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
            if copy_style:
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
