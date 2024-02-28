import logging
import os
import shutil
from collections import defaultdict
from itertools import count, zip_longest
from pathlib import Path
from urllib.parse import urlsplit

import openpyxl
from openpyxl.styles import Alignment
from rdflib import DCTERMS, OWL, RDF, SKOS, XSD, Graph, Literal

from voc4cat import config
from voc4cat.checks import Voc4catError
from voc4cat.dag_util import (
    dag_from_indented_text,
    dag_from_narrower,
    dag_to_narrower,
    dag_to_node_levels,
    get_concept_and_level_from_indented_line,
)
from voc4cat.utils import (
    EXCEL_FILE_ENDINGS,
    RDF_FILE_ENDINGS,
    adjust_length_of_tables,
    is_supported_template,
)

logger = logging.getLogger(__name__)


def extract_numeric_id_from_iri(iri):
    iri_path = urlsplit(iri).path
    reverse_id = []
    for char in reversed(iri_path):
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


def autoversion_cs(graph: Graph) -> Graph:
    """Set modified date and version if "requested" via environment variables."""
    if any(graph.triples((None, RDF.type, SKOS.ConceptScheme))):
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
    cs_graph.serialize(destination=vocab_dir.with_suffix(".ttl"), format="turtle")
    return cs_graph


def make_ids(
    fpath: Path, outfile: Path, search_prefix: str, start_id: int, base_iri=None
):
    """
    Replace all prefix:suffix CURIEs using IDs counting up from start_id

    If base_iri is None the new IRI is a concatenation of VOC_BASE_IRI and ID.
    If base_iri is given the new IRI is the concatenation of base_iri and ID.
    """
    logger.info("Replacing '%s' IRIs.", search_prefix)
    # Load in data_only mode to get cell values not formulas.
    wb = openpyxl.load_workbook(fpath, data_only=True)
    is_supported_template(wb)
    if base_iri is None:
        base_iri = wb["Concept Scheme"].cell(row=2, column=2).value
        if base_iri is None:
            base_iri = "https://example.org/"
            wb["Concept Scheme"].cell(row=2, column=2).value = base_iri
            logger.warning("No concept scheme IRI found, using https://example.org/")

    # TODO if config is set: Check that file name is in config
    voc_config = config.IDRANGES.vocabs.get(fpath.stem, {})
    id_length = voc_config.get("id_length", 7)

    id_gen = count(start_id)
    replaced_iris = {}
    # process primary iri column in both worksheets
    for sheet in ["Concepts", "Collections"]:
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=2):  # pragma: no branch
            if row[0].value:
                iri = str(row[0].value)
                if not iri.startswith(search_prefix):
                    continue
                if iri in replaced_iris:
                    iri_new = replaced_iris[iri]
                else:
                    iri_new = base_iri + f"{next(id_gen):0{id_length}d}"
                    msg = f"[{sheet}] Replaced CURIE {iri} by {iri_new}"
                    logger.debug(msg)
                    replaced_iris[iri] = iri_new
                row[0].value = iri_new

    # replace iri by new_iri in all columns where it might be referenced
    cols_to_update = {
        "Concepts": [6],
        "Collections": [3],
        "Additional Concept Features": [0, 1, 2, 3, 4, 5],
    }
    for sheet, cols in cols_to_update.items():
        ws = wb[sheet]
        # iterate over first two columns; skip header and start from row 3
        for row in ws.iter_rows(min_row=3, max_col=1 + max(cols)):  # pragma: no branch
            # stop processing a sheet after 3 empty rows
            for col in cols:
                if row[col].value:
                    iris = [iri.strip() for iri in str(row[col].value).split(",")]
                    count_new_iris = [1 for iri in iris if iri in replaced_iris].count(
                        1
                    )
                    if count_new_iris:
                        new_iris = [replaced_iris.get(iri, iri) for iri in iris]
                        msg = (
                            f"[{sheet}] Replaced {count_new_iris} CURIs "
                            f"in cell {row[col].coordinate}"
                        )
                        logger.debug(msg)
                        row[col].value = ", ".join(new_iris)
                    # subsequent_empty_rows = 0

    wb.save(outfile)
    logger.info("Saved updated file as %s", outfile)


