"""
Add mechanism to extend VocExcel with more commands

The new commands be may be run either before or after VocExcel.

Copyright (c) 2022 David Linke (ORCID: 0000-0002-5898-1820)
"""
import argparse
import datetime
import glob
import os
import sys
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

import openpyxl
from openpyxl.styles import PatternFill

from rdflib import URIRef

from vocexcel.convert import main
from vocexcel.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS, KNOWN_FILE_ENDINGS
from vocexcel.models import ORGANISATIONS, ORGANISATIONS_INVERSE

from django.utils.text import slugify

ORGANISATIONS["NFDI4Cat"] = URIRef("http://example.org/nfdi4cat/")
ORGANISATIONS["LIKAT"] = URIRef("https://www.catalysis.de/")
ORGANISATIONS_INVERSE.update({v: k for k, v in ORGANISATIONS.items()})
NOW = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")

try:
    __version__ = version("voc4cat")
except PackageNotFoundError:
    # package is not installed
    try:
        from _version import version as __version__
    except ImportError:
        __version__ = "0.0.0"


def is_file_available(fname, ftype):
    if not type(ftype) is list:
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
    else:
        seen = set()
        duplicates = [x for x in file_names if x in seen or seen.add(x)]
        return duplicates


def is_supported_template(wb):
    # TODO add check for Excel template version
    return True


def may_overwrite(no_warn, xlf, outfile, func):
    if not no_warn and os.path.exists(outfile) and Path(xlf) == Path(outfile):
        print(
            f'Option "{func.__name__}" will overwrite the existing file {outfile}\n'
            "Run again with --no-warn option to overwrite the file."
        )
        return False
    else:
        return True


