"""New cleaner command line interface for voc4cat with subcommands."""

import argparse
import logging
import os.path
import sys
import textwrap
from pathlib import Path

from voc4cat import __version__, config, setup_logging
from voc4cat.check import check
from voc4cat.checks import Voc4catError
from voc4cat.convert import DEFAULT_PROFILE, convert
from voc4cat.docs import docs
from voc4cat.gen_template import template_cmd
from voc4cat.transform import transform
from voc4cat.utils import ConversionError

logger = logging.getLogger(__name__)


def process_common_options(args, raw_args):
    # set up output directory
    outdir = getattr(args, "outdir", None)
    if outdir is not None and os.path.isfile(outdir):
        msg = "Outdir must be a directory but it is a file."
        logger.error(msg)
        raise Voc4catError(msg)
    if outdir is not None and not os.path.isdir(outdir):
        outdir.mkdir(exist_ok=True, parents=True)

    # set up logging
    loglevel = logging.INFO + (args.quieter - args.verboser) * 10
    logfile = args.logfile
    if logfile is None:
        setup_logging(loglevel)
    else:
        logfile.parents[0].mkdir(exist_ok=True, parents=True)
        setup_logging(loglevel, logfile)

    logger.info("Executing cmd: voc4cat %s", " ".join(raw_args))
    logger.debug("Processing common options.")

    # load config
    if args.config is not None:
        if args.config.exists():
            config.load_config(config_file=Path(args.config))
        else:
            msg = "Config file not found at: %s"
            logger.error(msg, args.config)
            raise Voc4catError(msg % args.config)

    # check VOCAB (only for commands where VOCAB is a Path to existing file/dir)
    if args.VOCAB is None:
        return
    if isinstance(args.VOCAB, Path) and not args.VOCAB.exists():
        msg = "File/dir not found: %s"
        logger.error(msg, args.VOCAB)
        raise Voc4catError(msg % args.VOCAB)


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
            if not line.strip():  # pragma: no cover
                continue
            indent = " " * (len(line) - len(line.lstrip()))
            lines.extend(
                textwrap.fill(line, width, subsequent_indent=indent).splitlines()
            )
        return lines


def root_cmd(args):
    if args.version:  # pragma: no cover
        print(f"voc4cat {__version__}")


def create_root_parser():
    parser = argparse.ArgumentParser(
        prog="voc4cat",
        description=(
            "A command-line tool to support using Excel (xlsx) to edit and "
            "maintain SKOS (turtle/rdf) vocabularies."
        ),
        allow_abbrev=False,
        formatter_class=DecentFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        help="The version of voc4cat command line interface.",
        action="store_true",
    )
    parser.set_defaults(func=root_cmd)
    return parser


