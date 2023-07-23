# This script is mainly useful for CI.
import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from voc4cat.wrapper import setup_logging

logger = logging.getLogger(__name__)

loglevel = logging.INFO


def main(ttl_inbox: Path, vocab: Path) -> int:
    """
    Sync ttl-files from ttl_inbox into vocab folder

    New files are copied, existing files are synced by git merge-file.
    """
    retcode = 0
    for p in os.listdir(ttl_inbox):
        new = ttl_inbox / Path(p)
        if new.suffix != ".ttl" or new.is_dir():
            logger.info('Skipping "%s"', new)
            continue
        if os.path.exists(vocab / Path(new).name):
            exists = vocab / Path(new).name
            cmd = ["git", "merge-file", "--theirs", str(exists), str(exists), str(new)]
            logger.info("Running cmd: %s", " ".join(cmd))
            outp = subprocess.run(cmd, capture_output=True)  # noqa: S603
            logger.info(outp.stdout)
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
        help="The file to write logging output to. It is place in directory outbox_dir.",
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
        setup_logging(loglevel)
    else:
        outbox.mkdir(exist_ok=True, parents=True)
        logfile = Path(outbox) / logfile
        setup_logging(loglevel, logfile)

    if not has_outbox or not vocab.exists():
        logger.error(
            'This script requires both folders to exist: "%s" and "%s"', outbox, vocab
        )
        return 1

    return main(Path(outbox), Path(vocab))


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    sys.exit(err)
