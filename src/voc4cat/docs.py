import logging
from pathlib import Path

from voc4cat.wrapper import run_ontospy, run_pylode

logger = logging.getLogger(__name__)


def docs(args):
    logger.info("Docs subcommand started!")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    turtle_files = [f for f in files if f.suffix.lower() in (".turtle", ".ttl")]

    if not turtle_files:
        logger.info("-> Nothing to do. No turtle file(s) found.")
        return

    for file in turtle_files:
        logger.debug('Processing "%s"', file)
        outdir = args.outdir
        if any(outdir.iterdir()) and not args.force:
            logger.warning(
                'The folder "%s" is not empty. Use "--force" to write to the folder anyway.',
                outdir,
            )
            return

        if args.style == "pylode":
            run_pylode(file, outdir)
        elif args.style == "ontospy":
            run_ontospy(file, outdir)
        else:  # pragma: no cover
            # This should not be reached since argparse checks --style choices.
            msg = f"Unsupported style: {args.style}"
            raise AssertionError(msg)
