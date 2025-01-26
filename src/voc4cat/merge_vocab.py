# This script is mainly useful for CI.
import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from voc4cat import setup_logging

logger = logging.getLogger(__name__)


def main(ttl_inbox: Path, vocab: Path) -> int:
    """
    Sync ttl-files from ttl_inbox into vocab folder

    New files are copied, existing files are synced by git merge-file.
    """
    retcode = 0
    for new in ttl_inbox.iterdir():
        if new.is_dir():
            logger.debug('Entering directory "%s"', new)
            (vocab / new.name).mkdir(exist_ok=True)
            retcode = main(new, vocab / new.name)
            if retcode != 0:
                break
            continue
        if new.suffix != ".ttl":
            logger.debug('Skipping "%s"', new)
            continue
        if (vocab / Path(new).name).exists():
            exists = vocab / Path(new).name
            cmd = ["git", "merge-file", "--theirs", str(exists), str(exists), str(new)]
            logger.info("Running cmd: %s", " ".join(cmd))
            outp = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
            if outp.stdout:
                logger.info("Cmd output: %s", outp.stdout)
            if retcode := outp.returncode != 0:
                break
        else:
            logger.info('Copying "%s" to "%s"', new, vocab)
            shutil.copy(new, vocab)
    return retcode


def main_cli(args=None) -> int:
    if args is None:  # run via entrypoint
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="merge_vocab", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-l",
        "--logfile",
        help="The file to write logging output to. It is placed in outbox_dir.",
        type=Path,
        required=False,
    )
    parser.add_argument("outbox_dir", type=Path, help="Directory with files to merge.")

    parser.add_argument("vocab_dir", type=Path, help="Directory to merge to.")
    args_merge = parser.parse_args(args)

    outbox, vocab = args_merge.outbox_dir, args_merge.vocab_dir
    logfile = args_merge.logfile
    has_outbox = outbox.exists()
    if logfile is None:
        setup_logging()
    else:
        outbox.mkdir(exist_ok=True, parents=True)
        setup_logging(logfile=logfile)

    logger.info("Executing cmd: merge_vocab %s", " ".join(args))
    if not has_outbox or not vocab.exists():
        logger.error(
            'This script requires both folders to exist: "%s" and "%s"', outbox, vocab
        )
        return 1

    return main(Path(outbox), Path(vocab))


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    sys.exit(err)
