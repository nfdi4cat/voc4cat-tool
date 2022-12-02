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
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from warnings import warn

import openpyxl
from django.utils.text import slugify
from openpyxl.styles import Alignment, PatternFill
from rdflib import URIRef
from vocexcel.convert import main
from vocexcel.models import ORGANISATIONS, ORGANISATIONS_INVERSE
from vocexcel.utils import EXCEL_FILE_ENDINGS, KNOWN_FILE_ENDINGS, RDF_FILE_ENDINGS

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

try:
    __version__ = version("voc4cat")
except PackageNotFoundError:
    # package is not installed
    try:
        from ._version import version as __version__
    except ImportError:
        __version__ = "0.0.0"


def is_file_available(fname, ftype):
    if not isinstance(ftype, list):
        ftype = [ftype]
    if fname is None or not os.path.exists(fname):
        print(f"File not found: {fname}")
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
    elif not VOC_BASE_IRI.endswith("/"):
        VOC_BASE_IRI += "/"

    # process both worksheets
    subsequent_empty_rows = 0
    for sheet in ["Concepts", "Collections"]:
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=2):
            if not row[0].value and row[1].value:
                concept_iri = VOC_BASE_IRI + slugify(row[1].value)
                concept_iri += "-coll" if sheet == "Collections" else ""
                ws.cell(row[0].row, column=1).value = concept_iri
                subsequent_empty_rows = 0
            elif row[0].value is None and row[1].value is None:
                # stop processing a sheet after 3 empty rows
                if subsequent_empty_rows < 2:
                    subsequent_empty_rows += 1
                else:
                    break

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
    row_by_iri = {}
    # read concepts, determine their indentation level, then clear indentation
    col_last = 9
    for row in ws.iter_rows(min_row=3, max_col=col_last):
        iri = row[0].value
        row_no = row[0].row
        if iri and row[1].value:
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
            # TODO think about how to handle language.
            if iri in row_by_iri:  # merge needed
                # compare fields, merge if one is empty, error if different values
                new_data = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
                merged = []
                for old, new in zip(row_by_iri[iri], new_data):
                    if (old and new) and (old != new):
                        raise ValueError(
                            "Cannot merge rows for {iri}. Resolve differences manually."
                        )
                    merged.append(old if old else new)
                row_by_iri[iri] = merged
            else:
                row_by_iri[iri] = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
            max_row = row_no
        elif iri is None and row[1].value is None:
            # stop processing a sheet after 3 empty rows
            if subsequent_empty_rows < 2:
                subsequent_empty_rows += 1
            else:
                subsequent_empty_rows = 0
                break

    term_dag = dag_from_indented_text("\n".join(concepts_indented))
    children_by_iri = dag_to_narrower(term_dag)

    # Update childrenURI column
    col_children_iri = 7
    for iri, row in zip(children_by_iri, ws.iter_rows(min_row=3, max_col=col_last)):
        ws.cell(row[0].row, column=1).value = iri
        for col, stored_value in zip(range(2, col_last), row_by_iri[iri]):
            ws.cell(row[0].row, column=col).value = stored_value
        ws.cell(row[0].row, column=col_children_iri).value = ", ".join(
            children_by_iri[iri]
        )

    # Clear remaining rows.
    first_row_to_clear = 3 + len(children_by_iri)
    for row in ws.iter_rows(min_row=first_row_to_clear, max_col=col_last):
        for col in range(1, col_last):
            ws.cell(row[0].row, column=col).value = None
        if row[0].row == max_row:
            break

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
    row_by_iri = {}
    col_last = 9
    # read all IRI, preferred labels, childrenURIs from the sheet
    for rows_total, row in enumerate(
        ws.iter_rows(min_row=3, max_col=col_last, values_only=True)
    ):
        if row[0] and row[1]:
            iri = row[0]
            if not row[6]:
                childrenURIs = []
            else:
                childrenURIs = [c.strip() for c in row[6].split(",")]
            concept_children_dict[iri] = childrenURIs
            row_by_iri[iri] = [row[col] for col in range(1, col_last)]
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

    # Set cell values by breaking them down into individual cells
    iri_written = []
    for row, (iri, level) in zip(
        ws.iter_rows(min_row=3, max_col=col_last), concept_levels
    ):
        row[0].value = iri
        concept_text = row_by_iri[iri][0]
        if sep is None:
            row[1].value = concept_text
            row[1].alignment = Alignment(indent=level)
        else:
            row[1].value = sep * level + concept_text
            row[1].alignment = Alignment(indent=0)
        row[2].value = row_by_iri[iri][1]
        for col, stored_value in zip(range(4, col_last), row_by_iri[iri][2:]):
            if iri in iri_written:
                ws.cell(row[0].row, column=col).value = None
            else:
                ws.cell(row[0].row, column=col).value = stored_value
            # clear children IRI column G
            ws.cell(row[0].row, column=7).value = None
        iri_written.append(iri)

    wb.save(outfile)
    print(f"Saved updated file as {outfile}")
    return 0


