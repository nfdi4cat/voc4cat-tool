# -*- coding: utf-8 -*-
"""
A wrapper to extend VocExcel with more commands.

The new commands may be run either before or after VocExcel.

Copyright (c) 2022 David Linke (ORCID: 0000-0002-5898-1820)
"""
import argparse
import datetime
import glob
import os
import sys
from collections import defaultdict
from itertools import count
from pathlib import Path
from warnings import warn

import openpyxl
from django.utils.text import slugify
from openpyxl.styles import Alignment, PatternFill
from rdflib import URIRef
from vocexcel.convert import main as vocexcel_main
from vocexcel.models import ORGANISATIONS, ORGANISATIONS_INVERSE
from vocexcel.utils import EXCEL_FILE_ENDINGS, KNOWN_FILE_ENDINGS, RDF_FILE_ENDINGS

from voc4cat import __version__
from voc4cat.util import (
    dag_from_indented_text,
    dag_from_narrower,
    dag_to_narrower,
    dag_to_node_levels,
    get_concept_and_level_from_indented_line,
)

ORGANISATIONS["NFDI4Cat"] = URIRef("http://example.org/nfdi4cat/")
ORGANISATIONS["LIKAT"] = URIRef("https://www.catalysis.de/")
ORGANISATIONS_INVERSE.update({v: k for k, v in ORGANISATIONS.items()})
NOW = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")


def is_file_available(fname, ftype):
    if not isinstance(ftype, list):
        ftype = [ftype]
    if fname is None or not os.path.exists(fname):
        return False
    if "excel" in ftype and fname.suffix.lower().endswith(tuple(EXCEL_FILE_ENDINGS)):
        return True
    if "rdf" in ftype and fname.suffix.lower().endswith(tuple(RDF_FILE_ENDINGS)):
        return True
    return False


def has_file_in_more_than_one_format(dir_):
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
    duplicates = [x for x in file_names if x in seen or seen.add(x)]
    return duplicates


def is_supported_template(wb):
    # TODO add check for Excel template version
    return True


def may_overwrite(no_warn, xlf, outfile, func):
    if not no_warn and os.path.exists(outfile) and Path(xlf) == Path(outfile):
        warn(
            f'Option "{func.__name__}" will overwrite the existing file {outfile}\n'
            "Run again with --no-warn option to overwrite the file."
        )
        return False
    return True


def add_IRI(fpath, outfile):
    """
    Add IRIs from preferred label in col A of sheets Concepts & Collections.

    Safe and valid IRIs are created using django's slugify function.
    Column A is only updated for the rows where the cell is empty.
    """
    print(f"\nRunning add_IRI for file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    VOC_BASE_IRI = wb["Concept Scheme"].cell(row=2, column=2).value
    if VOC_BASE_IRI is None:
        VOC_BASE_IRI = "https://example.org/"
        wb["Concept Scheme"].cell(row=2, column=2).value = VOC_BASE_IRI
    if not VOC_BASE_IRI.endswith("/"):
        VOC_BASE_IRI += "/"

    # process both worksheets
    subsequent_empty_rows = 0
    for sheet in ["Concepts", "Collections"]:
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=2):  # pragma: no branch
            if not row[0].value and row[1].value:
                concept_iri = VOC_BASE_IRI + slugify(row[1].value)
                concept_iri += "-coll" if sheet == "Collections" else ""
                ws.cell(row[0].row, column=1).value = concept_iri
                subsequent_empty_rows = 0
            else:
                # stop processing a sheet after 3 empty rows
                if subsequent_empty_rows < 2:
                    subsequent_empty_rows += 1
                else:
                    break

    wb.save(outfile)
    print(f"Saved updated file as {outfile}")
    return 0


