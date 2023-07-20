"""New command line interface for voc4cat with subcommands"""

import argparse
import logging
import sys

from voc4cat.checks import Voc4catError

logger = logging.getLogger(__name__)


def main_cli(args=None):
    """
    _summary_

    _extended_summary_

    Parameters
    ----------
    args : _type_, optional
        _description_, by default None

    Possible command structure:

    voc4cat
    <subcommands>
    -V --version
    -H --help
    -v -vv --verbose
    -q -qq  --quiet
    -l --logfile
    --force (was: --no-warn)        here or better on subcmds?
    -O --outputdir   here or better on subcmds?

    transform                     Conversions with xlsx files as input and output
        file-to-process
        --make-ids prefix start-ID  Specify prefix to search and replace by ID-based vocabulary IRIs. ...
        --hierarchy-from-indent     Convert concept sheet with indentation to children-URI hierarchy.
        --hierarchy-to-indent       Convert concept sheet from children-URI hierarchy to indentation.
        --indent-separator          Separator character(s) to read/write indented hierarchies (default: xlsx indent)

    convert     Convert between rdf and xlsx and back.
        file-to-process
        --rdf-format  xml, turtle, json-ld   Output format of generated rdf.
        --output-type screen/file       Where to output generated rdf.
        --template  Path to xlsx template to be used when converting to xlsx.

    docs        Documentation generation from rdf
        file-to-process

    check       Validation and checks
        file-to-process
        --xlsx
        --ci
        --shacl
        --listprofiles
        -p --profile    Profile name or file (implies --shacl = True)

    """
    parser = argparse.ArgumentParser(
        prog="voc4cat-ng", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

def start_cli_app(args=None):
    if args is None:  # app started via entrypoint
        args = sys.argv[1:]
    try:
        main_cli(args)
    except Voc4catError:
        logger.exception()
        sys.exit(1)
    except Exception:
        logger.exception()
        sys.exit(2)

if __name__ == "__main__":
    start_cli_app(sys.argv[1:])
