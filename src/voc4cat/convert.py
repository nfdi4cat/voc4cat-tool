from sys import path
from pathlib import Path
import argparse
path.append(str(Path(__file__).parent.parent))
from vocexcel import profiles, convert, __version__
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from rdflib import Graph, URIRef, Literal
import re


def validate_uri(uri: str):
    uri_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if re.match(uri_pattern, uri) is not None:
        return True
    else:
        return False


def make_vocabulary(
        g: Graph,
        voc_uri: str,
        title: str,
        description: str,
        created: str,
        modified: str,
        creator: str,
        publisher: str,
        version: str,
        provenance : str,
        custodian: str
):
    assert validate_uri(voc_uri), "The Vocabulary URI you supplied is invalid"


def convert_file(excel_file_path: Path):
    wb = None
    try:
        wb = load_workbook(filename=str(excel_file_path))
        sheet_ranges = wb["example - complex"]

        g = Graph()

        # Vocabulary
        voc_uri = sheet_ranges["B1"].value
        title = sheet_ranges["B2"].value
        description = sheet_ranges["B3"].value
        created = sheet_ranges["B4"].value
        modified = sheet_ranges["B5"].value
        creator = sheet_ranges["B6"].value
        publisher = sheet_ranges["B7"].value
        version = sheet_ranges["B8"].value
        provenance = sheet_ranges["B9"].value
        custodian = sheet_ranges["B10"].value

        make_vocabulary(g, voc_uri, title, description, created, modified, creator, publisher, version, provenance, custodian)

    except InvalidFileException as e:
        print("You supplied a path to a file that either doesn't exist or isn't an Excel file")


def main(args=None):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-v",
        "--version",
        help="The version of this copy of VocExel.",
        action="store_true"
    )

    parser.add_argument(
        "-lp",
        "--listprofiles",
        help="This flag, if set, must be the only flag supplied. It will cause the program to list all the vocabulary"
        " profiles that this converter, indicating both their URI and their short token for use with the"
        " -p (--profile) flag when converting Excel files",
        action="store_true",
    )

    parser.add_argument(
        "excel_file",
        type=Path,
        help="The Excel file to convert to a SKOS vocabulary in RDF",
    )

    parser.add_argument(
        "-val",
        "--validate",
        help="Validate output file",
        action="store_true"
    )

    parser.add_argument(
        "-p",
        "--profile",
        help="A profile - a specified information model - for a vocabulary. This tool understands several profiles and"
             "you can choose which one you want to convert the Excel file according to. The list of profiles - URIs "
             "and their corresponding tokens - supported by VocExcel, can be found by running the program with the "
             "flag -lp or --listprofiles.",
        default="vocpub",
    )

    args = parser.parse_args()

    if args.listprofiles:
        print(profiles.list_profiles())
        exit()
    elif args.version:
        print(__version__)
        exit()
    elif args.excel_file:
        print(f"Processing file {args.excel_file}")

        convert_file(args.excel_file)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
