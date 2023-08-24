import glob
import logging
import os
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_from_string
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


def adjust_length_of_tables(wb_path):
    """Expand length of all tables in workbook to include all filled rows

    For all tables in the workbook the table is expanded to include the last
    row with content. Note that tables are not shrunk by this method if they
    contain empty rows at the end.
    """
    wb = load_workbook(wb_path)

    for ws in wb.sheetnames:
        for t_name in list(wb[ws].tables):
            old_range = wb[ws].tables[t_name].ref  # "A2:I20"
            start, end = old_range.split(":")
            end_col, _end_row = coordinate_from_string(end)
            adjusted = f"{start}:{end_col}{wb[ws].max_row}"
            if adjusted == old_range:
                continue
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

    wb.save(wb_path)
    wb.close()
