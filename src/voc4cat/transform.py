import logging
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import Graph
from rdflib.namespace import SKOS

from voc4cat.checks import Voc4catError
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS
from voc4cat.wrapper import hierarchy_from_indent, hierarchy_to_indent, make_ids

logger = logging.getLogger(__name__)


def extract_numeric_id_from_iri(iri):
    iri_path = urlsplit(iri).path
    reverse_id = []
    for char in reversed(iri_path):  # pragma: no cover
        if char.isdigit():
            reverse_id.append(char)
        elif char == "/":
            continue
        else:
            break
    return "".join(reversed(reverse_id))


def write_split_turtle(vocab_graph: Graph, outdir: Path) -> None:
    """
    Write each concept, collection and concept scheme to a separate turtle file.

    The ids are used as filenames.
    """
    outdir.mkdir(exist_ok=True)
    query = "SELECT ?iri WHERE {?iri a %s.}"

    for skos_class in ["skos:Concept", "skos:Collection", "skos:ConceptScheme"]:
        qresults = vocab_graph.query(query % skos_class, initNs={"skos": SKOS})
        # Iterate over search results and write each concept, collection and
        # concept scheme to a separate turtle file using id as filename.
        for qresult in qresults:
            iri = qresult["iri"]
            tmp_graph = Graph()
            tmp_graph += vocab_graph.triples((iri, None, None))
            id_part = extract_numeric_id_from_iri(iri)
            if skos_class == "skos:ConceptScheme":
                outfile = outdir / "concept_scheme.ttl"
            else:
                outfile = outdir / f"{id_part}.ttl"
            tmp_graph.serialize(destination=outfile, format="longturtle")
        logger.debug("-> wrote %i %ss-file(s).", len(qresults), skos_class)


def read_split_turtle(vocab_dir: Path) -> Graph:
    # Search recursively all turtle files belonging to the concept scheme
    turtle_files = vocab_dir.rglob("*.ttl")
    # Create an empty RDF graph to hold the concept scheme
    cs_graph = Graph()
    # Load each turtle file into a separate graph and merge it into the concept scheme graph
    for file in turtle_files:
        graph = Graph().parse(file, format="turtle")
        cs_graph += graph
    cs_graph.serialize(destination=vocab_dir.with_suffix(".ttl"), format="turtle")
    return cs_graph


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


def _transform_xlsx(file, args):
    if args.from_indent or args.to_indent:
        separator = _check_indent(args)
    if args.make_ids:
        prefix, base_iri, start_id = _check_make_ids_args(args)

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


def _transform_rdf(file, args):
    if args.split:
        vocab_graph = Graph().parse(str(file), format=RDF_FILE_ENDINGS[file.suffix])
        vocab_dir = (
            args.outdir / file.with_suffix("").name
            if args.outdir
            else file.with_suffix("")
        )
        vocab_dir.mkdir(exist_ok=True)
        write_split_turtle(vocab_graph, vocab_dir)
        logger.debug("-> wrote split vocabulary to: %s", vocab_dir)
        if args.inplace:
            logger.debug("-> going to remove %s", file)
            file.unlink()
    else:
        logger.debug("-> nothing to do for rdf files!")


def transform(args):
    logger.info("Transform subcommand started!")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]

    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    if args.VOCAB.is_file() and (len(xlsx_files) + len(rdf_files)) == 0:
        logger.warning("Unsupported filetype: %s", args.VOCAB)

    if args.join:
        rdf_dirs = [d for d in Path(args.VOCAB).iterdir() if any(d.glob("*.ttl"))]
    else:
        rdf_dirs = []

    # transform xlsx files (could be a separate function)
    for file in xlsx_files:
        _transform_xlsx(file, args)

    for file in rdf_files:
        logger.debug('Processing "%s"', file)
        _transform_rdf(file, args)

    for rdf_dir in rdf_dirs:
        logger.debug('Processing rdf files in "%s"', rdf_dir)
        # The if..else is not required now. It is a frame for future additions.
        if args.join:
            vocab_graph = read_split_turtle(rdf_dir)
            dest = (
                (args.outdir / rdf_dir).with_suffix(".ttl").name
                if args.outdir
                else rdf_dir.with_suffix(".ttl")
            )
            vocab_graph.serialize(destination=str(dest), format="turtle")
            logger.debug("-> joined vocabulary into: %s", dest)
            if args.inplace:
                logger.debug("-> going to remove %s", rdf_dir)
                shutil.rmtree(rdf_dir, ignore_errors=True)
        else:  # pragma: no cover
            logger.debug("-> nothing to do!")
