"""New cleaner command line interface for voc4cat with subcommands."""

import argparse
import logging
import sys
import textwrap
from pathlib import Path

from voc4cat import setup_logging
from voc4cat.checks import Voc4catError

logger = logging.getLogger(__name__)


def transform(args):
    print("Transform subcommand executed!")
    print(f"args: {args!r}")


def convert(args):
    print("Convert subcommand executed!")
    print(f"args: {args!r}")


def check(args):
    print("Check subcommand executed!")
    print(f"args: {args!r}")


def docs(args):
    print("Docs subcommand executed!")
    print(f"args: {args!r}")


class DecentFormatter(argparse.HelpFormatter):
    """
    An argparse formatter that preserves newlines & keeps indentation.
    """

    def _fill_text(self, text, width, indent):
        """
        Reformat text while keeping newlines for lines shorter than width.
        """
        lines = []
        for line in textwrap.indent(textwrap.dedent(text), indent).splitlines():
            lines.append(textwrap.fill(line, width, subsequent_indent=indent))
        return "\n".join(lines)

    def _split_lines(self, text, width):
        """
        Conserve indentation in help/description lines when splitting long lines.
        """
        lines = []
        for line in textwrap.dedent(text).splitlines():
            if not line.strip():
                continue
            indent = " " * (len(line) - len(line.lstrip()))
            lines.extend(
                textwrap.fill(line, width, subsequent_indent=indent).splitlines()
            )
        return lines


def create_root_parser():
    parser = argparse.ArgumentParser(
        prog="voc4cat-ng",
        description="Next generation of command line interface for voc4cat-tool.",
        allow_abbrev=False,
        formatter_class=DecentFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        help="The version of voc4cat command line interface.",
        action="store_true",
    )
    return parser


def create_common_options_parser():
    parser = argparse.ArgumentParser(
        prog="voc4cat-ng",
        description="Next generation of command line interface for voc4cat-tool.",
        allow_abbrev=False,
        add_help=False,
        formatter_class=DecentFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verboser",
        default=0,
        help="Make output more verbose. Repeat to increase verbosity (-vv or -vvv).",
    )
    group.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        dest="quieter",
        help="Make output less verbose. Repeat to decrease verbosity (-qq or -qqq).",
    )
    parser.add_argument(
        "--config",
        help=('Path to config file (typically "idranges.toml").'),
        type=Path,
        required=False,
    )
    parser.add_argument(
        "-l",
        "--logfile",
        help=(
            "Activate logging to a file at given path. "
            "The path will be created if it is not existing."
        ),
        type=Path,
    )
    # We set a do-nothing func here so that we can call func for all parsers below.
    parser.set_defaults(func=lambda _: None)
    return parser


def add_transform_subparser(subparsers, options):
    """Transforms have the same input and output filetype."""
    parser = subparsers.add_parser(
        "transform",
        description=(  # used in subcmd help
            "Transforms have the same input and output filetype. By default a "
            "transform will not overwrite existing files. To enforce replacing "
            'existing files run with "--inplace" flag. Alternatively, supply an '
            "output directory with -O / --outdir flag."
        ),
        help=(  # used in help of root parser
            "Transform data. Transforms have the same input and output filetype."
        ),
        **options,
    )
    parser.add_argument(
        "-O",
        "--outdir",
        help=(
            "Specify directory where files should be written to. "
            "The directory is created if required."
        ),
        metavar=("DIRECTORY"),
        type=Path,
    )
    parser.add_argument(
        "--make-ids",
        help=(
            "Specify prefix or mapping prefix:base-uri and first ID to use. "
            'An example for a prefix-mapping is "ex:https://example.org/". '
            "If only the prefix is given without a base-URI part "
            "the concept-scheme URI is used as base-URI to append the IDs to.\n"
            "The default length of the ID is 7 digits. It can be changed "
            "via a config-file."
        ),
        nargs=2,
        metavar=("PREFIX-MAPPING", "START-ID"),
        type=str,
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
        "--indent",
        help=(
            "Separator character(s) to read/write indented hierarchies "
            'or "xlsx" to use xlsx-indent. (default: "xlsx")'
        ),
        default="xlsx",
        type=str,
        metavar=("SEPARATOR",),
    )
    parser.add_argument(
        "--inplace",  # was "--no-warn"
        help=(
            "Transform file(s) in place. Replaces the input file(s) with the transformed output file(s)."
        ),
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "VOCAB",
        nargs=1,  # allow 0 or 1 file name as argument
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=transform)


