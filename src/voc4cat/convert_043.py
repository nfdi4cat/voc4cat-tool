from typing import List, Tuple

from curies import Converter
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import ValidationError

from voc4cat import models
from voc4cat.utils import ConversionError, split_and_tidy


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


def extract_concepts_and_collections(
    q: Worksheet, r: Worksheet, s: Worksheet, prefix_converter: Converter
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

            uri = q[f"A{row}"].value
            clean_uri = (prefix_converter.expand(uri) or uri) if uri else None
            home_vocab_uri = q[f"I{row}"].value
            clean_home_vocab_uri = (
                (prefix_converter.expand(home_vocab_uri) or home_vocab_uri)
                if home_vocab_uri
                else None
            )
            try:
                c = models.Concept(
                    uri=clean_uri,
                    pref_label=q[f"B{row}"].value,
                    pl_language_code=split_and_tidy(q[f"C{row}"].value),
                    definition=q[f"D{row}"].value,
                    def_language_code=split_and_tidy(q[f"E{row}"].value),
                    alt_labels=split_and_tidy(q[f"F{row}"].value),
                    children=q[f"G{row}"].value,
                    provenance=q[f"H{row}"].value,
                    # Note in the new template, home_vocab_uri is synonymous with source vocab uri
                    home_vocab_uri=clean_home_vocab_uri,
                    # additional concept features sheets
                    related_match=r[f"B{row}"].value,
                    close_match=r[f"C{row}"].value,
                    exact_match=r[f"D{row}"].value,
                    narrow_match=r[f"E{row}"].value,
                    broad_match=r[f"F{row}"].value,
                )
                concepts.append(c)
            except ValidationError as exc:
                msg = f"Concept processing error likely at sheet {q}, row {row}, and has error: {exc}"
                raise ConversionError(msg) from exc

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

            try:
                uri = s[f"A{row}"].value
                c = models.Collection(
                    uri=(prefix_converter.expand(uri) or uri) if uri else None,
                    pref_label=s[f"B{row}"].value,
                    definition=s[f"C{row}"].value,
                    members=s[f"D{row}"].value,
                    provenance=s[f"E{row}"].value,
                )
                collections.append(c)
            except ValidationError as exc:
                msg = f"Collection processing error, likely at sheet {s}, row {row}, and has error: {exc}"
                raise ConversionError(msg) from exc

    return concepts, collections


def extract_concept_scheme(sheet: Worksheet, prefix_converter: Converter):
    uri = sheet["B2"].value
    cs = models.ConceptScheme(
        uri=(prefix_converter.expand(uri) or uri) if uri else None,
        title=sheet["B3"].value,
        description=sheet["B4"].value,
        created=sheet["B5"].value,
        modified=sheet["B6"].value,
        creator=sheet["B7"].value,
        publisher=sheet["B8"].value,
        version=sheet["B9"].value,
        provenance=sheet["B10"].value,
        custodian=sheet["B11"].value,
        pid=sheet["B12"].value,
    )
    return cs  # noqa: RET504
