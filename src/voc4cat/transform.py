import logging
from pathlib import Path

from voc4cat.checks import Voc4catError
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS
from voc4cat.wrapper import hierarchy_from_indent, hierarchy_to_indent, make_ids

logger = logging.getLogger(__name__)


def _check_make_ids_args(args):
    """Validate make_ids arguments"""
    try:
        start_id = int(args.make_ids[1])
        msg = "" if start_id > 0 else "Start ID must be greater than zero."
    except ValueError:
        msg = "Start ID must be an integer number."
    if msg:
        logger.error(msg)
        raise Voc4catError(msg)
    if ":" in args.make_ids[0]:
        prefix, base_iri = args.make_ids[0].split(":", 1)
        if not base_iri.strip().startswith("http"):
            msg = 'The base_iri must be in IRI-form and start with "http".'
            logging.error(msg)
            raise Voc4catError(msg)
        base_iri = base_iri.strip()
    else:
        prefix, base_iri = args.make_ids[0], None
    return prefix.strip(), base_iri, start_id


def _check_indent(args):
    if args.indent is None or args.indent.lower() == "xlsx":
        # xlsx's default indent / openpyxl.styles.Alignment(indent=0)
        separator = None
    elif not len(args.indent):
        msg = "Setting the indent separator to zero length is not allowed."
        logging.error(msg)
        raise Voc4catError(msg)
    else:
        separator = args.indent
    return separator


def transform(args):
    logger.info("Transform subcommand started!")

    if args.from_indent or args.to_indent:
        separator = _check_indent(args)

    if args.make_ids:
        prefix, base_iri, start_id = _check_make_ids_args(args)

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]
    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]
    if args.VOCAB.is_file() and (len(xlsx_files) + len(rdf_files)) == 0:
        logger.warning("Unsupported filetype: %s", args.VOCAB)

    # transform xlsx files (could be a separate function)
    for file in xlsx_files:
        logger.debug('Processing "%s"', file)
        outfile = file if args.outdir is None else args.outdir / file.name
        any_action = any(
            (args.from_indent, args.to_indent, args.make_ids),
        )
        if outfile == file and not args.inplace and any_action:
            logger.warning(
                'This command will overwrite the existing file "%s".'
                'Use the flag "--inplace" to enforce replacement or '
                'supply an output directory with flag "--outdir".',
                file,
            )
            return
        if args.from_indent:
            hierarchy_from_indent(file, outfile, separator)
        elif args.to_indent:
            hierarchy_to_indent(file, outfile, separator)
        elif args.make_ids:
            make_ids(file, outfile, prefix, start_id, base_iri)
        else:
            logger.debug("-> nothing to do for xlsx files!")

    for file in rdf_files:
        logger.debug('Processing "%s"', file)
        logger.debug("-> nothing to do for rdf files!")
