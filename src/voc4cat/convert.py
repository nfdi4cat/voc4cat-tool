import logging
from itertools import chain
from pathlib import Path

import pyshacl
from colorama import Fore, Style
from pyshacl.pytypes import GraphLike
from rdflib import RDF, SH

from voc4cat import config
from voc4cat.checks import Voc4catError
from voc4cat.convert_043 import convert_rdf_043_to_v1
from voc4cat.convert_v1 import (
    excel_to_rdf_v1,
    rdf_to_excel_v1,
)
from voc4cat.models_v1 import CONCEPTS_SHEET_NAME
from voc4cat.utils import (
    EXCEL_FILE_ENDINGS,
    RDF_FILE_ENDINGS,
    ConversionError,
    has_file_in_multiple_formats,
    validate_template_sheets,
)
from voc4cat.xlsx_common import adjust_all_tables_length

logger = logging.getLogger(__name__)

PROFILE_DIR = Path(__file__).parent / "profile"
DEFAULT_PROFILE = "vp4cat-5.2"


def get_bundled_profiles() -> dict[str, Path]:
    """Return dict mapping profile tokens to their .ttl file paths."""
    profiles = {}
    for ttl_file in PROFILE_DIR.glob("*.ttl"):
        # Token is filename without extension
        token = ttl_file.stem
        profiles[token] = ttl_file
    return profiles


def resolve_profile(profile: str) -> tuple[Path, str]:
    """Resolve a profile argument to a file path and profile name.

    Args:
        profile: Either a bundled profile token (e.g., "vocpub-4.7") or
                 a path to a custom SHACL profile file.

    Returns:
        Tuple of (profile_path, profile_name).

    Raises:
        Voc4catError: If the profile file doesn't exist or token is unknown.
    """
    profile_as_path = Path(profile)

    # Check if it's a file path (exists and has RDF extension)
    if profile_as_path.suffix.lower() in RDF_FILE_ENDINGS and profile_as_path.exists():
        return profile_as_path, profile_as_path.stem

    # Otherwise treat as bundled profile token
    bundled = get_bundled_profiles()
    if profile in bundled:
        return bundled[profile], profile

    # If it looks like a file path but doesn't exist, give specific error
    if profile_as_path.suffix.lower() in RDF_FILE_ENDINGS:
        msg = f"SHACL profile file not found: {profile}"
        logger.error(msg)
        raise Voc4catError(msg)

    # Unknown profile token
    available = ", ".join(sorted(bundled.keys()))
    msg = f"Unknown profile '{profile}'. Available: {available}"
    raise Voc4catError(msg)


def validate_with_profile(
    data_graph: GraphLike | str | bytes,
    profile: str = DEFAULT_PROFILE,
    error_level: int = 1,
):
    """Validate data graph against a SHACL profile.

    Args:
        data_graph: The RDF data to validate.
        profile: Either a bundled profile token (e.g., "vocpub-4.7") or
                 a path to a custom SHACL profile file.
        error_level: Minimum severity level to treat as error (1=info, 2=warning, 3=violation).
    """
    allow_warnings = error_level > 1

    # Resolve profile to file path
    shacl_graph_path, _profile_name = resolve_profile(profile)
    shacl_graph_path = str(shacl_graph_path)

    # validate the RDF file
    _conforms, results_graph, _results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shacl_graph_path,
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

    # Log summary of validation results
    n_info = len(info_list)
    n_warn = len(warning_list)
    n_viol = len(violation_list)
    if n_info or n_warn or n_viol:
        logger.info(
            "Validation summary: %d info, %d warnings, %d violations",
            n_info,
            n_warn,
            n_viol,
        )

    error_messages = []

    if error_level == 3:  # noqa: PLR2004
        error_messages = violation_list
    elif error_level == 2:  # noqa: PLR2004
        error_messages = warning_list + violation_list
    else:  # error_level == 1
        error_messages = info_list + warning_list + violation_list

    if len(error_messages) > 0:
        msg = f"The vocabulary is not valid according to the {profile} profile."
        raise ConversionError(msg)


