import logging
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import DCTERMS, OWL, RDF, SDO, SKOS, XSD, Graph, Literal

from voc4cat.checks import Voc4catError
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS

logger = logging.getLogger(__name__)


def extract_numeric_id_from_iri(iri):
    iri_path = urlsplit(iri).path
    reverse_id = []
    for char in reversed(iri_path):  # pragma: no branch
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

    The ids are used as filenames. Schema:Person and schema:Organization entities
    are included in the concept_scheme.ttl file.
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
                # Include schema:Person and schema:Organization entities
                # in the concept scheme file (metadata related to scheme)
                for entity_type in [SDO.Person, SDO.Organization]:
                    for entity_iri in vocab_graph.subjects(RDF.type, entity_type):
                        tmp_graph += vocab_graph.triples((entity_iri, None, None))
                outfile = outdir / "concept_scheme.ttl"
            else:
                outfile = outdir / f"{id_part}.ttl"
            tmp_graph.serialize(destination=outfile, format="longturtle")
        logger.debug("-> wrote %i %ss-file(s).", len(qresults), skos_class)


def autoversion_cs(graph: Graph) -> Graph:
    """Set modified date and version if "requested" via environment variables."""
    if any(graph.triples((None, RDF.type, SKOS.ConceptScheme))):  # pragma: no branch
        cs, _, _ = next(graph.triples((None, RDF.type, SKOS.ConceptScheme)))
    if os.getenv("VOC4CAT_MODIFIED") is not None:
        graph.remove((None, DCTERMS.modified, None))
        date_modified = os.getenv("VOC4CAT_MODIFIED")
        graph.add((cs, DCTERMS.modified, Literal(date_modified, datatype=XSD.date)))
    if os.getenv("VOC4CAT_VERSION") is not None:
        version = os.getenv("VOC4CAT_VERSION")
        if version is not None and not version.startswith("v"):
            msg = 'Invalid environment variable VOC4CAT_VERSION "%s". Version must start with letter "v".'
            logger.error(msg, version)
            raise Voc4catError(msg % version)
        graph.remove((None, OWL.versionInfo, None))
        graph.add(
            (cs, OWL.versionInfo, Literal(version)),
        )
    return graph


def join_split_turtle(vocab_dir: Path) -> Graph:
    """Join split turtle files back into a single graph.

    The schema:Person and schema:Organization entities are included in
    concept_scheme.ttl and will be joined automatically.
    """
    # Search recursively all turtle files belonging to the concept scheme
    turtle_files = vocab_dir.rglob("*.ttl")
    # Create an empty RDF graph to hold the concept scheme
    cs_graph = Graph()
    # Load each turtle file into a separate graph and merge it into the concept scheme graph
    for file in turtle_files:
        graph = Graph().parse(file, format="turtle")
        # Set modified date if "requested" via environment variable.
        if file.name == "concept_scheme.ttl" or any(
            graph.triples((None, RDF.type, SKOS.ConceptScheme))
        ):
            graph = autoversion_cs(graph)
        cs_graph += graph

    return cs_graph


# ===== transform command & helpers to validate cmd options =====


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
        logger.info("-> wrote split vocabulary to: %s", vocab_dir)
        if args.inplace:
            logger.debug("-> going to remove %s", file)
            file.unlink()
    else:
        logger.debug("-> nothing to do for rdf files!")


def transform(args):
    logger.debug("Transform subcommand started!")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]

    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    if args.VOCAB.is_file() and (len(xlsx_files) + len(rdf_files)) == 0:
        logger.warning("Unsupported filetype: %s", args.VOCAB)

    if args.join:
        rdf_dirs = [d for d in Path(args.VOCAB).iterdir() if any(d.glob("*.ttl"))]
    else:
        rdf_dirs = []

    for file in xlsx_files:
        logger.debug('Processing "%s"', file)
        logger.debug("-> nothing to do for xlsx files!")

    for file in rdf_files:
        logger.debug('Processing "%s"', file)
        _transform_rdf(file, args)

    for rdf_dir in rdf_dirs:
        logger.debug('Processing rdf files in "%s"', rdf_dir)
        # The if..else is not required now. It is a frame for future additions.
        if args.join:
            vocab_graph = join_split_turtle(rdf_dir)
            dest = (
                (args.outdir / rdf_dir.name).with_suffix(".ttl")
                if args.outdir
                else rdf_dir.with_suffix(".ttl")
            )
            vocab_graph.serialize(destination=str(dest), format="turtle")
            logger.info("-> joined vocabulary into: %s", dest)
            if args.inplace:
                logger.debug("-> going to remove %s", rdf_dir)
                shutil.rmtree(rdf_dir, ignore_errors=True)
        else:  # pragma: no cover
            logger.debug("-> nothing to do!")
