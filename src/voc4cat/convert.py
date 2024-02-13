import logging
from itertools import chain
from pathlib import Path
from typing import Dict, Literal, Union

import pyshacl
from colorama import Fore, Style
from curies import Converter
from pydantic.error_wrappers import ValidationError
from pyshacl.pytypes import GraphLike
from rdflib import DCAT, DCTERMS, OWL, PROV, RDF, RDFS, SH, SKOS, Graph

from voc4cat import config, models, profiles
from voc4cat.checks import Voc4catError, validate_config_has_idrange
from voc4cat.convert_043 import create_prefix_dict, write_prefix_sheet
from voc4cat.convert_043 import (
    extract_concept_scheme as extract_concept_scheme_043,
)
from voc4cat.convert_043 import (
    extract_concepts_and_collections as extract_concepts_and_collections_043,
)
from voc4cat.utils import (
    EXCEL_FILE_ENDINGS,
    RDF_FILE_ENDINGS,
    ConversionError,
    adjust_length_of_tables,
    has_file_in_multiple_formats,
    is_supported_template,
    load_template,
    load_workbook,
)

TEMPLATE_VERSION = None

logger = logging.getLogger(__name__)


def validate_with_profile(
    data_graph: Union[GraphLike, str, bytes],
    profile="vocpub",
    error_level=1,
):
    if profile not in profiles.PROFILES:
        msg = "The profile chosen for conversion must be one of '{}'. 'vocpub' is default".format(
            "', '".join(profiles.PROFILES.keys())
        )
        raise Voc4catError(msg)
    allow_warnings = error_level > 1

    # validate the RDF file
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=str(Path(__file__).parent / "profile" / "vocpub-4.7.ttl"),
        allow_warnings=allow_warnings,
    )

    info_list = []
    warning_list = []
    violation_list = []

    for report in results_graph.subjects(RDF.type, SH.ValidationReport):
        for result in results_graph.objects(report, SH.result):
            result_dict = {}
            for p, o in results_graph.predicate_objects(result):
                if p == SH.focusNode:
                    result_dict["focusNode"] = str(o)
                elif p == SH.resultMessage:
                    result_dict["resultMessage"] = str(o)
                elif p == SH.resultSeverity:
                    result_dict["resultSeverity"] = str(o)
                elif p == SH.sourceConstraintComponent:
                    result_dict["sourceConstraintComponent"] = str(o)
                elif p == SH.sourceShape:
                    result_dict["sourceShape"] = str(o)
                elif p == SH.value:
                    result_dict["value"] = str(o)
            result_message_formatted = format_log_msg(result_dict)
            result_message = format_log_msg(
                result_dict, colored=True
            )  # output to screen
            if result_dict["resultSeverity"] == str(SH.Info):
                logger.info(result_message_formatted)
                info_list.append(result_message)
            elif result_dict["resultSeverity"] == str(SH.Warning):
                logger.warning(result_message_formatted)
                warning_list.append(result_message)
            elif result_dict["resultSeverity"] == str(SH.Violation):
                logger.error(result_message_formatted)
                violation_list.append(result_message)

    error_messages = []

    if error_level == 3:  # noqa: PLR2004
        error_messages = violation_list
    elif error_level == 2:  # noqa: PLR2004
        error_messages = warning_list + violation_list
    else:  # error_level == 1
        error_messages = info_list + warning_list + violation_list

    if len(error_messages) > 0:
        msg = f"The file you supplied is not valid according to the {profile} profile."
        raise ConversionError(msg)