def run_ontospy(file_path, output_path):
    """
    Generate Ontospy documentation for a file or directory of files.
    """
    import ontospy
    from ontospy.ontodocs.viz.viz_d3dendogram import Dataviz
    from ontospy.ontodocs.viz.viz_html_single import HTMLVisualizer

    if not glob.glob("outbox/*.ttl"):
        print(f'No turtle file found to document with Ontospy in "{file_path}"')
        return 1

    print(f"\nBuilding ontospy documentation for {file_path}")

    g = ontospy.Ontospy(file_path)

    docs = HTMLVisualizer(g)
    docs_path = os.path.join(output_path, "docs")
    docs.build(docs_path)  # => build and save docs/visualization.

    viz = Dataviz(g)
    viz_path = os.path.join(output_path, "dendro")
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
    for row in ws.iter_rows(min_row=3, max_col=3):
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
        elif row[0].value is None and row[1].value is None:
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
    retval = main(args)
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
        "--output_directory",
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
            "The file to write logging output to. If -od/--output_directory is also "
            "given, the file is placed in that diretory."
        ),
        type=Path,
        required=False,
    )

    parser.add_argument(
        "-f",
        "--forward",
        help=("Forward file resulting from other running other options to vocexcel."),
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

    args_wrapper, vocexcel_args = parser.parse_known_args(args)

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

    if args_wrapper.indent_separator:
        sep = args_wrapper.indent_separator
        if not len(sep):
            raise ValueError(
                "Setting the indent separator to zero length is not allowed."
            )
    else:  # Excel's default indent / openpyxl.styles.Alignment(indent=0)
        sep = None

    if args_wrapper.version:
        print(f"voc4cat {__version__}")

    elif args_wrapper.hierarchy_from_indent:
        if is_file_available(args_wrapper.file_to_preprocess, ftype="excel"):
            fprefix, fsuffix = str(args_wrapper.file_to_preprocess).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = args_wrapper.file_to_preprocess
            else:
                outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
        else:
            # processing all file in directory is not supported for now.
            raise NotImplementedError()
        hierarchy_from_indent(args_wrapper.file_to_preprocess, outfile, sep)

    elif args_wrapper.hierarchy_to_indent:
        if is_file_available(args_wrapper.file_to_preprocess, ftype="excel"):
            fprefix, fsuffix = str(args_wrapper.file_to_preprocess).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = args_wrapper.file_to_preprocess
            else:
                outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
        else:
            # processin all file in directory is not supported for now.
            raise NotImplementedError()
        hierarchy_to_indent(args_wrapper.file_to_preprocess, outfile, sep)

    elif args_wrapper.add_IRI or args_wrapper.check:
        funcs = [
            m
            for m, to_run in zip(
                [add_IRI, check],
                [args_wrapper.add_IRI, args_wrapper.check],
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
                    outfile = xlf
                else:
                    outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
                infile = xlf
                for func in funcs:
                    if not may_overwrite(args_wrapper.no_warn, xlf, outfile, func):
                        return 1
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
                doc_path = infile.parent[0] if outdir is None else outdir
                err += run_ontospy(indir, doc_path)

        elif is_file_available(args_wrapper.file_to_preprocess, ftype="excel"):
            fprefix, fsuffix = str(args_wrapper.file_to_preprocess).rsplit(".", 1)
            fname = os.path.split(fprefix)[1]  # split off leading dirs
            if outdir is None:
                outfile = args_wrapper.file_to_preprocess
            else:
                outfile = Path(outdir) / Path(f"{fname}.{fsuffix}")
            infile = args_wrapper.file_to_preprocess
            for func in funcs:
                if not may_overwrite(args_wrapper.no_warn, infile, outfile, func):
                    return 1
                err += func(infile, outfile)
                infile = outfile
            if args_wrapper.forward:
                print(f"\nCalling VocExcel for forwarded Excel file {infile}")
                locargs = list(vocexcel_args)
                locargs.append(str(infile))
                err += run_vocexcel(locargs)
            if args_wrapper.docs:
                infile = Path(infile).with_suffix(".ttl") if outdir is None else outfile
                doc_path = infile.parent[0] if outdir is None else outdir
                err += run_ontospy(infile, doc_path)
        else:
            return err
    elif args_wrapper and args_wrapper.file_to_preprocess:
        if os.path.isdir(args_wrapper.file_to_preprocess):
            to_build_docs = False
            dir_ = args_wrapper.file_to_preprocess
            if duplicates := has_file_in_more_than_one_format(dir_):  # noqa: WPS332
                print(
                    "Files may only be present in one format. Found more than one "
                    "format for:\n  " + "\n  ".join(duplicates)
                )
                return 1
            print("\nCalling VocExcel for Excel files")
            for xlf in glob.glob(os.path.join(dir_, "*.xlsx")):
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

            print("Calling VocExcel for turtle files")
            for ttlf in glob.glob(os.path.join(dir_, "*.ttl")) + glob.glob(
                os.path.join(dir_, "*.turtle")
            ):
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
                to_build_docs = True

            if args_wrapper.docs and args_wrapper.forward and to_build_docs:
                infile = args_wrapper.file_to_preprocess
                doc_path = outdir if outdir is not None else infile.parent[0]
                err += run_ontospy(infile, doc_path)

        elif is_file_available(args_wrapper.file_to_preprocess, ftype=["excel", "rdf"]):
            print(f"Calling VocExcel for file {args_wrapper.file_to_preprocess}")
            err += run_vocexcel(args)
            if args_wrapper.docs:
                infile = Path(args_wrapper.file_to_preprocess).with_suffix(".ttl")
                doc_path = outdir if outdir is not None else infile.parent[0]
                err += run_ontospy(infile, doc_path)
        else:
            if os.path.exists(args_wrapper.file_to_preprocess):
                print(f"Cannot convert file {args_wrapper.file_to_preprocess}")
                endings = ", ".join(
                    [f".{ext}" for ext in EXCEL_FILE_ENDINGS]
                    + list(RDF_FILE_ENDINGS.keys())
                )
                print(f"Files for processing must end with one of {endings}.")
            err = 0
    else:
        print("\nThis part should not be reached!")
        err = 1

    return err


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    # CI needs to know if an error occurred (failed check or validation error)
    sys.exit(err)