def add_IRI(fpath, outfile):
    """
    Add IRIs from preferred label in col A of sheets Concepts & Collections

    Safe and valid IRIs are created using django's slugify function.
    Column A is only updated for the rows where the cell is empty.
    """
    print(f"\nRunning add_IRI for file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    VOC_BASE_IRI = wb["Concept Scheme"].cell(row=2, column=2).value
    if not VOC_BASE_IRI.endswith("/"):
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


def add_related(fpath, outfile):
    """
    Add related Children URI and Members URI by preferred label if none is present.

    In detail the folowing sheets are modified:
    "Concepts": update col. G "Children URI" from col. J "Children by Pref. Label"
    "Collections": update col. D "Members URI" from col. F "Members by Pref. Label"
    """
    print(f"\nRunning add_related for file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    # process both worksheets
    subsequent_empty_rows = 0
    for sheet in ["Concepts", "Collections"]:
        print(f"Processing sheet '{sheet}'")
        ws = wb[sheet]
        pref_label_lookup = {}
        # read all preferred labels from the sheet
        for row in ws.iter_rows(min_row=3, max_col=2):
            if row[0].value and row[1].value:
                pref_label_lookup[slugify(row[1].value)] = row[0].value
                subsequent_empty_rows = 0
            elif row[0].value is None and row[1].value is None:
                # stop processing a sheet after 3 empty rows
                if subsequent_empty_rows < 2:
                    subsequent_empty_rows += 1
                else:
                    subsequent_empty_rows = 0
                    break

        # update read all peferred labels from the sheet
        col_to_fill = 6 if sheet == "Concepts" else 3
        col_preflabel = 9 if sheet == "Concepts" else 5
        for row in ws.iter_rows(min_row=3, max_col=col_preflabel + 1):
            if not row[col_to_fill].value and row[col_preflabel].value:
                # update cell in col_to_fill
                pref_label_slugs = [
                    slugify(pl.strip()) for pl in row[col_preflabel].value.split(",")
                ]
                found = [
                    pref_label_lookup[pl]
                    for pl in pref_label_slugs
                    if pl in pref_label_lookup
                ]
                ws.cell(row[0].row, column=col_to_fill + 1).value = ", ".join(found)
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


def run_ontospy(file_path, output_path):
    """
    Generate Ontospy documentation for a file or directory of files
    """
    import ontospy
    from ontospy.ontodocs.viz.viz_html_single import HTMLVisualizer
    from ontospy.ontodocs.viz.viz_d3dendogram import Dataviz

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

    In detail the following checks are performed:
    Concepts:
    - The language-specific preferred label of a concept must be unique.
      The comparison ignores case.
    - The "Concept IRI" must be unique; this is the case when no language
      is used more than once per concept.
    """
    print(f"\nRunning check of Concepts sheet for file {fpath}")
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    ws = wb["Concepts"]
    color = PatternFill("solid", start_color="00FFCC00")  # orange

    subsequent_empty_rows = 0
    seen_preflabels = []
    # seen_conceptIRIs = defaultdict(list)
    seen_conceptIRIs = []
    failed_check = False
    for row_no, row in enumerate(ws.iter_rows(min_row=3, max_col=3), 3):
        if row[0].value and row[1].value:
            conceptIRI, preflabel, lang = [c.value.strip() for c in row]

            new_preflabel = f'"{preflabel}"@{lang}'.lower()
            if new_preflabel in seen_preflabels:
                failed_check = True
                print(f"ERROR: Duplicate of Preferred Label found: {new_preflabel}")
                # colorise problematic cells
                row[1].fill = row[2].fill = color
                seen_in_row = 3 + seen_preflabels.index(new_preflabel)
                ws[f"B{seen_in_row}"].fill = ws[f"C{seen_in_row}"].fill = color
            else:
                seen_preflabels.append(new_preflabel)

            new_conceptIRI = f'"{conceptIRI}"@{lang.lower()}'
            if new_conceptIRI in seen_conceptIRIs:
                failed_check = True
                print(
                    f'ERROR: Same Concept IRI "{conceptIRI}" used more than once for '
                    'language "{lang}"'
                )
                # colorise problematic cells
                row[0].fill = row[2].fill = color
                seen_in_row = 3 + seen_conceptIRIs.index(new_conceptIRI)
                ws[f"A{seen_in_row}"].fill = ws[f"C{seen_in_row}"].fill = color
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
    else:
        print("All checks passed succesfully.")
        return 0


def run_vocexcel(args=None):
    retval = main(args)
    if retval is not None:
        return 1
    else:
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
        "-od",
        "--output_directory",
        help=(
            "Specify directory where files should be written to. "
            "The directory is created if required."
        ),
        type=Path,
        required=False,
    )

    parser.add_argument(
        "-r",
        "--add_related",
        help=(
            "Add related Children URI and Members URI by preferred label "
            "if none is present."
        ),
        action="store_true",
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
        "--hierarchy-as-indent",
        help=("Convert concept sheet from children-URI hierarchy to indentation."),
        action="store_true",
    )

    parser.add_argument(
        "-sep",
        "--hierarchy-indent-separator",
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

    if not has_args:
        # show help if no args are given
        parser.print_help()
        parser.exit()

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

    if args_wrapper.hierarchy_indent_separator:
        sep = args_wrapper.hierarchy_indent_separator
        if len(sep) < 1:
            raise ValueError(
                "Setting the indent separator to zero length is not allowed."
            )
    else:  # Excel's default indent / openpyxl.styles.Alignment(indent=0)
        sep = "xlsx"
    err = 0
    if args_wrapper.version:
        print(f"{__version__}")

    elif args_wrapper.hierarchy_from_indent:
        raise NotImplementedError()

    elif args_wrapper.hierarchy_as_indent:
        raise NotImplementedError()

    elif args_wrapper.add_IRI or args_wrapper.add_related or args_wrapper.check:
        funcs = [
            m
            for m, to_run in zip(
                [add_IRI, add_related, check],
                [args_wrapper.add_IRI, args_wrapper.add_related, args_wrapper.check],
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
                        parser.exit()
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
                    parser.exit()
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
            parser.exit()
    elif args_wrapper and args_wrapper.file_to_preprocess:
        if os.path.isdir(args_wrapper.file_to_preprocess):
            to_build_docs = False
            dir_ = args_wrapper.file_to_preprocess
            if duplicates := has_file_in_more_than_one_format(dir_):
                print(
                    "Files may only be present in one format. Found more than one "
                    "format for:\n  " + "\n  ".join(duplicates)
                )
                parser.exit()
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

            print("Calling VocExcel for Excel files")
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
                    [f".{e}" for e in EXCEL_FILE_ENDINGS]
                    + list(RDF_FILE_ENDINGS.keys())
                )
                print(f"Files for processing must end with one of {endings}.")
            parser.exit()
    else:
        print("\nThis part should not be reached!")

    return err


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    # CI need to know if an error occurred (failed check or validation error)
    sys.exit(err)