def excel_to_rdf(
    file_to_convert_path: Path,
    output_file_path: Path | None = None,
    output_format: Literal["turtle", "xml", "json-ld"] = "turtle",
    output_type: Literal["file", "graph"] = "file",
) -> None:
    """Converts an Excel workbook to a SKOS vocabulary file"""
    wb = load_workbook(file_to_convert_path)
    is_supported_template(wb)
    vocab_name = file_to_convert_path.stem.lower()
    # If non-default config is present, verify that at least one id_range defined.
    if not config.IDRANGES.default_config:
        validate_config_has_idrange(vocab_name)

    models.reset_curies(create_prefix_dict(wb["Prefix Sheet"]))

    # template_version == "0.4.3":
    try:
        sheet = wb["Concept Scheme"]
        concept_sheet = wb["Concepts"]
        additional_concept_sheet = wb["Additional Concept Features"]
        collection_sheet = wb["Collections"]
        prefix_sheet = wb["Prefix Sheet"]
        prefix_converter_xlsx = Converter.from_prefix_map(
            create_prefix_dict(prefix_sheet)
        )

        concepts, collections = extract_concepts_and_collections_043(
            concept_sheet,
            additional_concept_sheet,
            collection_sheet,
            prefix_converter_xlsx,
            vocab_name,
        )
        cs = extract_concept_scheme_043(
            sheet,
            prefix_converter_xlsx,
        )
    except ValidationError as exc:
        msg = f"ConceptScheme processing error: {exc}"
        raise ConversionError(msg) from exc

    # Build the total vocab
    vocab = models.Vocabulary(
        concept_scheme=cs, concepts=concepts, collections=collections
    )
    vocab_graph = vocab.to_graph()

    if output_type == "graph":  # only used in tests
        return vocab_graph

    # output_format == "file":
    if output_file_path is not None:
        dest = output_file_path
    else:
        if output_format == "xml":
            suffix = ".rdf"
        elif output_format == "json-ld":
            suffix = ".json-ld"
        else:
            suffix = ".ttl"
        dest = file_to_convert_path.with_suffix(suffix)
    vocab_graph.serialize(destination=str(dest), format=output_format)
    return None