def format_log_msg(result: dict, colored: bool = False) -> str:
    formatted_msg = ""
    message = f"""Validation Result in {result["sourceConstraintComponent"].split(str(SH))[1]} ({result["sourceConstraintComponent"]}):
\tSeverity: sh:{result["resultSeverity"].split(str(SH))[1]}
\tSource Shape: <{result["sourceShape"]}>
\tFocus Node: <{result["focusNode"]}>
\tValue Node: <{result.get("value", "")}>
\tMessage: {result["resultMessage"]}
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


def _get_vocab_config(vocab_name: str) -> "config.Vocab | None":
    """Get vocab config for a vocabulary name if available.

    Returns the Vocab config from idranges.toml if:
    - A non-default config is loaded
    - The vocabulary name exists in the config

    Args:
        vocab_name: Name of the vocabulary (lowercase).

    Returns:
        Vocab config if available, None otherwise.
    """
    if config.IDRANGES.default_config:
        return None

    vocab = config.IDRANGES.vocabs.get(vocab_name)
    if vocab is None:
        return None

    return vocab


def _check_convert_args(args):
    if args.template is not None:
        if not args.template.exists():
            logger.warning(
                "Template file not found: %s. Continuing without template.",
                args.template,
            )
            args.template = None
        elif args.template.suffix.lower() not in EXCEL_FILE_ENDINGS:
            msg = 'Template file must be of type ".xlsx".'
            logger.error(msg)
            raise Voc4catError(msg)
        else:
            # Validate template doesn't contain reserved sheet names
            validate_template_sheets(args.template)
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

    # Check for --from option (043 to v1.0 RDF conversion)
    from_format = getattr(args, "from_format", "auto")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]
    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    # Handle --from 043: RDF-to-RDF conversion (043 -> v1.0)
    if from_format == "043":
        if xlsx_files:
            logger.warning(
                "XLSX files ignored when using --from 043 (RDF-to-RDF conversion only)"
            )

        # Require config for --from 043
        if config.IDRANGES.default_config:
            msg = (
                "--from 043 requires an idranges.toml config file. "
                "Use --config option to specify the config file."
            )
            raise Voc4catError(msg)

        # Check config version - require v1.0 for conversion
        if not config.IDRANGES.config_version:
            msg = (
                "Pre-v1.0 idranges.toml detected (missing 'config_version' field). "
                "Please update your config file to v1.0 format. "
                "See template at: src/voc4cat/templates/vocab/idranges.toml"
            )
            raise Voc4catError(msg)

        # Proceed with RDF conversion
        for file in rdf_files:
            logger.debug('Converting 043 RDF to v1.0: "%s"', file)
            outfile = file if args.outdir is None else args.outdir / file.name
            suffix = "ttl" if args.outputformat == "turtle" else args.outputformat
            output_file_path = outfile.with_suffix(f".{suffix}")

            # Get vocab config for metadata enrichment
            vocab_name = file.stem.lower()
            vocab_config = _get_vocab_config(vocab_name)

            convert_rdf_043_to_v1(
                file,
                output_file_path,
                output_format=args.outputformat,
                vocab_config=vocab_config,
            )
            logger.info("-> successfully converted to %s", output_file_path)
        return

    # Default behavior: xlsx <-> rdf conversion
    for file in chain(xlsx_files, rdf_files):
        logger.debug('Processing "%s"', file)
        outfile = file if args.outdir is None else args.outdir / file.name
        vocab_name = file.stem.lower()

        # Get vocab config for ConceptScheme metadata
        vocab_config = _get_vocab_config(vocab_name)

        if file in xlsx_files:
            if args.template is not None:
                logger.warning(
                    "Template option ignored for xlsx->RDF conversion (input: %s)",
                    file.name,
                )
            if vocab_config is None:
                msg = (
                    f"No idranges.toml config found for vocabulary '{vocab_name}'. "
                    "XLSX to RDF conversion requires vocab config for ConceptScheme metadata."
                )
                raise Voc4catError(msg)
            suffix = "ttl" if args.outputformat == "turtle" else args.outputformat
            output_file_path = outfile.with_suffix(f".{suffix}")
            excel_to_rdf_v1(
                file,
                output_file_path,
                output_format=args.outputformat,
                vocab_config=vocab_config,
            )
            logger.info("-> successfully converted to %s", output_file_path)
        elif file in rdf_files:
            output_file_path = outfile.with_suffix(".xlsx")
            # RDF to Excel always uses v1.0 format
            rdf_to_excel_v1(
                file,
                output_file_path,
                vocab_config=vocab_config,
                template_path=args.template,
            )
            logger.info("-> successfully converted to %s", output_file_path)
            # Extend size (length) of tables in all sheets
            adjust_all_tables_length(
                output_file_path,
                rows_pre_allocated=config.xlsx_rows_pre_allocated,
                active_sheet=CONCEPTS_SHEET_NAME,
            )
