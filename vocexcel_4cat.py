"""
Add mechanism to extend VocExcel with more commands

The new commands be may be run either before or after VocExcel.

Copyright (c) 2022 David Linke (ORCID: 0000-0002-5898-1820)
"""
import argparse
import sys

from pathlib import Path

from vocexcel.convert import main
from vocexcel.utils import EXCEL_FILE_ENDINGS
from vocexcel.models import ORGANISATIONS

__version__ = "0.1.0"

ORGANISATIONS['NFDI4Cat'] = "http://example.org/nfdi4cat/"

def run_vocexcel(args=None):
    main(args)


def wrapper(args=None):
    print("Running VocExcel wrapper")
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-v",
        "--version",
        help="The version of this wrapper of VocExel.",
        action="store_true",
    )

    parser.add_argument(
        "file_to_preprocess",
        nargs="?",  # allow 0 or 1 file name as argument
        type=Path,
        help="The Excel file to preprocess and convert to a SKOS vocabulary.",
    )

    args_wrapper = parser.parse_args()

    if args_wrapper.version:
        print(f"{__version__}")
    elif args_wrapper and args_wrapper.file_to_preprocess:
        if not args_wrapper.file_to_preprocess.suffix.lower().endswith(
            tuple(EXCEL_FILE_ENDINGS)
        ):
            print("Files for preprocessing must end with .xlsx (Excel).")
            sys.exit()
        else:
            print(f"Processing file {args_wrapper.file_to_preprocess}")
            print("\nCalling VocExcel")
            main(args)
    else:
        print("\nCalling VocExcel")
        # We add a dummy since vocexcel must be called with a filename.
        main(args.insert(1, "."))

    return args_wrapper


if __name__ == "__main__":
    w = wrapper(sys.argv[1:])