# def load_prefixes(wb):
#     ws = wb["Prefix Sheet"]
#     namespace_prefixes = {}
#     # iterate over first two columns; skip header and start from row 3
#     for row in ws.iter_rows(min_row=3, max_col=2):  # pragma: no branch
#         if row[0].value and row[1].value:
#             prefix, namespace = row[0].value.rstrip(":"), row[1].value
#             namespace_prefixes[namespace] = prefix
#     return namespace_prefixes


def make_ids(fpath, outfile, search_prefix, start_id):
    """
    Replace all prefix:suffix CURIs using IDs counting up from start_id

    If new_prefix is None the new IRI is a concatenation of VOC_BASE_IRI and ID.
    If new_prefix is given the new IRI is the CURI new_prefix:ID.
    """
    print(f"\nReplacing {search_prefix}:... IRIs.")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    VOC_BASE_IRI = wb["Concept Scheme"].cell(row=2, column=2).value
    if VOC_BASE_IRI is None:
        VOC_BASE_IRI = "https://example.org/"
        wb["Concept Scheme"].cell(row=2, column=2).value = VOC_BASE_IRI
    if not VOC_BASE_IRI.endswith("/"):
        VOC_BASE_IRI += "/"

    try:
        start_id = int(start_id)
    except ValueError:
        start_id = -1
    if start_id <= 0:
        raise ValueError(
            'For option --make-ids the "start_id" must be an integer greater than 0.'
        )

    id_gen = count(int(start_id))
    replaced_iris = {}
    # process primary iri column in both worksheets
    for sheet in ["Concepts", "Collections"]:
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=2):  # pragma: no branch
            if row[0].value:
                iri = str(row[0].value)
                if iri.startswith(search_prefix):
                    iri_new = VOC_BASE_IRI + str(next(id_gen))
                    print(f"[{sheet}] Replaced CURI {iri} by {iri_new}")
                    replaced_iris[iri] = iri_new
                    # TODO Check elsewhere, code was unnecessary complex: ws.cell(row[0].row, column=1).value = iri_new
                    row[0].value = iri_new

    # replace iri by new_iri in all columns where it might be referenced
    cols_to_update = {
        "Concepts": [6],
        "Collections": [3],
        "Additional Concept Features": [1, 2, 3, 4, 5],
    }
    for sheet, cols in cols_to_update.items():
        subsequent_empty_rows = 0
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=1 + max(cols)):  # pragma: no branch
            # stop processing a sheet after 3 empty rows
            if subsequent_empty_rows < 3:
                subsequent_empty_rows += 1
            else:
                break
            for col in cols:
                if row[col].value:
                    iris = [iri.strip() for iri in str(row[col].value).split(",")]
                    new_iris = [replaced_iris.get(iri, iri) for iri in iris]
                    print(
                        f"[{sheet}] Replaced {len(new_iris)} CURIs in cell {row[col].coordinate}"
                    )
                    row[col].value = ", ".join(new_iris)
                    subsequent_empty_rows = 0

    wb.save(outfile)
    print(f"Saved updated file as {outfile}")
    return 0