def add_convert_subparser(subparsers, options):
    """Conversions xlsx <-> rdf and between different rdf representations."""

    parser = subparsers.add_parser(
        "convert",
        description=(
            "Convert data from xlsx to rdf and back or between different "
            "rdf representations."
        ),
        help=(
            "Convert data from xlsx to rdf, rdf to xlsx or and between different "
            "rdf representations."
        ),
        **options,
    )
    parser.add_argument(
        "-O",
        "--outdir",
        help=(
            "Specify directory where files should be written to. "
            "The directory is created if required."
        ),
        metavar=("DIRECTORY"),
        type=Path,
    )
    parser.add_argument(
        "--outputformat",
        help=(
            "An optionally-provided output format for RDF files. Only relevant in "
            "Excel-to-RDf conversions. (default: turtle)"
        ),
        required=False,
        choices=["turtle", "xml", "json-ld"],
        default="turtle",
    )
    parser.add_argument(
        "-t",
        "--template",
        help=(
            "An optionally-provided xlsx-template file to be used in "
            "SKOS -> xlsx conversion."
        ),
        type=Path,
        metavar=("FILE"),
    )
    parser.add_argument(
        "VOCAB",
        nargs=1,
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=convert)


def add_check_subparser(subparsers, options):
    """Validation and checks of xlsx files, SKOS file and directory usage in CI."""

    parser = subparsers.add_parser(
        "check",
        description=(
            "Perform checks of vocabulary files in xlsx or in SKOS/turtle format."
            "You can also validate the state of directories in a CI vocabulary pipeline."
        ),
        help="Check vocabularies or validate vocabulary pipelines.",
        **options,
    )
    parser.add_argument(
        "--ci",
        nargs=1,
        metavar=("EXISTING",),
        type=Path,
        help="Perform checks on EXISTING and VOCAB directories in CI pipeline.",
    )
    parser.add_argument(
        "-p",
        "--profile",
        help=(
            "A token for a SHACL profile to check against. To list the supported "
            "profiles and their corresponding tokens run the program with the "
            'flag --listprofiles. (default: "vocpub")'
        ),
        default="vocpub",
    )
    parser.add_argument(
        "--fail_at_level",
        help=(
            "The minimum level which fails SHACL validation: 1-info, 2-warning, 3-violation "
            "(default: 1-info)"
        ),
        default=1,
        type=int,
        choices=[1, 2, 3],
    )
    parser.add_argument(
        "--listprofiles",
        help=(
            "List all vocabulary profiles that this converter supports "
            "indicating both their URI and the short token to use with the "
            "-p (--profile) flag."
        ),
        action="store_true",
    )
    parser.add_argument(
        "VOCAB",
        nargs="?",
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=check)


def add_docs_subparser(subparsers, options):
    """HTML documentation generation for SKOS vocabulary from rdf-format."""
    parser = subparsers.add_parser(
        "docs",
        description="Generate HTML documentation.",
        help="Generate HTML documentation.",
        **options,
    )
    parser.add_argument(
        "-O",
        "--outdir",
        help=(
            "Specify directory where files should be written to. "
            "The directory is created if required."
        ),
        metavar=("DIRECTORY"),
        type=Path,
    )
    parser.add_argument(
        "--style",
        help="Select style of html documentation. (default: pylode)",
        choices=("pylode", "ontospy"),
        type=str,
        required=False,
    )
    parser.add_argument(
        "VOCAB",
        nargs=1,
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=docs)


def main_cli(args=None):
    """Setup CLI app and run commands based on args."""

    # Create root parser for cli app
    parser = create_root_parser()

    subparsers = parser.add_subparsers(
        title="Subcommands",
        dest="subcommand",
        description="Get help for commands with voc4cat-ng COMMAND --help",
        # help="The following sub-commands are available:",
    )
    # Create parser to share some options between subparsers. We cannot use the
    # root parser for this because it includes the sub-commands and their help.
    common_options_parser = create_common_options_parser()

    # Create the subparsers with some common options
    common_options = {
        "parents": [common_options_parser],
        "formatter_class": DecentFormatter,
    }
    add_transform_subparser(subparsers, common_options)
    add_convert_subparser(subparsers, common_options)
    add_check_subparser(subparsers, common_options)
    add_docs_subparser(subparsers, common_options)

    if not args:
        parser.print_help()

    # Parse the command-line arguments
    #   pars_args will call sys.exit(2) if invalid commands are given.
    #   For Py>=3.9 this can be changed https://docs.python.org/3/library/argparse.html#exit-on-error
    args = parser.parse_args()
    args.func(args)


def run_cli_app(args=None):
    """Entry point for running the cli app."""
    if args is None:
        args = sys.argv[1:]

    setup_logging()

    try:
        main_cli(args)
    except Voc4catError:
        logger.exception("Terminating with Voc4cat error.")
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error.")
        sys.exit(3)  # value 2 is used by argparse for invalid args.


if __name__ == "__main__":
    run_cli_app(sys.argv[1:])
