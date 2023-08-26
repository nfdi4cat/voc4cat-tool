import glob
import logging
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill

from voc4cat import profiles
from voc4cat.checks import (
    Voc4catError,
    check_for_removed_iris,
    check_number_of_files_in_inbox,
    validate_vocabulary_files_for_ci_workflow,
)
from voc4cat.convert import validate_with_profile
from voc4cat.transform import join_split_turtle
from voc4cat.utils import (
    EXCEL_FILE_ENDINGS,
    RDF_FILE_ENDINGS,
    adjust_length_of_tables,
    is_supported_template,
)

logger = logging.getLogger(__name__)


def check_xlsx(fpath: Path, outfile: Path) -> int:
    """
    Complex checks of the xlsx file not handled by pydantic model validation

    Checks/validation implemented here need/use information from several rows
    and can therefore not be easily done in models.py with pydantic.
    However, SHACL validation does also catch the problem, at least in pre-
    liminary testing. So this function may get removed later. Doing the check
    in Excel has the advantage that the cell position can be added to the
    validation message which would not work with SHACL validation.

    For concepts:
    - The "Concept IRI" must be unique. However, it can be present in several
      rows as long as the languages in the rows with the same IRI are
      different. This condition is fulfilled when no language is used more
      than once per concept.
    """
    logger.debug("Running check of Concepts sheet for file %s", fpath)
    wb = openpyxl.load_workbook(fpath)
    is_supported_template(wb)
    ws = wb["Concepts"]
    color = PatternFill("solid", start_color="00FFCC00")  # orange

    subsequent_empty_rows = 0
    seen_concept_iris = []
    failed_checks = 0
    for row in ws.iter_rows(min_row=3, max_col=3):  # pragma: no branch
        if row[0].value and row[1].value:
            concept_iri, _, lang = (
                c.value.strip() if c.value is not None else "" for c in row
            )
            # Check that IRI is valid.
            #            config.IDRANGES
            # Check that IRI is used for exactly one concept.
            new_concept_iri = f'"{concept_iri}"@{lang.lower()}'
            if new_concept_iri in seen_concept_iris:
                failed_checks += 1
                msg = (
                    f'Same Concept IRI "{concept_iri}" used more than once for '
                    f'language "{lang}"'
                )
                logger.error(msg)
                # colorize problematic cells
                row[0].fill = color
                row[2].fill = color
                previously_seen_in_row = 3 + seen_concept_iris.index(new_concept_iri)
                ws[f"A{previously_seen_in_row}"].fill = color
                ws[f"C{previously_seen_in_row}"].fill = color
            else:
                seen_concept_iris.append(new_concept_iri)

            subsequent_empty_rows = 0

        # stop processing a sheet after 3 empty rows
        elif subsequent_empty_rows < 2:  # noqa: PLR2004
            subsequent_empty_rows += 1
        else:
            subsequent_empty_rows = 0
            break

    if failed_checks:
        wb.save(outfile)
        logger.info("-> Saved file with highlighted errors as %s", outfile)
        # Extend size (length) of tables in all sheets
        adjust_length_of_tables(outfile)
        return

    logger.info("-> xlsx check passed for file: %s", fpath)


def ci_post(args):
    prev_vocab_dir, vocab_new = args.ci_post, args.VOCAB
    for vocfile in glob.glob(str(vocab_new.resolve() / "*.ttl")):
        new = Path(vocfile)
        prev_split_voc = prev_vocab_dir / new.stem
        # The prev version could be in split form in a vocabulary directory
        if (
            prev_split_voc.exists()
            and prev_split_voc.is_dir()
            and any(prev_split_voc.glob("*.ttl"))
        ):
            # Create a single vocab out of the directory
            logger.debug("-> previous version is a split vocabulary, joining...")
            join_split_turtle(prev_split_voc)

        prev = prev_vocab_dir / new.name
        if not prev.exists():
            logger.debug(
                '-> previous version of vocabulary "%s" does not exist.',
                new.name,
            )
            continue
        check_for_removed_iris(prev, new)
        logger.info("-> Check ci-post passed.")


# ===== check command & helpers to validate cmd options =====


def _check_ci_args(args):
    msg = ""
    if args.ci_pre:
        if args.VOCAB and args.VOCAB.is_dir() and args.ci_pre.is_dir():
            return
        msg = "Need two dirs for ci_pre!"
    if args.ci_post:
        if args.VOCAB and args.VOCAB.is_dir() and args.ci_post.is_dir():
            return
        msg = "Need two dirs for ci_post!"
    if msg:
        logging.error(msg)
        raise Voc4catError(msg)


def check(args):
    logger.debug("Check subcommand started!")

    _check_ci_args(args)

    if not args.VOCAB and not args.listprofiles:
        msg = (
            "Argument VOCAB is required for this sub-command (except for "
            "option --listprofiles)."
        )
        logger.error(msg)
        return

    if args.listprofiles:
        s = "\nProfiles\nToken\tIRI\n-----\t-----\n"
        for k, v in profiles.PROFILES.items():
            s += f"{k}\t{v.uri}\n"
        print(s.rstrip())
        return

    if args.ci_pre:
        inbox_dir, vocab_dir = args.ci_pre, args.VOCAB
        check_number_of_files_in_inbox(inbox_dir)
        validate_vocabulary_files_for_ci_workflow(vocab_dir, inbox_dir)
        logger.info("-> Check ci-pre passed.")
        return

    if args.ci_post:
        ci_post(args)
        return

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]
    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    # check xlsx files
    for file in xlsx_files:
        outfile = file if args.outdir is None else args.outdir / file.name
        if outfile == file and not args.inplace:
            logger.warning(
                'This command will overwrite the existing file "%s".'
                'Use the flag "--inplace" to enforce replacement or '
                'supply an output directory with flag "--outdir".',
                file,
            )
            return
        check_xlsx(file, outfile)

    # validate rdf files with profile/pyshacl
    for file in rdf_files:
        logger.debug("Running SHACL validation for file %s", file)
        validate_with_profile(
            str(file), profile=args.profile, error_level=args.fail_at_level
        )
        logger.info("-> The file is valid according to the %s profile.", args.profile)
