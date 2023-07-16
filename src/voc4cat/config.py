# This module is used to share the configuration in across voc4cat.

import logging
import os
import sys
from pathlib import Path

from curies import Converter
from pydantic import AnyHttpUrl, BaseModel, conint, root_validator, validator
from rdflib import Graph
from rdflib.namespace import NamespaceManager

from voc4cat.fields import Orcid, Ror

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
    first_id: conint(ge=1)
    last_id: int
    gh_name: str
    orcid: Orcid | None = None
    organisation_ror_id: Ror | None = None

    @root_validator  # validates the model not a single field
    def order_of_ids(cls, values):
        if "first_id" in values:
            first, last = values["first_id"], values.get("last_id", "? (missing)")
            if last <= first:
                msg = f"last_id ({last}) must be greater than first_id ({first})."
                raise ValueError(msg)

        orcid = values.get("orcid", "")
        gh = values.get("gh_name", "")
        if not (orcid or gh):
            msg = (
                "ID range requires a github name or an ORCID "
                f"(range: {first_id}-{last_id})."
            )
            raise ValueError(msg)
        return values

    @validator("organisation_ror_id", "orcid", pre=True)
    def handle_empty_organisation_ror_id(cls, value):
        # None cannot be expressed in toml so we need to catch empty string before validation.
        if value == "":
            return None
        return value


class Vocab(BaseModel):
    id_length: conint(gt=2, lt=19)
    checks: Checks
    prefix_map: dict[str, AnyHttpUrl]
    id_range: list[IdrangeItem]

    @validator("id_range")
    def check_names_not_empty(cls, value):
        ids_defined = set()
        for idr in value:
            new_ids = set(range(idr.first_id, idr.last_id + 1))
            reused = list(ids_defined & new_ids)
            if reused:
                msg = f"Overlapping ID ranges for IDs {min(reused)}-{max(reused)}"
                raise ValueError(msg)
            ids_defined = ids_defined | new_ids
        return value


class IDrangeConfig(BaseModel):
    single_vocab: bool = False
    vocabs: dict[str, Vocab] = {}


def load_config():
    with CONFIG_FILE.open(mode="rb") as fp:
        conf = tomllib.load(fp)
    return IDrangeConfig(**conf)


idranges = load_config() if CONFIG_FILE.exists() else IDrangeConfig()

logger.debug("Config imported from %s", CONFIG_FILE)
