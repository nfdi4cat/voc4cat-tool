"""Config module to share a configuration across all modules in voc4cat."""

import logging
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Annotated

from curies import Converter
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from rdflib import Graph
from rdflib.namespace import NamespaceManager
from typing_extensions import Self

from voc4cat.fields import ORCIDIdentifier, RORIdentifier

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)

# === Configuration that is not imported from idranges.toml ===

# Initialize curies-converter with default namespace of rdflib.Graph.
# It is globally changed depending on which vocabulary is processed.
curies_converter: Converter = Converter.from_prefix_map(
    {prefix: str(url) for prefix, url in NamespaceManager(Graph()).namespaces()}
)

# Number of empty rows appended to the tables. The keys in the dict must match
# the table names exactly.
xlsx_rows_pre_allocated = {
    "Concepts": 20,
    "Mappings": 15,
    "Collections": 10,
}

# === Configuration imported from idranges.toml stored as pydantic model ===


class Checks(BaseModel):
    allow_delete: bool = False


class IdrangeItem(BaseModel):
    first_id: Annotated[int, Field(ge=1)]
    last_id: int
    gh_name: Annotated[
        str, StringConstraints(pattern=r"((^$)|^[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38})$")
    ] = ""
    orcid: ORCIDIdentifier | None = None
    ror_id: RORIdentifier | None = None
    name: str = ""  # Optional human-readable name (from ORCID profile)

    @model_validator(mode="after")
    def order_of_ids(self) -> Self:
        first, last = self.first_id, self.last_id
        if last <= first:
            msg = f"last_id ({last}) must be greater than first_id ({first})."
            raise ValueError(msg)

        orcid = self.orcid
        gh = self.gh_name
        if not (orcid or gh):
            msg = (
                "ID range requires a GitHub name or an ORCID "
                f"(range: {first!s}-{last!s})."
            )
            raise ValueError(msg)
        return self

    @field_validator("ror_id", "orcid", mode="before")
    @classmethod
    def handle_empty_field(cls, value):
        # None cannot be expressed in toml so we catch an empty string before validation.
        if value == "":
            return None
        return value


class Vocab(BaseModel):
    # Required fields
    id_length: Annotated[int, Field(ge=1, lt=19)]
    permanent_iri_part: AnyHttpUrl
    checks: Checks
    prefix_map: dict[str, AnyHttpUrl]
    id_range: list[IdrangeItem] = []

    # Scheme metadata fields (all optional, used for ConceptScheme in Excel)
    vocabulary_iri: str = ""
    prefix: str = ""
    title: str = ""
    description: str = ""
    created_date: str = ""
    creator: str = ""  # Multi-line: "<orcid-URL or ror> <name>" per line
    publisher: str = ""  # Multi-line: "<orcid-URL or ror> <name>" per line
    custodian: str = ""  # Multi-line: "<name> <gh-profile-URL> <orcid-URL>" per line
    catalogue_pid: str = ""
    documentation: str = ""
    issue_tracker: str = ""
    helpdesk: str = ""
    repository: str = ""
    provenance_url_template: str = ""  # Jinja template for provenance (git blame) URLs
    homepage: str = ""
    conforms_to: str = ""
    history_note: str = ""  # Auto-generated if empty: "Created {date} by {names}."
    profile_local_path: str = (
        ""  # Path to SHACL profile file, relative to idranges.toml
    )

    @field_validator("id_range", mode="before")
    @classmethod
    def check_names_not_empty(cls, value):
        ids_defined = set()
        for idr in value:
            new_ids = set(range(idr["first_id"], idr["last_id"] + 1))
            reused = list(ids_defined & new_ids)
            if reused:
                msg = f"Overlapping ID ranges for IDs {min(reused)}-{max(reused)}."
                raise ValueError(msg)
            ids_defined = ids_defined | new_ids
        return value

    @model_validator(mode="after")
    def validate_required_scheme_fields(self) -> Self:
        """Validate that mandatory ConceptScheme metadata fields are not empty."""
        required_fields = [
            "vocabulary_iri",
            "title",
            "description",
            "created_date",
            "creator",
            "repository",
        ]

        missing = []
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or not value.strip():
                missing.append(field_name)

        if missing:
            msg = f"Mandatory ConceptScheme fields are empty: {', '.join(missing)}"
            raise ValueError(msg)

        # Validate provenance_url_template if provided
        if (
            self.provenance_url_template
            and "{{ entity_id }}" not in self.provenance_url_template
        ):
            msg = "provenance_url_template must contain '{{ entity_id }}'"
            raise ValueError(msg)

        return self


class IDrangeConfig(BaseModel):
    config_version: str = ""
    single_vocab: bool = False
    vocabs: dict[Annotated[str, StringConstraints(to_lower=True)], Vocab] = {}
    default_config: bool = False

    @model_validator(mode="after")
    def check_names_not_empty(self) -> Self:
        if self.single_vocab and len(self.vocabs) > 1:
            msg = 'Inconsistent config: "single_vocab" is true but multiple vocabularies are found.'
            raise ValueError(msg)
        return self


# These parameters will be updated/set by load_config.
IDRANGES = IDrangeConfig(default_config=True)
IDRANGES_PATH: Path | None = (
    None  # Path to idranges.toml (for resolving relative paths)
)
ID_PATTERNS = {}
ID_RANGES_BY_ACTOR = defaultdict(list)
CURIES_CONVERTER_MAP = {}


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
    new_conf["IDRANGES_PATH"] = None
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
        new_conf["IDRANGES_PATH"] = config_file.resolve()
    else:
        new_conf["IDRANGES"] = IDrangeConfig().model_validate_json(
            config.model_dump_json()
        )
        logger.debug("Refreshing global state of config.")

    # pre-compile regex patterns for ID part of IRIs for each vocabulary
    id_patterns = {}
    for name in new_conf["IDRANGES"].vocabs:
        voc = new_conf["IDRANGES"].vocabs.get(name)
        id_patterns[name] = re.compile(r"(?P<identifier>[0-9]{%i})$" % voc.id_length)  # noqa: UP031
    new_conf["ID_PATTERNS"] = id_patterns

    new_conf["ID_RANGES_BY_ACTOR"] = _id_ranges_by_actor(new_conf)

    # Initialize curies-converter for all vocabs with default namespace of rdflib.Graph
    namespace_manager = NamespaceManager(Graph())
    for name in new_conf["IDRANGES"].vocabs:
        curies_converter = Converter.from_prefix_map(
            {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
        )
        prefix_map = new_conf["IDRANGES"].vocabs[name].prefix_map
        for prefix, uri_prefix in prefix_map.items():
            curies_converter.add_prefix(prefix, str(uri_prefix), merge=True)
        CURIES_CONVERTER_MAP[name] = curies_converter

    for name, value in new_conf.items():
        globals()[name] = value
