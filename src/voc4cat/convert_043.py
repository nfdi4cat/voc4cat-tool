import logging
from typing import List, Tuple

from curies import Converter
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import ValidationError

from voc4cat import models
from voc4cat.utils import ConversionError, split_and_tidy

logger = logging.getLogger(__name__)


def create_prefix_dict(s: Worksheet):
    # create an empty dict
    prefix_dict = {}

    # add prefix values according to the prefix sheet
    for col in s.iter_cols(max_col=1):
        for cell in col:
            row = cell.row
            if cell.value is None or cell.value in ["Prefix", "Prefix Sheet"]:
                continue

            # dynamically allocate the prefix sheet
            try:
                prefix_dict[s[f"A{row}"].value] = s[f"B{row}"].value
            except Exception as exc:
                msg = f"Prefix processing error, sheet {s}, row {row}, error: {exc}"
                raise ConversionError(msg) from exc
    return prefix_dict


def write_prefix_sheet(wb: Workbook, prefix_map):
    """
    Write prefix_dict to prefix sheet
    """
    ws = wb["Prefix Sheet"]

    # Clear the sheet except for the header.
    ws.delete_rows(2, ws.max_row - 1)

    for prefix, iri in prefix_map.items():
        ws.append([prefix, iri])


def extract_concepts_and_collections(
    q: Worksheet,
    r: Worksheet,
    s: Worksheet,
    prefix_converter: Converter,
    vocab_name: str = "",
) -> Tuple[List[models.Concept], List[models.Collection]]:
    concepts = []
    collections = []
    # Iterating over the concept page and the additional concept page
    for col in q.iter_cols(max_col=1):
        for cell in col:
            row = cell.row
            if cell.value is None or cell.value in [
                "Concepts",
                "Concepts*",
                "Concept IRI*",
            ]:
                continue

            concept_data = {
                "uri": q[f"A{row}"].value,
                "pref_label": q[f"B{row}"].value,
                "pl_language_code": split_and_tidy(q[f"C{row}"].value),
                "definition": q[f"D{row}"].value,
                "def_language_code": split_and_tidy(q[f"E{row}"].value),
                "alt_labels": split_and_tidy(q[f"F{row}"].value),
                "children": q[f"G{row}"].value,
                "provenance": q[f"H{row}"].value,
                # Note in the new template, source_vocab is synonymous with source vocab uri
                "source_vocab": q[f"I{row}"].value,
                # additional concept features sheets
                "related_match": r[f"B{row}"].value,
                "close_match": r[f"C{row}"].value,
                "exact_match": r[f"D{row}"].value,
                "narrow_match": r[f"E{row}"].value,
                "broad_match": r[f"F{row}"].value,
                "vocab_name": vocab_name,
            }
            try:
                c = models.Concept(**concept_data)
            except ValidationError as exc:
                msg = f"Concept processing error likely at sheet {q}, row {row}, and has error: {exc}"
                raise ConversionError(msg) from exc
            concepts.append(c)

    # iterating over the collections page
    for col in s.iter_cols(max_col=1):
        for cell in col:
            row = cell.row
            if cell.value is None or cell.value in [
                "Collections",
                "Collection URI",
                "Collection IRI",
            ]:
                continue

            data_collection = {
                "uri": s[f"A{row}"].value,
                "pref_label": s[f"B{row}"].value,
                "definition": s[f"C{row}"].value,
                "members": s[f"D{row}"].value,
                "provenance": s[f"E{row}"].value,
                "vocab_name": vocab_name,
            }

            try:
                c = models.Collection(**data_collection)
                collections.append(c)
            except ValidationError as exc:
                msg = f"Collection processing error, likely at sheet {s}, row {row}, and has error: {exc}"
                raise ConversionError(msg) from exc

    return concepts, collections


def extract_concept_scheme(
    sheet: Worksheet, prefix_converter: Converter, vocab_name: str = ""
):
    uri = sheet["B2"].value
    cs = models.ConceptScheme(
        uri=(prefix_converter.expand(uri) or uri) if uri else None,
        title=sheet["B3"].value,
        description=sheet["B4"].value,
        created=sheet["B5"].value,
        modified=(
            sheet["B6"].value if sheet["B6"].value is not None else sheet["B5"].value
        ),
        creator=sheet["B7"].value,
        publisher=sheet["B8"].value,
        version=sheet["B9"].value if sheet["B9"].value is not None else "",
        provenance=sheet["B10"].value,
        custodian=sheet["B11"].value,
        pid=sheet["B12"].value,
        vocab_name=vocab_name,
    )
    return cs  # noqa: RET504
