import logging
import os
import subprocess
import sys
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from voc4cat import config
from voc4cat.checks import Voc4catError

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates" / "docs"
STYLE_DIR = TEMPLATES_DIR


class IndexPage:
    def __init__(self, vocpath=None):
        self.METADATA = {}
        self.METADATA["title"] = "Index of vocabulary versions"
        self.vocpath = Path(".") if vocpath is None else Path(vocpath)
        self.vocabs = []
        self.vocab_data = defaultdict(dict)
        self.tags = []

    def _load_template(self, template_file):
        return Environment(
            loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True
        ).get_template(template_file)

    def get_version_data(self):
        cmd = ["git", "-C", str(self.vocpath), "tag", "--list", "v[0-9]*-[0-9]*-[0-9]*"]
        logger.debug("Running cmd: %s", " ".join(cmd))
        outp = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
        if outp.returncode != 0:
            logger.error("git command returned with error")
            return
        logger.debug("Cmd output: %s", outp.stdout)
        self.tags = outp.stdout.decode(sys.getdefaultencoding()).splitlines()

        gh_repo = os.getenv("GITHUB_REPOSITORY", "").split("/")[-1]  # owner/repo
        logger.debug('Repository name (from env.var): "%s"', gh_repo)

        for voc, vocdata in config.IDRANGES.vocabs.items():
            base_url = str(vocdata.permanent_iri_part).rstrip("_").rstrip("/")
            self.vocab_data[voc]["url_latest"] = base_url
            self.vocab_data[voc]["url_dev"] = base_url + "/dev"
            # links dev-docs on gh-pages (accessible even with non-resolving base_url)
            self.vocab_data[voc]["url_dev_gh"] = f"/{gh_repo}/dev/{voc}"
            # xlsx has no permanent uri; we link to its relative location in gh-pages
            self.vocab_data[voc]["url_xlsx"] = f"/{gh_repo}/dev/{voc}.xlsx"
            if not self.tags:
                logger.debug('No tags found in "%s"', str(self.vocpath))
                continue
            for tag in self.tags:
                self.vocab_data[voc][tag] = base_url + f"/{tag}"
                logger.debug('Adding tag "%s" to index.html', tag)

    def _make_versions(self):
        return self._load_template("vocabularies.html").render(
            tags=sorted(self.tags, reverse=True),
            vocabularies=self.vocab_data,
            has_releases=bool(self.tags),
        )

    def _make_document(self):
        with open(STYLE_DIR / "pylode.css") as f:
            css = f.read()

        return self._load_template("index.html").render(
            schemaorg=None,
            title=self.METADATA["title"],
            versions=self._make_versions(),
            vocabularies=self._make_versions(),
            has_vocabularies=len(self.vocab_data) > 0,
            css=css,
            voc4cat_version=version("voc4cat").split("+")[0],
        )

    def generate_document(self):
        return self._make_document()


def build_multirelease_index(voc_path, out_path):
    # load config
    conf = voc_path / "idranges.toml"
    if conf.exists():
        config.load_config(config_file=conf)
    else:
        msg = "Config file not found at: %s"
        logger.error(msg, conf)
        raise Voc4catError(msg % conf)

    destination = out_path / "index.html"
    p = IndexPage(voc_path)
    p.get_version_data()
    doc = p.generate_document()

    with open(destination, "w", encoding="utf-8") as f:
        f.write(doc)


if __name__ == "__main__":
    voc_path = Path(r"C:\Users\dlinke\MyProg_local\gh-nfdi4cat\voc4cat")
    build_multirelease_index(voc_path, Path("."))