def hierarchy_from_indent(fpath, outfile, sep):
    """
    Convert indentation hierarchy of concepts to children-URI form.

    If separator character(s) are given they will be replaced with
    Excel indent which is also the default if sep is None.
    """
    print(f"\nReading concepts from file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    # process both worksheets
    subsequent_empty_rows = 0
    ws = wb["Concepts"]
    concepts_indented = []
    row_by_iri = defaultdict(dict)
    # read concepts, determine their indentation level, then clear indentation
    col_last = 9
    max_row = 0
    for row in ws.iter_rows(min_row=3, max_col=col_last):  # pragma: no branch
        iri = row[0].value
        if iri and row[1].value:
            row_no = row[0].row
            lang = row[2].value

            if sep is None:  # Excel indentation
                level = int(row[1].alignment.indent)
                ws.cell(row_no, column=2).alignment = Alignment(indent=0)
            else:
                descr, level = get_concept_and_level_from_indented_line(
                    row[1].value, sep=sep
                )
                ws.cell(row_no, column=2).value = descr
                ws.cell(row_no, column=2).alignment = Alignment(indent=0)
            concepts_indented.append(level * " " + iri)

            if iri in row_by_iri:  # merge needed
                # compare fields, merge if one is empty, error if different values
                new_data = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
                old_data = row_by_iri[iri].get(lang, [None] * (len(new_data)))
                merged = []
                labels = ["ChildrenIRI", "Provenance", "SourceVocabURL"]
                for old, new, label in zip(old_data, new_data, labels):
                    if (old and new) and (old != new):
                        raise ValueError(
                            f"Cannot merge rows for {iri}. "
                            "Resolve differences manually."
                        )
                    merged.append(old if old else new)
                row_by_iri[iri][lang] = merged
            else:
                row_by_iri[iri][lang] = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
            max_row = row_no
        else:
            # stop processing a sheet after 3 empty rows
            if subsequent_empty_rows < 2:
                subsequent_empty_rows += 1
            else:
                subsequent_empty_rows = 0
                break

    term_dag = dag_from_indented_text("\n".join(concepts_indented))
    children_by_iri = dag_to_narrower(term_dag)

    # Write rows to xlsx-file, write translation directly after each concept.
    col_children_iri = 7
    row = 3
    for iri in children_by_iri:
        for lang in row_by_iri[iri]:
            ws.cell(row, column=1).value = iri
            for col, stored_value in zip(range(2, col_last), row_by_iri[iri][lang]):
                ws.cell(row, column=col).value = stored_value
            ws.cell(row, column=col_children_iri).value = ", ".join(
                children_by_iri[iri]
            )
            row += 1

    while row <= max_row:
        # Clear remaining rows.
        for col in range(1, col_last):
            ws.cell(row, column=col).value = None
        row += 1

    wb.save(outfile)
    print(f"Saved updated file as {outfile}")
    return 0


def hierarchy_to_indent(fpath, outfile, sep):
    """
    Convert concept hierarchy in children-URI form to indentation.

    If separator character(s) are given they will be used.
    If sep is None, Excel indent will be used.
    """
    print(f"\nReading concepts from file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    ws = wb["Concepts"]

    concept_children_dict = {}
    subsequent_empty_rows = 0
    row_by_iri = defaultdict(dict)
    col_last = 9
    # read all IRI, preferred labels, childrenURIs from the sheet
    for rows_total, row in enumerate(  # pragma: no branch
        ws.iter_rows(min_row=3, max_col=col_last, values_only=True)
    ):
        if row[0] and row[1]:
            iri = row[0]
            lang = row[2]
            if not row[6]:
                childrenURIs = []
            else:
                childrenURIs = [c.strip() for c in row[6].split(",")]
            # We need to check if ChildrenIRI, Provenance & Source Vocab URL
            # are consistent across languages since SKOS has no support for
            # per language statements. (SKOS-XL would add this)
            if iri in row_by_iri:  # merge needed
                # compare fields, merge if one is empty, error if different values
                new_data = [row[col_no] for col_no in range(6, col_last)]
                old_data = row_by_iri[iri][list(row_by_iri[iri].keys())[0]][5:]
                merged = []
                labels = ["ChildrenIRI", "Provenance", "SourceVocabURL"]
                for old, new, label in zip(old_data, new_data, labels):
                    if (old and new) and (old != new):
                        raise ValueError(
                            f"Merge conflict for concept {iri} in column {label}. "
                            f'New: "{new}" - Before: "{old}"'
                        )
                    merged.append(old if old else new)
                row_by_iri[iri][lang] = [row[col] for col in range(1, 6)] + merged
            else:
                row_by_iri[iri][lang] = [row[col] for col in range(1, col_last)]
                concept_children_dict[iri] = childrenURIs

        else:
            # stop processing a sheet after 3 empty rows
            if subsequent_empty_rows < 2:
                subsequent_empty_rows += 1
            else:
                subsequent_empty_rows = 0
                rows_total = rows_total - 2
                break

    term_dag = dag_from_narrower(concept_children_dict)
    concept_levels = dag_to_node_levels(term_dag)

    # Write indented rows to xlsx-file but
    # 1 - each concept translation only once
    # 2 - details only once per concept and language
    iri_written = []
    row = 3
    for iri, level in concept_levels:
        for transl_no, lang in enumerate(row_by_iri[iri]):
            if transl_no and (iri, lang) in iri_written:  # case 1
                continue
            ws.cell(row, 1).value = iri
            concept_text = row_by_iri[iri][lang][0]
            if sep is None:
                ws.cell(row, 2).value = concept_text
                ws.cell(row, 2).alignment = Alignment(indent=level)
            else:
                ws.cell(row, 2).value = sep * level + concept_text
                ws.cell(row, 2).alignment = Alignment(indent=0)
            ws.cell(row, 3).value = lang

            if (iri, lang) in iri_written:  # case 2
                for col, stored_value in zip(
                    range(4, col_last + 1), row_by_iri[iri][lang][2:]
                ):
                    ws.cell(ws.cell(row, 1).row, column=col).value = None
                row += 1
                continue
            else:
                for col, stored_value in zip(
                    range(4, col_last + 1), row_by_iri[iri][lang][2:]
                ):
                    ws.cell(ws.cell(row, 1).row, column=col).value = stored_value
            # clear children IRI column G
            ws.cell(ws.cell(row, 1).row, column=7).value = None
            row += 1
            iri_written.append((iri, lang))

    wb.save(outfile)
    print(f"Saved updated file as {outfile}")
    return 0


def run_ontospy(file_path, output_path):
    """
    Generate Ontospy documentation for a file or directory of files.
    """
    import ontospy
    from ontospy.gendocs.viz.viz_d3dendogram import Dataviz
    from ontospy.gendocs.viz.viz_html_single import HTMLVisualizer

    if Path(file_path).is_dir():
        turtle_files = glob.glob(f"{file_path}/*.ttl")
        if not turtle_files:
            print(f"No turtle file(s) found to document with Ontospy in {file_path}")
            return 1
    elif Path(file_path).exists():
        turtle_files = [file_path]
    else:
        print(f"File/dir not found (ontospy): {file_path}")
        return 1

    for turtle_file in turtle_files:
        print(f"\nBuilding ontospy documentation for {turtle_file}")
        specific_output_path = Path(output_path) / Path(turtle_file).stem

        g = ontospy.Ontospy(Path(turtle_file).resolve().as_uri())

        docs = HTMLVisualizer(g)
        docs_path = os.path.join(specific_output_path, "docs")
        docs.build(docs_path)  # => build and save docs/visualization.

        viz = Dataviz(g)
        viz_path = os.path.join(specific_output_path, "dendro")
        viz.build(viz_path)  # => build and save docs/visualization.

    return 0


def check(fpath, outfile):
    """
    Check vocabulary in Excel sheet

    For concepts:
    - The "Concept IRI" must be unique; this is the case when no language
      is used more than once per concept.
    """
    print(f"\nRunning check of Concepts sheet for file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    ws = wb["Concepts"]
    color = PatternFill("solid", start_color="00FFCC00")  # orange

    subsequent_empty_rows = 0
    seen_conceptIRIs = []
    failed_check = False
    for row in ws.iter_rows(min_row=3, max_col=3):  # pragma: no branch
        if row[0].value and row[1].value:
            conceptIRI, _, lang = [
                c.value.strip() if c.value is not None else "" for c in row
            ]

            new_conceptIRI = f'"{conceptIRI}"@{lang.lower()}'
            if new_conceptIRI in seen_conceptIRIs:
                failed_check = True
                print(
                    f'ERROR: Same Concept IRI "{conceptIRI}" used more than once for '
                    f'language "{lang}"'
                )
                # colorize problematic cells
                row[0].fill = color
                row[2].fill = color
                seen_in_row = 3 + seen_conceptIRIs.index(new_conceptIRI)
                ws[f"A{seen_in_row}"].fill = color
                ws[f"C{seen_in_row}"].fill = color
            else:
                seen_conceptIRIs.append(new_conceptIRI)

            subsequent_empty_rows = 0
        else:
            # stop processing a sheet after 3 empty rows
            if subsequent_empty_rows < 2:
                subsequent_empty_rows += 1
            else:
                subsequent_empty_rows = 0
                break

    if failed_check:
        wb.save(outfile)
        print(f"Saved file with highlighted errors as {outfile}")
        return 1

    print("All checks passed successfully.")
    return 0


def run_vocexcel(args=None):
    if args is None:  # pragma: no cover
        args = []  # Important! Prevents vocexcel to use args from sys.argv.
    retval = vocexcel_main(args)
    if retval is not None:
        return 1
    return 0


def main_cli(args=None):
    if args is None:  # voc4cat run via entrypoint
        args = sys.argv[1:]

    has_args = True if args else False

    parser = argparse.ArgumentParser(
        prog="voc4cat", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-v",
        "--version",
        help="The version of this wrapper of VocExcel.",
        action="store_true",
    )

    parser.add_argument(
        "-i",
        "--add_IRI",
        help=(
            "Add IRI (http://example.org/...) for concepts and collections "
            "if none is present."
        ),
        action="store_true",
    )
    parser.add_argument(
        "--make-ids",
        help=(
            "Specify prefix to search and replace by ID-based vocabulary IRIs. "
            "The prefix and the start ID (positive interger) are required."
        ),
        nargs=2,
        metavar=("prefix", "start-ID"),
        type=str,
        required=False,
    )

    parser.add_argument(
        "--output-directory",
        help=(
            "Specify directory where files should be written to. "
            "The directory is created if required."
        ),
        type=Path,
        required=False,
    )

    parser.add_argument(
        "-c",
        "--check",
        help=(
            "Perform various checks on vocabulary in Excel file (detect duplicates,...)"
        ),
        action="store_true",
    )

    parser.add_argument(
        "--docs",
        help=("Build documentation and dendrogram-visualization with ontospy."),
        action="store_true",
    )

    parser.add_argument(
        "-l",
        "--logfile",
        help=(
            "The file to write logging output to. If -od/--output-directory is also "
            "given, the file is placed in that directory."
        ),
        type=Path,
        required=False,
    )

    parser.add_argument(
        "-f",
        "--forward",
        help=("Forward file resulting from running other options to vocexcel."),
        action="store_true",
    )

    parser.add_argument(
        "--hierarchy-from-indent",
        help=("Convert concept sheet with indentation to children-URI hierarchy."),
        action="store_true",
    )

    parser.add_argument(
        "--hierarchy-to-indent",
        help=("Convert concept sheet from children-URI hierarchy to indentation."),
        action="store_true",
    )

    parser.add_argument(
        "--indent-separator",
        help=(
            "Separator character(s) to read/write indented hierarchies "
            "(default: Excel's indent)."
        ),
        type=str,
        required=False,
    )

    parser.add_argument(
        "--no-warn",
        help=(
            "Don't warn if an input file would be overwritten by the generated "
            "output file."
        ),
        action="store_true",
    )

    parser.add_argument(
        "file_to_preprocess",
        nargs="?",  # allow 0 or 1 file name as argument
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )

    parser.add_argument(
        "vocexcel_options",
        nargs="?",  # allow 0 or 1 file name as argument
        help=(
            "Options to forward to vocexcel. Run vocexcel --help to see what "
            "is available."
        ),
    )

    args_wrapper, unknown_option = parser.parse_known_args(args)
    vocexcel_args = args_wrapper.vocexcel_options or []

    err = 0  # return error code

    if not has_args:
        # show help if no args are given
        parser.print_help()
        return err

    outdir = args_wrapper.output_directory
    if outdir is not None and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)

    logfile = args_wrapper.logfile
    if logfile is not None:
        if outdir is not None:
            logfile = Path(outdir) / logfile
        elif not logfile.parents[0].exists():
            os.makedirs(logfile.parents[0], exist_ok=True)
        vocexcel_args.append("--logfile")
        vocexcel_args.append(str(logfile))

    if args_wrapper.indent_separator is not None:
        sep = args_wrapper.indent_separator
        if not len(sep):
            raise ValueError(
                "Setting the indent separator to zero length is not allowed."
            )
    else:  # Excel's default indent / openpyxl.styles.Alignment(indent=0)
        sep = None

    if args_wrapper.version:
        print(f"voc4cat {__version__}")

    elif args_wrapper.hierarchy_from_indent or args_wrapper.hierarchy_to_indent:
        if is_file_available(args_wrapper.file_to_preprocess, ftype="excel"):
            fprefix, fsuffix = str(args_wrapper.file_to_preprocess).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = args_wrapper.file_to_preprocess
            else:
                outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
        elif args_wrapper.file_to_preprocess.is_dir():
            # processing all files in directory is not supported for now.
            raise NotImplementedError(
                "Processing all files in directory not implemented for this option."
            )
        else:
            print(f"File not found: {args_wrapper.file_to_preprocess}.")
            return 1
        if args_wrapper.hierarchy_from_indent:
            hierarchy_from_indent(args_wrapper.file_to_preprocess, outfile, sep)
        else:
            hierarchy_to_indent(args_wrapper.file_to_preprocess, outfile, sep)

    elif args_wrapper.add_IRI or args_wrapper.make_ids or args_wrapper.check:
        funcs = [
            m
            for m, to_run in zip(
                [add_IRI, make_ids, check],
                [args_wrapper.add_IRI, args_wrapper.make_ids, args_wrapper.check],
            )
            if to_run
        ]
        if os.path.isdir(args_wrapper.file_to_preprocess):
            to_build_docs = False
            for xlf in glob.glob(
                os.path.join(args_wrapper.file_to_preprocess, "*.xlsx")
            ):
                fprefix, fsuffix = xlf.rsplit(".", 1)
                fname = os.path.split(fprefix)[1]  # split off leading dirs
                if outdir is None:
                    outfile = Path(xlf)
                else:
                    outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
                infile = Path(xlf)
                for func in funcs:
                    if not may_overwrite(args_wrapper.no_warn, xlf, outfile, func):
                        return 1
                    if args_wrapper.make_ids:
                        err += func(infile, outfile, *args_wrapper.make_ids)
                    else:
                        err += func(infile, outfile)
                    infile = outfile
                if args_wrapper.forward:
                    print(f"\nCalling VocExcel for forwarded Excel file {infile}")
                    locargs = list(vocexcel_args)
                    locargs.append(str(infile))
                    err += run_vocexcel(locargs)
                to_build_docs = True

            if args_wrapper.docs and args_wrapper.forward and to_build_docs:
                indir = args_wrapper.file_to_preprocess if outdir is None else outdir
                doc_path = infile.parent if outdir is None else outdir
                err += run_ontospy(indir, doc_path)

        elif is_file_available(args_wrapper.file_to_preprocess, ftype="excel"):
            fprefix, fsuffix = str(args_wrapper.file_to_preprocess).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = Path(args_wrapper.file_to_preprocess)
            else:
                outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
            infile = args_wrapper.file_to_preprocess
            for func in funcs:
                if not may_overwrite(args_wrapper.no_warn, infile, outfile, func):
                    return 1
                if args_wrapper.make_ids:
                    err += func(infile, outfile, *args_wrapper.make_ids)
                else:
                    err += func(infile, outfile)
                infile = outfile
            if args_wrapper.forward:
                print(f"\nCalling VocExcel for forwarded Excel file {infile}")
                locargs = list(vocexcel_args)
                locargs.append(str(infile))
                err += run_vocexcel(locargs)
            if args_wrapper.docs:
                infile = Path(infile).with_suffix(".ttl") if outdir is None else outfile
                doc_path = infile.parent if outdir is None else outdir
                err += run_ontospy(infile, doc_path)
        else:
            print(
                "Expected xlsx-file or directory but got: {0}".format(
                    args_wrapper.file_to_preprocess
                )
            )
            return 1
    elif args_wrapper and args_wrapper.file_to_preprocess:
        if os.path.isdir(args_wrapper.file_to_preprocess):
            dir_ = args_wrapper.file_to_preprocess
            if duplicates := has_file_in_more_than_one_format(dir_):  # noqa: WPS332
                print(
                    "Files may only be present in one format. Found more than one "
                    "format for:\n  " + "\n  ".join(duplicates)
                )
                return 1

            turtle_files = glob.glob(os.path.join(dir_, "*.ttl")) + glob.glob(
                os.path.join(dir_, "*.turtle")
            )
            xlsx_files = glob.glob(os.path.join(dir_, "*.xlsx"))
        elif is_file_available(args_wrapper.file_to_preprocess, ftype=["excel"]):
            turtle_files = []
            xlsx_files = [str(args_wrapper.file_to_preprocess)]
        elif is_file_available(args_wrapper.file_to_preprocess, ftype=["rdf"]):
            turtle_files = [str(args_wrapper.file_to_preprocess)]
            xlsx_files = []
        else:
            if os.path.exists(args_wrapper.file_to_preprocess):
                print(f"Cannot convert file {args_wrapper.file_to_preprocess}")
                endings = ", ".join(
                    [f".{ext}" for ext in EXCEL_FILE_ENDINGS]
                    + list(RDF_FILE_ENDINGS.keys())
                )
                print(f"Files for processing must end with one of {endings}.")
            else:
                print(f"File not found: {args_wrapper.file_to_preprocess}.")
            return 1

        if xlsx_files:
            print("\nCalling VocExcel for Excel files")
        for xlf in xlsx_files:
            print(f"  {xlf}")
            locargs = list(vocexcel_args)
            locargs.append(xlf)
            fprefix, fsuffix = str(xlf).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = Path(f"{fprefix}.ttl")
            else:
                outfile = Path(outdir) / Path(f"{fname}.ttl")
                locargs = ["--outputfile", str(outfile)] + locargs
            err += run_vocexcel(locargs)

        if turtle_files:
            print("Calling VocExcel for turtle files")
        for ttlf in turtle_files:
            print(f"  {ttlf}")
            locargs = list(vocexcel_args)
            locargs.append(ttlf)
            fprefix, fsuffix = str(ttlf).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = Path(f"{fprefix}.xlsx")
            else:
                outfile = Path(outdir) / Path(f"{fname}.xlsx")
                locargs = ["--outputfile", str(outfile)] + locargs
            err += run_vocexcel(locargs)

        if (
            args_wrapper.docs
            and (args_wrapper.forward or turtle_files)
            and os.path.isdir(args_wrapper.file_to_preprocess)
        ):
            infile = args_wrapper.file_to_preprocess
            doc_path = infile if outdir is None else outdir
            err += run_ontospy(infile, doc_path)
        elif args_wrapper.docs:
            infile = Path(args_wrapper.file_to_preprocess).with_suffix(".ttl")
            doc_path = outdir if outdir is not None else infile.parent
            err += run_ontospy(infile, doc_path)
    else:
        # Unknown voc4cat option
        print(f"Unknown option: {unknown_option}")
        return 1

    return err


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    sys.exit(err)
