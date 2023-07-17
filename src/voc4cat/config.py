"""Config module to share a configuration across all modules in voc4cat."""

import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from curies import Converter
from pydantic import AnyHttpUrl, BaseModel, conint, constr, validator
from pydantic.class_validators import root_validator
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
    allow_delete: bool = False


class IdrangeItem(BaseModel):
    first_id: conint(ge=1)
    last_id: int
    gh_name: constr(regex=r"(^(^$)|([a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$))") = ""
    orcid: Orcid | None = None
    ror_id: Ror | None = None

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
                f"(range: {first}-{last})."
            )
            raise ValueError(msg)
        return values

    @validator("ror_id", "orcid", pre=True)
    def handle_empty_field(cls, value):
        # None cannot be expressed in toml so we catch an empty string before validation.
        if value == "":
            return None
        return value


class Vocab(BaseModel):
    id_length: conint(gt=2, lt=19)
    permanent_iri_part: AnyHttpUrl
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
    vocabs: dict[constr(to_lower=True), Vocab] = {}
    default_config: bool = (
        False  # True if initialized as default (not from config file)
    )

    @root_validator
    def check_names_not_empty(cls, values):
        if values["single_vocab"] and len(values["vocabs"]) > 1:
            msg = 'Inconsistent config: "single_vocab" is true but multiple vocabularies are found.'
            raise ValueError(msg)
        return values


def load_config():
    with CONFIG_FILE.open(mode="rb") as fp:
        conf = tomllib.load(fp)
    return IDrangeConfig(**conf)


idranges = load_config() if CONFIG_FILE.exists() else IDrangeConfig(default_config=True)

logger.debug("Config imported from %s", CONFIG_FILE)

# pre-compile regex patterns for ID part of IRIs for each vocabulary
id_patterns = {}
for name in idranges.vocabs:
    voc = idranges.vocabs.get(name)
    if (id_length := voc.id_length) > 0:
        id_patterns[name] = re.compile(r"(?P<identifier>[0-9]{%i})$" % id_length)

id_ranges_by_actor = defaultdict(list)
for name in idranges.vocabs:
    voc = idranges.vocabs.get(name)
    for idr in voc.id_range:
        rng = (idr.first_id, idr.last_id)
        if idr.orcid:
            id_ranges_by_actor[str(idr.orcid)].append(rng)
        if idr.gh_name:
            id_ranges_by_actor[str(idr.gh_name)].append(rng)
        if idr.ror_id:
            id_ranges_by_actor[str(idr.ror_id)].append(rng)
