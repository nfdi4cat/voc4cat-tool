import glob
import logging
from pathlib import Path

from voc4cat import profiles
from voc4cat.checks import (
    Voc4catError,
    check_for_removed_iris,
    check_number_of_files_in_inbox,
    validate_vocabulary_files_for_ci_workflow,
)
from voc4cat.convert import validate_with_profile
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS
from voc4cat.wrapper import check as check_xlsx

logger = logging.getLogger(__name__)


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
    logger.info("Check subcommand started!")

    _check_ci_args(args)

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
        return

    if args.ci_post:
        prev_vocab_dir, vocab_new = args.ci_post, args.VOCAB
        for vocfile in glob.glob(str(vocab_new.resolve() / "*.ttl")):
            new = Path(vocfile)
            vocfile_name = Path(vocfile).name
            prev = prev_vocab_dir / vocfile_name
            if not prev.exists():
                logger.debug(
                    '-> previous version of vocabulary "%s" does not exist.',
                    vocfile_name,
                )
                continue
            check_for_removed_iris(prev, new)
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
        logger.info("Running SHACL validation for file %s", file)
        validate_with_profile(
            str(file), profile=args.profile, error_level=args.fail_at_level
        )
        logger.info("-> The file is valid according to the %s profile.", args.profile)
