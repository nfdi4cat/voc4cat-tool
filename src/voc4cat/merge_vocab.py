# This script is mainly useful for CI.
import os
import shutil
import subprocess
import sys
from pathlib import Path

VOCAB_DIR = Path("vocabularies")
OUTBOX = Path("outbox")


def main(outbox, vocab):
    """
    Sync ttl-files in outbox and vocab folder

    New files are copied, existing files are synced by git merge-file.
    """
    retcode = 0
    for p in os.listdir(outbox):
        new = outbox / Path(p)
        if not new.suffix == ".ttl" or new.is_dir():
            print(f'skipping "{new}"')
            continue
        if os.path.exists(vocab / Path(new).name):
            exists = vocab / Path(new).name
            cmd = ["git", "merge-file", "--theirs", str(exists), str(exists), str(new)]
            print(" ".join(cmd))
            outp = subprocess.run(cmd, capture_output=True)
            print(outp.stdout)
            if retcode := outp.returncode != 0:
                break
        else:
            print(f'copying "{new}" to "{vocab}"')
            shutil.copy(new, vocab)
    return retcode


def run():
    if len(sys.argv) != 3:
        print('Usage: "python merge_vocab.py outbox_dir vocab_dir')
        sys.exit(1)
    outbox, vocab = sys.argv[1:]
    if os.path.exists(outbox) and os.path.exists(vocab):
        retcode = main(Path(outbox), Path(vocab))
        sys.exit(retcode)
    else:
        print(f'This script requires both folders to exist: "{outbox}" and "{vocab}"')
        sys.exit(1)


if __name__ == "__main__":
    run()