def rdf_to_excel(
    file_to_convert_path: Path,
    output_file_path: Path | None = None,
    template_file_path: Path | None = None,
) -> None:
    if not file_to_convert_path.name.endswith(tuple(RDF_FILE_ENDINGS.keys())):
        msg = "Files for conversion to Excel must end with one of the RDF file formats: '{}'".format(
            "', '".join(RDF_FILE_ENDINGS.keys())
        )
        raise ValueError(msg)

    # the RDF is valid so extract data and create Excel
    g = Graph().parse(
        str(file_to_convert_path), format=RDF_FILE_ENDINGS[file_to_convert_path.suffix]
    )
    # Update graph with prefix-mappings of the vocabulary
    vocab_name = file_to_convert_path.stem.lower()
    # If non-default config is present, verify that at least one id_range defined.
    if not config.IDRANGES.default_config:
        validate_config_has_idrange(vocab_name)

    if template_file_path is None:
        wb = load_template(file_path=(Path(__file__).parent / "blank_043.xlsx"))
    else:
        wb = load_template(file_path=template_file_path)

    holder = {"hasTopConcept": [], "provenance": None}
    for s in g.subjects(RDF.type, SKOS.ConceptScheme):
        holder["uri"] = str(s)
        for p, o in g.predicate_objects(s):
            if p == SKOS.prefLabel:
                holder["title"] = o.toPython()
            elif p == SKOS.definition:
                holder["description"] = str(o)
            elif p == DCTERMS.created:
                holder["created"] = o.toPython()
            elif p == DCTERMS.modified:
                holder["modified"] = o.toPython()
            elif p == DCTERMS.creator:
                holder["creator"] = (
                    models.ORGANISATIONS_INVERSE[o]
                    if models.ORGANISATIONS_INVERSE.get(o)
                    else str(o)
                )
            elif p == DCTERMS.publisher:
                holder["publisher"] = (
                    models.ORGANISATIONS_INVERSE[o]
                    if models.ORGANISATIONS_INVERSE.get(o)
                    else str(o)
                )
            elif p == OWL.versionInfo:
                holder["versionInfo"] = str(o)
            elif p in [
                DCTERMS.source,
                DCTERMS.provenance,
                PROV.wasDerivedFrom,
                SKOS.historyNote,
            ]:
                holder["provenance"] = str(o)
            elif p == SKOS.hasTopConcept:
                holder["hasTopConcept"].append(str(o))
            elif p == DCAT.contactPoint:
                holder["custodian"] = str(o)
            elif p == RDFS.seeAlso:
                holder["pid"] = str(o)

    cs = models.ConceptScheme(
        uri=holder["uri"],
        title=holder["title"],
        description=holder["description"],
        created=holder["created"],
        modified=holder["modified"],
        creator=holder["creator"],
        publisher=holder["publisher"],
        version=holder.get("versionInfo", None),
        provenance=holder.get("provenance", None),
        custodian=holder.get("custodian", None),
        pid=holder.get("pid", None),
    )
    cs.to_excel(wb)

    # infer inverses
    for s, o in g.subject_objects(SKOS.broader):
        g.add((o, SKOS.narrower, s))

    row_no_features, row_no_concepts = 3, 3
    for s in g.subjects(RDF.type, SKOS.Concept):
        holder = {
            "uri": str(s),
            "pref_label": [],
            "pl_language_code": [],
            "definition": [],
            "def_language_code": [],
            "children": [],
            "alt_labels": [],
            "source_vocab": None,
            "provenance": None,
            "related_match": [],
            "close_match": [],
            "exact_match": [],
            "narrow_match": [],
            "broad_match": [],
        }
        for p, o in g.predicate_objects(s):
            if p == SKOS.prefLabel:
                holder["pref_label"].append(o.toPython())
                holder["pl_language_code"].append(o.language)
            elif p == SKOS.definition:
                holder["definition"].append(str(o))
                holder["def_language_code"].append(o.language)
            elif p == SKOS.narrower:
                holder["children"].append(str(o))
            elif p == SKOS.altLabel:
                holder["alt_labels"].append(str(o))
            elif p == RDFS.isDefinedBy:
                holder["source_vocab"] = str(o)
            elif p in [
                DCTERMS.source,
                DCTERMS.provenance,
                PROV.wasDerivedFrom,
                SKOS.historyNote,
            ]:
                holder["provenance"] = str(o)
            elif p == SKOS.relatedMatch:
                holder["related_match"].append(str(o))
            elif p == SKOS.closeMatch:
                holder["close_match"].append(str(o))
            elif p == SKOS.exactMatch:
                holder["exact_match"].append(str(o))
            elif p == SKOS.narrowMatch:
                holder["narrow_match"].append(str(o))
            elif p == SKOS.broadMatch:
                holder["broad_match"].append(str(o))

        row_no_concepts = models.Concept(
            uri=holder["uri"],
            pref_label=holder["pref_label"],
            pl_language_code=holder["pl_language_code"],
            definition=holder["definition"],
            def_language_code=holder["def_language_code"],
            children=holder["children"],
            alt_labels=holder["alt_labels"],
            source_vocab=holder["source_vocab"],
            provenance=holder["provenance"],
            related_match=holder["related_match"],
            close_match=holder["close_match"],
            exact_match=holder["exact_match"],
            narrow_match=holder["narrow_match"],
            broad_match=holder["broad_match"],
            vocab_name=vocab_name,
        ).to_excel(wb, row_no_features, row_no_concepts)
        row_no_features += 1

    row_no = 3

    for s in g.subjects(RDF.type, SKOS.Collection):
        holder = {
            "uri": str(s),
            "members": [],
        }
        for p, o in g.predicate_objects(s):
            if p == SKOS.prefLabel:
                holder["pref_label"] = o.toPython()
            elif p == SKOS.definition:
                holder["definition"] = str(o)
            elif p == SKOS.member:
                holder["members"].append(str(o))
            elif p in [
                DCTERMS.source,
                DCTERMS.provenance,
                PROV.wasDerivedFrom,
                SKOS.historyNote,
            ]:
                holder["provenance"] = str(o)

        models.Collection(
            uri=holder["uri"],
            pref_label=holder["pref_label"],
            definition=holder["definition"],
            members=holder["members"],
            provenance=(
                holder["provenance"] if holder.get("provenance") is not None else None
            ),
            vocab_name=vocab_name,
        ).to_excel(wb, row_no)
        row_no += 1

    # Write the prefix_map used in the conversion to the prefix sheet.
    write_prefix_sheet(wb, config.curies_converter.prefix_map)

    if output_file_path is not None:
        dest = output_file_path
    else:
        dest = file_to_convert_path.with_suffix(".xlsx")
    wb.save(filename=dest)
    return dest