def create_common_options_parser():
    parser = argparse.ArgumentParser(
        prog="voc4cat",
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
        help="More verbose output. Repeat to increase verbosity (-vv or -vvv).",
    )
    group.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        dest="quieter",
        help="Less verbose output. Repeat to reduce verbosity (-qq or -qqq).",
    )
    parser.add_argument(
        "--config",
        help=('Path to config file (typically "idranges.toml").'),
        type=Path,
        required=False,
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
        "-l",
        "--logfile",
        help=(
            "Activate logging to a file at given path. "
            "The path will be created if it is not existing."
        ),
        type=Path,
    )
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
    skosopt = parser.add_argument_group("SKOS options")
    skosopt_meg = skosopt.add_mutually_exclusive_group()
    skosopt_meg.add_argument(
        "--split",
        help=(
            "Convert a single SKOS turtle file to a set of turtle files with "
            "one class per file. The diff-optimized long turtle format is used. "
            "Combine with --inplace to remove the source file."
        ),
        action="store_true",
    )
    skosopt_meg.add_argument(
        "--join",
        help=(
            "Join a directory of turtles files representing a split SKOS "
            "vocabulary to a single turtle file. Combine with --inplace "
            "to remove the source directory and files."
        ),
        action="store_true",
    )
    skosopt.add_argument(
        "--prov-from-git",
        help=(
            "Add dct:created and dct:modified dates to split turtle files "
            "based on git history. dct:created is added only if missing; "
            "dct:modified is updated if different from git. "
            "Requires files to be tracked in git."
        ),
        action="store_true",
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
    skosopt = parser.add_argument_group("Creating SKOS")
    skosopt.add_argument(
        "--outputformat",
        help=("An optionally-provided output format for RDF files. (default: turtle)"),
        required=False,
        choices=["turtle", "xml", "json-ld"],
        default="turtle",
    )
    skosopt.add_argument(
        "--from",
        dest="from_format",
        help=(
            "Source format version for RDF-to-RDF conversion. Use '043' to convert "
            "template 0.4.3 RDF to current RDF format. (default: auto - no conversion)"
        ),
        required=False,
        choices=["043", "auto"],
        default="auto",
    )
    xlsxopt = parser.add_argument_group("Creating Excel/xlsx")
    xlsxopt.add_argument(
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
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=convert)


def add_check_subparser(subparsers, options):
    """Validation and checks of xlsx files, SKOS file and directory usage in CI."""

    parser = subparsers.add_parser(
        "check",
        description=(
            "Perform checks of vocabulary files in xlsx or in SKOS/turtle format. "
            "You can also validate the state of directories in a CI vocabulary pipeline."
        ),
        help="Check vocabularies or validate vocabulary pipelines.",
        **options,
    )
    xlsxopt = parser.add_argument_group("Excel/xlsx validation")
    xlsxopt.add_argument(
        "--inplace",  # was "--no-warn"
        help=(
            "Annotate file(s) in place. Replaces the input file(s) with the annotated output file(s)."
        ),
        default=False,
        action="store_true",
    )
    shacl = parser.add_argument_group("RDF validation")
    shacl.add_argument(
        "-p",
        "--profile",
        help=(
            "A SHACL profile token or path to a profile file. "
            "If a file path with an RDF extension exists, it is used directly. "
            "Otherwise, treated as a bundled profile token. "
            "Run with --listprofiles to see available profiles. "
            f'(default: "{DEFAULT_PROFILE}")'
        ),
        default=DEFAULT_PROFILE,
    )
    shacl.add_argument(
        "--fail-at-level",
        help=(
            "The minimum level which fails SHACL validation: 1-info, 2-warning, 3-violation "
            "(default: 1-info)"
        ),
        default=1,
        type=int,
        choices=[1, 2, 3],
    )
    shacl.add_argument(
        "--listprofiles",
        help=(
            "List all vocabulary profiles that this converter supports "
            "indicating both their URI and the short token to use with the "
            "-p (--profile) flag."
        ),
        action="store_true",
    )
    shacl.add_argument(
        "--redundant-hierarchies",
        help=(
            "Detect redundant hierarchical relationships where a concept has "
            "skos:broader to both a parent and an ancestor of that parent."
        ),
        action="store_true",
        default=False,
    )
    workflow = parser.add_argument_group("Workflow options")
    workflow.add_argument(
        "--ci-pre",
        metavar=("INBOX",),
        type=Path,
        help=(
            "Perform consistency check on INBOX and VOCAB directories, e.g.\n"
            "- are too many vocabulary file in INBOX (if restricted via config)\n"
            "- do xlsx filenames in INBOX match SKOS file names in VOCAB"
        ),
    )
    workflow.add_argument(
        "--ci-post",
        metavar=("EXISTING",),
        type=Path,
        help=(
            "Validate if changes between EXISTING and new VOCAB directories "
            "are allowed."
        ),
    )
    parser.add_argument(
        "VOCAB",
        nargs="?",
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=check, _parser=parser)


def add_docs_subparser(subparsers, options):
    """HTML documentation generation for SKOS vocabulary from rdf-format."""
    parser = subparsers.add_parser(
        "docs",
        description="Generate HTML documentation.",
        help="Generate HTML documentation.",
        **options,
    )
    parser.add_argument(
        "--style",
        help="Select style of html documentation. (default: pylode)",
        choices=("pylode",),
        default="pylode",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--force",
        help=("Enforce overwriting files in output path."),
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "VOCAB",
        type=Path,
        help="Either the file to process or a directory with files to process.",
    )
    parser.set_defaults(func=docs)


def add_template_subparser(subparsers, options):
    """Generate blank vocabulary templates."""
    parser = subparsers.add_parser(
        "template",
        description="Generate blank vocabulary templates.",
        help="Generate blank vocabulary templates.",
        **options,
    )
    parser.add_argument(
        "--version",
        help='Template version to generate (default: "v1.0")',
        choices=["v1.0"],
        default="v1.0",
        dest="template_version",  # avoid conflict with root --version
    )
    parser.add_argument(
        "-t",
        "--template",
        help="An optionally-provided xlsx-template file to use as base.",
        type=Path,
        metavar="FILE",
    )
    parser.add_argument(
        "VOCAB",
        type=str,
        help="Vocabulary name used as the filename for the generated xlsx template.",
    )
    parser.set_defaults(func=template_cmd)


def main_cli(raw_args=None):
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
    add_template_subparser(subparsers, common_options)

    if not raw_args:
        parser.print_help()
        return

    # Parse the command-line arguments
    #   pars_args will call sys.exit(2) if invalid commands are given.
    args = parser.parse_args(raw_args)
    if hasattr(args, "config"):
        process_common_options(args, raw_args)
    args.func(args)


def run_cli_app(raw_args=None):
    """Entry point for running the cli app."""
    if raw_args is None:
        raw_args = sys.argv[1:]
    try:
        main_cli(raw_args)
    except (Voc4catError, ConversionError) as e:
        logger.error("Terminating with error: %s", e)  # noqa: TRY400
        sys.exit(1)
    except Exception:  # pragma: no cover
        logger.exception("Unexpected error.")
        sys.exit(3)  # value 2 is used by argparse for invalid args.


if __name__ == "__main__":
    run_cli_app(sys.argv[1:])
