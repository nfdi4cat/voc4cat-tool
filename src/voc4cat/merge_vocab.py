# -*- coding: utf-8 -*-
# This script is mainly useful for CI.
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main(ttl_inbox, vocab):
    """
    Sync ttl-files from ttl_inbox into vocab folder

    New files are copied, existing files are synced by git merge-file.
    """
    retcode = 0
    for p in os.listdir(ttl_inbox):
        new = ttl_inbox / Path(p)
        if not new.suffix == ".ttl" or new.is_dir():
            print(f'Skipping "{new}"')
            continue
        if os.path.exists(vocab / Path(new).name):
            exists = vocab / Path(new).name
            cmd = ["git", "merge-file", "--theirs", str(exists), str(exists), str(new)]
            print("Running cmd: {0}".format(" ".join(cmd)))
            outp = subprocess.run(cmd, capture_output=True)
            print(outp.stdout)
            if retcode := outp.returncode != 0:
                break
        else:
            print(f'Copying "{new}" to "{vocab}"')
            shutil.copy(new, vocab)
    return retcode


def main_cli(args=None):

    if args is None:  # script run via entrypoint
        args = sys.argv[1:]

    if len(args) != 2:
        print("Usage: python merge_vocab.py <outbox_dir> <vocab_dir>")
        return 1
    outbox, vocab = args
    if os.path.exists(outbox) and os.path.exists(vocab):
        retcode = main(Path(outbox), Path(vocab))
        return retcode

    print(f'This script requires both folders to exist: "{outbox}" and "{vocab}"')
    return 1


if __name__ == "__main__":
    err = main_cli(sys.argv[1:])
    sys.exit(err)
