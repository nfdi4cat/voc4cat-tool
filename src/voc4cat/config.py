# This module is used to share the configuration in across voc4cat.

import logging
import os
import sys
from pathlib import Path

from curies import Converter
from pydantic import AnyHttpUrl, BaseModel
from rdflib import Graph
from rdflib.namespace import NamespaceManager

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)

# === Configuration that is not imported from idranges.toml ===

VOCAB_TITLE: str = ""
CONFIG_FILE: Path = Path("idranges.toml").resolve()
CI_RUN: bool = os.getenv("GITHUB_ACTIONS")

namespace_manager = NamespaceManager(Graph())
# Initialize curies-converter with default namespace of rdflib.Graph
curies_converter = Converter.from_prefix_map(
    {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
)


# === Configuration imported from idranges.toml stored as pydantic model ===


class Checks(BaseModel):
    no_delete: bool


class IdrangeItem(BaseModel):
    first_id: int
    last_id: int
    gh_username: str
    orcid: str
    organisation_ror_id: str


class Vocab(BaseModel):
    id_length: int
    checks: Checks
    prefix_map: dict[str, AnyHttpUrl]
    idrange: list[IdrangeItem]


class Config(BaseModel):
    single_vocab: bool = False
    vocabs: dict[str, Vocab] = {}


def load_config():
    with CONFIG_FILE.open(mode="rb") as fp:
        conf = tomllib.load(fp)
    return Config(**conf)


idranges = load_config() if CONFIG_FILE.exists() else Config()

logger.debug("Config imported from %s", CONFIG_FILE)
