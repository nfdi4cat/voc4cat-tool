"""Config module to share a configuration across all modules in voc4cat."""

import logging
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
    gh_name: constr(regex=r"(^(^$)|[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38})$") = ""
    orcid: Orcid | None = None
    ror_id: Ror | None = None

    @root_validator  # validates the model not a single field
    def order_of_ids(cls, values):
        first, last = values["first_id"], values.get("last_id", "? (missing)")
        if last <= first:
            msg = f"last_id ({last}) must be greater than first_id ({first})."
            raise ValueError(msg)

        orcid = values.get("orcid", "")
        gh = values.get("gh_name", "")
        if not (orcid or gh):
            msg = (
                "ID range requires a GitHub name or an ORCID "
                f"(range: {first!s}-{last!s})."
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
    id_length: conint(gt=1, lt=19)
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
                msg = f"Overlapping ID ranges for IDs {min(reused)}-{max(reused)}."
                raise ValueError(msg)
            ids_defined = ids_defined | new_ids
        return value


class IDrangeConfig(BaseModel):
    single_vocab: bool = False
    vocabs: dict[constr(to_lower=True), Vocab] = {}
    default_config: bool = False

    @root_validator
    def check_names_not_empty(cls, values):
        if values["single_vocab"] and len(values.get("vocabs", [])) > 1:
            msg = 'Inconsistent config: "single_vocab" is true but multiple vocabularies are found.'
            raise ValueError(msg)
        return values


# These parameters will be update/set by load_config.
IDRANGES = IDrangeConfig(default_config=True)
ID_PATTERNS = {}
ID_RANGES_BY_ACTOR = defaultdict(list)


def _id_ranges_by_actor(new_conf):
    # create look-up map for ID ranges of all "actors"
    id_ranges_by_actor = defaultdict(list)
    for name in new_conf["IDRANGES"].vocabs:
        voc = new_conf["IDRANGES"].vocabs.get(name)
        for idr in voc.id_range:
            rng = (idr.first_id, idr.last_id)
            if idr.orcid:
                id_ranges_by_actor[str(idr.orcid)].append(rng)
                no_url_orcid = str(idr.orcid).split("orcid.org/")[-1]
                id_ranges_by_actor[no_url_orcid].append(rng)
            if idr.gh_name:
                id_ranges_by_actor[str(idr.gh_name)].append(rng)
            if idr.ror_id:
                id_ranges_by_actor[str(idr.ror_id)].append(rng)
    return id_ranges_by_actor


def load_config(config_file: Path | None = None, config: IDrangeConfig | None = None):
    new_conf = {}
    new_conf["ID_PATTERNS"] = {}
    new_conf["ID_RANGES_BY_ACTOR"] = defaultdict(list)
    if config_file is not None and not config_file.exists():
        logger.warning('Configuration file "%s" not found.', config_file)
    if (True if config_file is None else not config_file.exists()) and config is None:
        new_conf["IDRANGES"] = IDrangeConfig(default_config=True)
        logger.debug("Initializing default config.")
    elif config_file and config is None:
        with config_file.open(mode="rb") as fp:
            conf = tomllib.load(fp)
        logger.debug("Config loaded from: %s", config_file)
        new_conf["IDRANGES"] = IDrangeConfig(**conf)
    else:
        new_conf["IDRANGES"] = IDrangeConfig().parse_raw(config.json())
        logger.debug("Refreshing global state of config.")

    # pre-compile regex patterns for ID part of IRIs for each vocabulary
    id_patterns = {}
    for name in new_conf["IDRANGES"].vocabs:
        voc = new_conf["IDRANGES"].vocabs.get(name)
        id_patterns[name] = re.compile(r"(?P<identifier>[0-9]{%i})$" % voc.id_length)
    new_conf["ID_PATTERNS"] = id_patterns

    new_conf["ID_RANGES_BY_ACTOR"] = _id_ranges_by_actor(new_conf)

    for name, value in new_conf.items():
        globals()[name] = value