def format_log_msg(result: Dict, colored: bool = False) -> str:
    from rdflib.namespace import SH

    formatted_msg = ""
    message = f"""Validation Result in {result['sourceConstraintComponent'].split(str(SH))[1]} ({result['sourceConstraintComponent']}):
\tSeverity: sh:{result['resultSeverity'].split(str(SH))[1]}
\tSource Shape: <{result['sourceShape']}>
\tFocus Node: <{result['focusNode']}>
\tValue Node: <{result.get('value', '')}>
\tMessage: {result['resultMessage']}
"""
    if result["resultSeverity"] == str(SH.Info):
        formatted_msg = (
            f"INFO: {message}"
            if colored
            else Fore.BLUE + "INFO: " + Style.RESET_ALL + message
        )
    elif result["resultSeverity"] == str(SH.Warning):
        formatted_msg = (
            f"WARNING: {message}"
            if colored
            else Fore.YELLOW + "WARNING: " + Style.RESET_ALL + message
        )
    elif result["resultSeverity"] == str(SH.Violation):
        formatted_msg = (
            f"VIOLATION: {message}"
            if colored
            else Fore.RED + "VIOLATION: " + Style.RESET_ALL + message
        )
    return formatted_msg


# ===== convert command & helpers to validate cmd options =====


def _check_convert_args(args):
    if args.template is not None:
        msg = ""
        if not args.template.exists():
            msg = f"Template file not found: {args.template}"
        elif args.template.suffix.lower() not in EXCEL_FILE_ENDINGS:
            msg = 'Template file must be of type ".xlsx".'
        if msg:
            logging.error(msg)
            raise Voc4catError(msg)
    # Option outputformat is validated by argparse since its restricted by choices.

    # Add check if files of the same name are present in different formats.
    if args.VOCAB.is_dir():  # noqa: SIM102
        if duplicates := has_file_in_multiple_formats(args.VOCAB):
            msg = (
                "Files may only be present in one format. Found more than one "
                'format for: "%s"'
            )
            logger.error(msg, '", "'.join(duplicates))
            raise Voc4catError(msg % '", "'.join(duplicates))


def convert(args):
    logger.debug("Convert subcommand started!")

    _check_convert_args(args)

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]
    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    # convert xlsx and rdf files
    for file in chain(xlsx_files, rdf_files):
        logger.debug('Processing "%s"', file)
        outfile = file if args.outdir is None else args.outdir / file.name

        if file in xlsx_files:
            suffix = "ttl" if args.outputformat == "turtle" else args.outputformat
            output_file_path = outfile.with_suffix(f".{suffix}")
            excel_to_rdf(file, output_file_path, output_format=args.outputformat)
            logger.info("-> successfully converted to %s", output_file_path)
        elif file in rdf_files:
            output_file_path = outfile.with_suffix(".xlsx")
            rdf_to_excel(file, output_file_path, template_file_path=args.template)
            logger.info("-> successfully converted to %s", output_file_path)
            # Extend size (length) of tables in all sheets
            adjust_length_of_tables(output_file_path)
