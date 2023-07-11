# This module is used to share the configuration in across voc4cat.

from pathlib import Path

import tomllib
from curies import Converter
from rdflib import Graph
from rdflib.namespace import NamespaceManager

VOCAB_TITLE = ""
CONFIG_FILE = Path("idranges.toml").resolve()


def load_config(fp: Path):
    with fp.open(mode="rb") as fp:
        return tomllib.load(fp)


idranges = load_config(CONFIG_FILE) if CONFIG_FILE.exists() else {}

namespace_manager = NamespaceManager(Graph())
# Initialize curies-converter with default namespace of rdflib.Graph
curies_converter = Converter.from_prefix_map(
    {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
)

# TODO Use pydantic for validation of idranges.toml content or https://gitlab.com/sscherfke/typed-settings