def hierarchy_from_indent(fpath, outfile, sep):
    """
    Convert indentation hierarchy of concepts to children-URI form.

    If separator character(s) are given they will be replaced with
    the xlsx default indent. This is also the default if sep is None.
    """
    logger.info("Reading concepts from file %s", fpath)
    # Load in data_only mode to get cell values not formulas.
    wb = openpyxl.load_workbook(fpath, data_only=True)
    is_supported_template(wb)
    # process both worksheets
    subsequent_empty_rows = 0
    ws = wb["Concepts"]
    concepts_indented = []
    row_by_iri = defaultdict(dict)
    # read concepts, determine their indentation level, then clear indentation
    col_last = 9
    max_row = 0
    for row in ws.iter_rows(min_row=3, max_col=col_last):  # pragma: no branch
        iri = row[0].value
        if iri and row[1].value:
            row_no = row[0].row
            lang = row[2].value

            if sep is None:  # xlsx indentation
                level = int(row[1].alignment.indent)
                ws.cell(row_no, column=2).alignment = Alignment(indent=0)
            else:
                descr, level = get_concept_and_level_from_indented_line(
                    row[1].value, sep=sep
                )
                ws.cell(row_no, column=2).value = descr
                ws.cell(row_no, column=2).alignment = Alignment(indent=0)
            concepts_indented.append(level * " " + iri)

            if iri in row_by_iri:  # merge needed
                # compare fields, merge if one is empty, error if different values
                new_data = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
                old_data = row_by_iri[iri].get(lang, [None] * (len(new_data)))
                merged = []
                for old, new in zip(old_data, new_data, strict=True):
                    if (old and new) and (old != new):
                        msg = f"Cannot merge rows for {iri}. Resolve differences manually."
                        raise Voc4catError(msg)
                    merged.append(old if old else new)
                row_by_iri[iri][lang] = merged
            else:
                row_by_iri[iri][lang] = [
                    ws.cell(row_no, col_no).value for col_no in range(2, col_last)
                ]
            max_row = row_no

        # stop processing a sheet after 3 empty rows
        elif subsequent_empty_rows < 2:  # noqa: PLR2004
            subsequent_empty_rows += 1
        else:
            subsequent_empty_rows = 0
            break

    term_dag = dag_from_indented_text("\n".join(concepts_indented))
    children_by_iri = dag_to_narrower(term_dag)

    # Write rows to xlsx-file, write translation directly after each concept.
    col_children_iri = 7
    row = 3
    for iri in children_by_iri:
        for lang in row_by_iri[iri]:
            ws.cell(row, column=1).value = iri
            for col, stored_value in zip_longest(
                range(2, col_last), row_by_iri[iri][lang]
            ):
                ws.cell(row, column=col).value = stored_value
            ws.cell(row, column=col_children_iri).value = ", ".join(
                children_by_iri[iri]
            )
            row += 1

    while row <= max_row:
        # Clear remaining rows.
        for col in range(1, col_last):
            ws.cell(row, column=col).value = None
        row += 1

    wb.save(outfile)
    logger.info("Saved file with children-IRI hierarchy as %s", outfile)


def hierarchy_to_indent(fpath, outfile, sep):
    """
    Convert concept hierarchy in children-URI form to indentation.

    If separator character(s) are given they will be used.
    If sep is None, xlsx default indent will be used.
    """
    logger.info("Reading concepts from file %s", fpath)
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    ws = wb["Concepts"]

    concept_children_dict = {}
    subsequent_empty_rows = 0
    row_by_iri = defaultdict(dict)
    col_last = 9
    # read all IRI, preferred labels, children_uris from the sheet
    for rows_total, row in enumerate(  # pragma: no branch
        ws.iter_rows(min_row=3, max_col=col_last, values_only=True)
    ):
        if row[0] and row[1]:
            iri = row[0]
            lang = row[2]
            children_uris = [] if not row[6] else [c.strip() for c in row[6].split(",")]
            # We need to check if ChildrenIRI, Provenance & Source Vocab URL
            # are consistent across languages since SKOS has no support for
            # per language statements. (SKOS-XL would add this)
            if iri in row_by_iri:  # merge needed
                # compare fields, merge if one is empty, error if different values
                new_data = [row[col_no] for col_no in range(6, col_last)]
                old_data = row_by_iri[iri][next(iter(row_by_iri[iri].keys()))][5:]
                merged = []
                for old, new in zip(old_data, new_data):
                    if (old and new) and (old != new):
                        msg = f'Merge conflict for concept {iri}. New: "{new}" - Before: "{old}"'
                        raise Voc4catError(msg)
                    merged.append(old if old else new)
                row_by_iri[iri][lang] = [row[col] for col in range(1, 6)] + merged
            else:
                row_by_iri[iri][lang] = [row[col] for col in range(1, col_last)]
                concept_children_dict[iri] = children_uris

        # stop processing a sheet after 3 empty rows
        elif subsequent_empty_rows < 2:  # noqa: PLR2004
            subsequent_empty_rows += 1
        else:
            subsequent_empty_rows = 0
            rows_total -= 2  # noqa: PLW2901
            break
    else:
        pass

    term_dag = dag_from_narrower(concept_children_dict)
    concept_levels = dag_to_node_levels(term_dag)

    # Write indented rows to xlsx-file but
    # 1 - each concept translation only once
    # 2 - details only once per concept and language
    iri_written = []
    row = 3
    for iri, level in concept_levels:
        for transl_no, lang in enumerate(row_by_iri[iri]):
            if transl_no and (iri, lang) in iri_written:  # case 1
                continue
            ws.cell(row, 1).value = iri
            concept_text = row_by_iri[iri][lang][0]
            if sep is None:
                ws.cell(row, 2).value = concept_text
                ws.cell(row, 2).alignment = Alignment(indent=level)
            else:
                ws.cell(row, 2).value = sep * level + concept_text
                ws.cell(row, 2).alignment = Alignment(indent=0)
            ws.cell(row, 3).value = lang

            if (iri, lang) in iri_written:  # case 2
                for col, _ in zip_longest(
                    range(4, col_last + 1), row_by_iri[iri][lang][2:]
                ):
                    ws.cell(row, column=col).value = None
                row += 1
                continue

            for col, stored_value in zip_longest(
                range(4, col_last + 1), row_by_iri[iri][lang][2:]
            ):
                ws.cell(row, column=col).value = stored_value

            # clear children IRI column G (value & hyperlink have to cleared separately)
            ws.cell(row, column=7).value = None
            ws.cell(row, column=7).hyperlink = None

            row += 1
            iri_written.append((iri, lang))

    wb.save(outfile)
    logger.info("Saved file with indentation hierarchy as %s", outfile)


# ===== transform command & helpers to validate cmd options =====


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

    # Extend size (length) of tables in all sheets
    adjust_length_of_tables(outfile)


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
