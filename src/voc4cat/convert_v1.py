"""Converter for RDF vocabularies to/from v1.0 Excel template format.

This module provides functions to convert between RDF vocabularies and
the v1.0 Excel template structure, supporting bidirectional conversion:
- RDF -> XLSX: Extract data from RDF graphs into v1.0 template
- XLSX -> RDF: Read v1.0 template and generate RDF graph

The two-way conversion is designed to be lossless (isomorphic graphs).
"""

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal as TypingLiteral

import curies
from rdflib import (
    DCAT,
    DCTERMS,
    OWL,
    PROV,
    RDF,
    RDFS,
    SKOS,
    XSD,
    Graph,
    Literal,
    Namespace,
    URIRef,
)

from voc4cat import config
from voc4cat.models_v1 import (
    CONCEPT_SCHEME_SHEET_NAME,
    CONCEPT_SCHEME_SHEET_TITLE,
    ID_RANGES_SHEET_NAME,
    ID_RANGES_SHEET_TITLE,
    OBSOLETION_REASONS_COLLECTIONS,
    OBSOLETION_REASONS_CONCEPTS,
    PREFIXES_SHEET_NAME,
    PREFIXES_SHEET_TITLE,
    TEMPLATE_VERSION,
    CollectionV1,
    ConceptSchemeV1,
    ConceptV1,
    IDRangeInfoV1,
    MappingV1,
    PrefixV1,
)
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS
from voc4cat.xlsx_api import export_to_xlsx, import_from_xlsx
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig

# schema.org namespace (not in rdflib by default)
SDO = Namespace("https://schema.org/")

logger = logging.getLogger(__name__)


# =============================================================================
# Provenance URL Helpers
# =============================================================================


def build_provenance_url(entity_id: str, vocab_name: str) -> str:
    """Build a git blame URL for an entity.

    The URL points to the version-specific TTL file on GitHub.
    Format: https://github.com/{owner}/{repo}/blame/{version}/vocabularies/{vocab_name}/{entity_id}.ttl

    Args:
        entity_id: The concept or collection ID (e.g., "0000004").
        vocab_name: The vocabulary name from idranges.toml (e.g., "voc4cat").

    Returns:
        The provenance URL, or empty string if GITHUB_REPOSITORY is not set.
    """
    github_repo = os.getenv("GITHUB_REPOSITORY", "")
    if not github_repo:
        return ""

    version = os.getenv("VOC4CAT_VERSION", "") or "main"
    return f"https://github.com/{github_repo}/blame/{version}/vocabularies/{vocab_name}/{entity_id}.ttl"


def extract_entity_id_from_iri(iri: str) -> str:
    """Extract the entity ID from a full IRI.

    Handles both slash-based and hash-based IRIs.

    Examples:
        'https://w3id.org/nfdi4cat/voc4cat/0000004' -> '0000004'
        'https://example.org/vocab#concept123' -> 'concept123'

    Args:
        iri: Full IRI string.

    Returns:
        The entity ID portion.
    """
    if "#" in iri:
        return iri.split("#")[-1]
    return iri.rstrip("/").split("/")[-1]


# =============================================================================
# RDF Extraction Functions
# =============================================================================


def extract_concept_scheme_from_rdf(graph: Graph) -> dict:
    """Extract ConceptScheme data from an RDF graph.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Dictionary with concept scheme data fields.
    """
    holder = {
        "vocabulary_iri": "",
        "title": "",
        "description": "",
        "created_date": "",
        "modified_date": "",
        "creator": "",
        "publisher": "",
        "version": "",
        "change_note": "",
        "custodian": "",
        "catalogue_pid": "",
    }

    for s in graph.subjects(RDF.type, SKOS.ConceptScheme):
        holder["vocabulary_iri"] = str(s)

        for p, o in graph.predicate_objects(s):
            if p == SKOS.prefLabel:
                holder["title"] = str(o)
            elif p == SKOS.definition:
                holder["description"] = str(o)
            elif p == DCTERMS.created:
                holder["created_date"] = str(o)
            elif p == DCTERMS.modified:
                holder["modified_date"] = str(o)
            elif p == DCTERMS.creator:
                holder["creator"] = str(o)
            elif p == DCTERMS.publisher:
                holder["publisher"] = str(o)
            elif p == OWL.versionInfo:
                holder["version"] = str(o)
            elif p in [SKOS.historyNote, DCTERMS.provenance, PROV.wasDerivedFrom]:
                holder["change_note"] = str(o)
            elif p == DCAT.contactPoint:
                holder["custodian"] = str(o)
            elif p == RDFS.seeAlso:
                holder["catalogue_pid"] = str(o)

        # Only process the first ConceptScheme found
        # TODO: log warning or error if multiple found
        break

    return holder


def format_config_suggestion_from_043(
    rdf_path: Path,
    existing_config: "config.Vocab | None" = None,
    vocab_name: str | None = None,
) -> str:
    """Extract scheme metadata from 043 RDF and merge with existing config.

    Args:
        rdf_path: Path to the 043 RDF file.
        existing_config: Optional existing Vocab config to merge with.
        vocab_name: Optional vocab name override. Defaults to RDF file stem.

    Returns:
        TOML string with complete [vocabs.VOCABNAME] section.
    """
    graph = Graph()
    graph.parse(rdf_path)

    rdf_data = extract_concept_scheme_from_rdf(graph)

    # Derive vocab name from file stem if not provided
    if vocab_name is None:
        vocab_name = rdf_path.stem.lower()

    lines = [
        f"# ==== Configuration for vocabulary '{vocab_name}' ====",
        f"# Metadata extracted from: {rdf_path.name}",
        "",
        f"[vocabs.{vocab_name}]",
    ]

    # Structural fields from existing config (required, can't be extracted from RDF)
    if existing_config:
        lines.append(f"id_length = {existing_config.id_length}")
        lines.append(f'permanent_iri_part = "{existing_config.permanent_iri_part}"')
    else:
        lines.append("# TODO: Set required structural fields")
        lines.append("id_length = 7")
        lines.append('permanent_iri_part = "https://example.org/"')

    lines.append("")
    lines.append("# ==== ConceptScheme Metadata ====")
    lines.append("# Fields marked MANDATORY must be filled before use.")
    lines.append("")

    # MANDATORY fields - prefer RDF data, fall back to existing config
    vocab_iri = rdf_data.get("vocabulary_iri") or (
        existing_config.vocabulary_iri if existing_config else ""
    )
    lines.append("# MANDATORY: IRI for the vocabulary (skos:ConceptScheme)")
    lines.append(f'vocabulary_iri = "{vocab_iri}"')
    lines.append("")

    lines.append("# Optional: Registered (or preferred) prefix for this vocabulary")
    prefix_val = existing_config.prefix if existing_config else ""
    lines.append(f'prefix = "{prefix_val}"')
    lines.append("")

    title = rdf_data.get("title") or (existing_config.title if existing_config else "")
    lines.append("# MANDATORY: Title of the vocabulary")
    lines.append(f'title = "{title}"')
    lines.append("")

    description = rdf_data.get("description") or (
        existing_config.description if existing_config else ""
    )
    lines.append("# MANDATORY: General description of the vocabulary")
    lines.append(f'description = "{description}"')
    lines.append("")

    created_date = rdf_data.get("created_date") or (
        existing_config.created_date if existing_config else ""
    )
    lines.append("# MANDATORY: Date of creation (ISO-8601 format: YYYY-MM-DD)")
    lines.append(f'created_date = "{created_date}"')
    lines.append("")

    # Creator - may be multi-line, use triple quotes
    creator = rdf_data.get("creator") or (
        existing_config.creator if existing_config else ""
    )
    lines.append(
        "# MANDATORY: Creator(s) - multi-line text, each line: "
        '"<orcid-URL or ror-URL> <name>"'
    )
    if creator:
        lines.append(f'creator = """\n{creator}\n"""')
    else:
        lines.append('# creator = """')
        lines.append("# https://orcid.org/0000-0001-2345-6788 Alice Smith")
        lines.append('# """')
    lines.append("")

    # Optional fields from RDF
    publisher = rdf_data.get("publisher") or (
        existing_config.publisher if existing_config else ""
    )
    lines.append(
        "# Optional: Publisher(s) - multi-line text, each line: "
        '"<orcid-URL or ror-URL> <name>"'
    )
    if publisher:
        lines.append(f'publisher = """\n{publisher}\n"""')
    else:
        lines.append('# publisher = """')
        lines.append("# https://ror.org/04fa4r544 Example Organization")
        lines.append('# """')
    lines.append("")

    custodian = rdf_data.get("custodian") or (
        existing_config.custodian if existing_config else ""
    )
    lines.append(
        "# Optional: Custodian(s) - multi-line text, each line: "
        '"<name> <gh-profile-URL> <orcid-URL>"'
    )
    if custodian:
        lines.append(f'custodian = """\n{custodian}\n"""')
    else:
        lines.append('# custodian = """')
        lines.append(
            "# Alice Smith https://github.com/asmith https://orcid.org/0000-0001-2345-6789"
        )
        lines.append('# """')
    lines.append("")

    catalogue_pid = rdf_data.get("catalogue_pid") or (
        existing_config.catalogue_pid if existing_config else ""
    )
    lines.append("# Optional: DOI or other catalogue persistent identifier")
    if catalogue_pid:
        lines.append(f'catalogue_pid = "{catalogue_pid}"')
    else:
        lines.append('# catalogue_pid = ""')
    lines.append("")

    # New v1.0 fields (not in 043 RDF)
    documentation = existing_config.documentation if existing_config else ""
    lines.append("# Optional: URL of documentation or guidelines")
    if documentation:
        lines.append(f'documentation = "{documentation}"')
    else:
        lines.append('# documentation = ""')
    lines.append("")

    issue_tracker = existing_config.issue_tracker if existing_config else ""
    lines.append("# Optional: URL of issue tracker")
    if issue_tracker:
        lines.append(f'issue_tracker = "{issue_tracker}"')
    else:
        lines.append('# issue_tracker = ""')
    lines.append("")

    helpdesk = existing_config.helpdesk if existing_config else ""
    lines.append("# Optional: URL of helpdesk")
    if helpdesk:
        lines.append(f'helpdesk = "{helpdesk}"')
    else:
        lines.append('# helpdesk = ""')
    lines.append("")

    # Repository - MANDATORY but not in 043 RDF
    repository = existing_config.repository if existing_config else ""
    lines.append("# MANDATORY: URL of repository or online vocabulary editor")
    lines.append("# NOTE: This field is mandatory in v1.0 but not present in 043 RDF.")
    if repository:
        lines.append(f'repository = "{repository}"')
    else:
        lines.append('# repository = "https://github.com/YOUR-ORG/YOUR-REPO"')
    lines.append("")

    homepage = existing_config.homepage if existing_config else ""
    lines.append("# Optional: URL of homepage")
    if homepage:
        lines.append(f'homepage = "{homepage}"')
    else:
        lines.append('# homepage = ""')
    lines.append("")

    conforms_to = existing_config.conforms_to if existing_config else ""
    lines.append("# Optional: URL of SHACL profile the vocabulary conforms to")
    if conforms_to:
        lines.append(f'conforms_to = "{conforms_to}"')
    else:
        lines.append('# conforms_to = ""')
    lines.append("")

    # Checks section
    lines.append("# ==== Checks Configuration ====")
    lines.append(f"[vocabs.{vocab_name}.checks]")
    if existing_config:
        lines.append(
            f"allow_delete = {str(existing_config.checks.allow_delete).lower()}"
        )
    else:
        lines.append("allow_delete = false")
    lines.append("")

    # Prefix map section
    lines.append("# ==== Prefix Map ====")
    lines.append(f"[vocabs.{vocab_name}.prefix_map]")
    if existing_config and existing_config.prefix_map:
        for prefix_key, prefix_url in existing_config.prefix_map.items():
            lines.append(f'{prefix_key} = "{prefix_url}"')
    else:
        lines.append("# Add prefix mappings here, e.g.:")
        lines.append('# ex = "https://example.org/"')
    lines.append("")

    # ID ranges section
    lines.append("# ==== ID Ranges ====")
    if existing_config and existing_config.id_range:
        for id_range in existing_config.id_range:
            lines.append(f"[[vocabs.{vocab_name}.id_range]]")
            lines.append(f"first_id = {id_range.first_id}")
            lines.append(f"last_id = {id_range.last_id}")
            lines.append(f'gh_name = "{id_range.gh_name}"')
            lines.append(f'orcid = "{id_range.orcid or ""}"')
            lines.append(f'ror_id = "{id_range.ror_id or ""}"')
            lines.append("")
    else:
        lines.append(f"[[vocabs.{vocab_name}.id_range]]")
        lines.append("first_id = 1")
        lines.append("last_id = 100")
        lines.append('gh_name = "your-github-name"')
        lines.append('orcid = ""')
        lines.append('ror_id = ""')
        lines.append("")

    return "\n".join(lines)


def build_config_file_from_suggestions(
    suggestions: list[str],
    single_vocab: bool | None = None,
) -> str:
    """Build a complete idranges.toml config file from vocab suggestions.

    Args:
        suggestions: List of TOML strings for each [vocabs.X] section.
        single_vocab: Override for single_vocab setting. If None, determined by count.

    Returns:
        Complete TOML config file as string.
    """
    if single_vocab is None:
        single_vocab = len(suggestions) == 1

    lines = [
        "# ==== General Configuration ====",
        "# Generated config suggestion for v1.0 format",
        "# Review and fill in MANDATORY fields before use.",
        "",
        "# Configuration format version (for future compatibility)",
        'config_version = "1.0"',
        "",
        "# Allow only a single vocabulary (default) or multiple vocabularies.",
        f"single_vocab = {str(single_vocab).lower()}",
        "",
    ]

    for suggestion in suggestions:
        lines.append(suggestion)

    return "\n".join(lines)


def extract_concepts_from_rdf(graph: Graph) -> dict[str, dict[str, dict]]:
    """Extract Concepts from an RDF graph, grouped by IRI and language.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Nested dict: {concept_iri: {language: concept_data_dict}}
        Each concept_data_dict contains: preferred_label, definition,
        alternate_labels, parent_iris, source_vocab_iri, change_note,
        editorial_note, obsolete_reason, influenced_by_iris,
        source_vocab_license, source_vocab_rights_holder.
    """
    # Structure: {iri: {lang: {field: value}}}
    concepts_by_iri_lang: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(dict)
    )

    # First pass: collect all data per concept
    concept_data: dict[str, dict] = defaultdict(
        lambda: {
            "pref_labels": {},  # {lang: label}
            "definitions": {},  # {lang: definition}
            "alt_labels": {},  # {lang: [labels]}
            "editorial_notes": {},  # {lang: note}
            "parent_iris": [],
            "source_vocab_iri": "",
            "source_vocab_license": "",
            "source_vocab_rights_holder": "",
            "change_note": "",
            "obsolete_reason": "",
            "is_deprecated": False,
            "influenced_by_iris": [],
            "replaced_by_iri": "",
        }
    )

    for s in graph.subjects(RDF.type, SKOS.Concept):
        iri = str(s)
        data = concept_data[iri]

        for p, o in graph.predicate_objects(s):
            if p == SKOS.prefLabel:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["pref_labels"][lang] = str(o)
            elif p == SKOS.definition:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["definitions"][lang] = str(o)
            elif p == SKOS.altLabel:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                if lang not in data["alt_labels"]:
                    data["alt_labels"][lang] = []
                data["alt_labels"][lang].append(str(o))
            elif p == SKOS.editorialNote:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["editorial_notes"][lang] = str(o)
            elif p == SKOS.broader:
                data["parent_iris"].append(str(o))
            elif p == PROV.hadPrimarySource:
                data["source_vocab_iri"] = str(o)
            elif p == DCTERMS.license:
                data["source_vocab_license"] = str(o)
            elif p == DCTERMS.rightsHolder:
                data["source_vocab_rights_holder"] = str(o)
            elif p == SKOS.changeNote:
                data["change_note"] = str(o)
            elif p == OWL.deprecated:
                data["is_deprecated"] = str(o).lower() == "true"
            elif p == SKOS.historyNote:
                # historyNote is used for obsoletion reason when deprecated
                data["obsolete_reason"] = str(o)
            elif p == PROV.wasInfluencedBy:
                data["influenced_by_iris"].append(str(o))
            elif p == DCTERMS.isReplacedBy:
                data["replaced_by_iri"] = str(o)

    # Second pass: organize by IRI and language
    for iri, data in concept_data.items():
        # Determine all languages present for this concept
        all_langs = set(data["pref_labels"].keys()) | set(data["definitions"].keys())

        # Put "en" first if available
        langs_ordered = sorted(all_langs)
        if "en" in langs_ordered:
            langs_ordered.remove("en")
            langs_ordered.insert(0, "en")

        for lang in langs_ordered:
            # Only include obsolete_reason if concept is deprecated
            obsolete_reason = data["obsolete_reason"] if data["is_deprecated"] else ""

            concepts_by_iri_lang[iri][lang] = {
                "preferred_label": data["pref_labels"].get(lang, ""),
                "definition": data["definitions"].get(lang, ""),
                "alternate_labels": data["alt_labels"].get(lang, []),
                "editorial_note": data["editorial_notes"].get(lang, ""),
                "parent_iris": data["parent_iris"],
                "source_vocab_iri": data["source_vocab_iri"],
                "source_vocab_license": data["source_vocab_license"],
                "source_vocab_rights_holder": data["source_vocab_rights_holder"],
                "change_note": data["change_note"],
                "obsolete_reason": obsolete_reason,
                "influenced_by_iris": data["influenced_by_iris"],
                "replaced_by_iri": data["replaced_by_iri"],
                "is_deprecated": data["is_deprecated"],
            }

    return dict(concepts_by_iri_lang)


def extract_collections_from_rdf(graph: Graph) -> dict[str, dict[str, dict]]:
    """Extract Collections from an RDF graph, grouped by IRI and language.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Nested dict: {collection_iri: {language: collection_data_dict}}
        Each collection_data_dict contains: preferred_label, definition, change_note,
        editorial_note, obsolete_reason, ordered, members.
    """
    from rdflib.collection import Collection as RDFCollection

    collections_by_iri_lang: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(dict)
    )

    # First pass: collect all data per collection
    collection_data: dict[str, dict] = defaultdict(
        lambda: {
            "pref_labels": {},  # {lang: label}
            "definitions": {},  # {lang: definition}
            "editorial_notes": {},  # {lang: note}
            "change_note": "",
            "obsolete_reason": "",
            "is_deprecated": False,
            "ordered": False,
            "members": [],  # member IRIs (concepts or collections) - unordered
            "ordered_members": [],  # member IRIs in order - for OrderedCollection
            "replaced_by_iri": "",
        }
    )

    # Process both Collection and OrderedCollection types
    collection_iris = set()
    for s in graph.subjects(RDF.type, SKOS.Collection):
        collection_iris.add(s)
    for s in graph.subjects(RDF.type, SKOS.OrderedCollection):
        collection_iris.add(s)

    for s in collection_iris:
        iri = str(s)
        data = collection_data[iri]

        # Check if it's an OrderedCollection
        if (s, RDF.type, SKOS.OrderedCollection) in graph:
            data["ordered"] = True

        for p, o in graph.predicate_objects(s):
            if p == SKOS.prefLabel:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["pref_labels"][lang] = str(o)
            elif p == SKOS.definition:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["definitions"][lang] = str(o)
            elif p == SKOS.editorialNote:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["editorial_notes"][lang] = str(o)
            elif p == SKOS.changeNote:
                data["change_note"] = str(o)
            elif p == OWL.deprecated:
                data["is_deprecated"] = str(o).lower() == "true"
            elif p == SKOS.historyNote:
                # historyNote is used for obsoletion reason when deprecated
                data["obsolete_reason"] = str(o)
            elif p == SKOS.member:
                data["members"].append(str(o))
            elif p == SKOS.memberList:
                # Parse RDF List for ordered members
                try:
                    rdf_list = RDFCollection(graph, o)
                    data["ordered_members"] = [str(m) for m in rdf_list]
                except Exception:
                    # If parsing fails, fall back to empty list
                    data["ordered_members"] = []
            elif p == DCTERMS.isReplacedBy:
                data["replaced_by_iri"] = str(o)

    # Second pass: organize by IRI and language
    for iri, data in collection_data.items():
        all_langs = set(data["pref_labels"].keys()) | set(data["definitions"].keys())

        langs_ordered = sorted(all_langs)
        if "en" in langs_ordered:
            langs_ordered.remove("en")
            langs_ordered.insert(0, "en")

        # Only include obsolete_reason if collection is deprecated
        obsolete_reason = data["obsolete_reason"] if data["is_deprecated"] else ""

        for lang in langs_ordered:
            collections_by_iri_lang[iri][lang] = {
                "preferred_label": data["pref_labels"].get(lang, ""),
                "definition": data["definitions"].get(lang, ""),
                "editorial_note": data["editorial_notes"].get(lang, ""),
                "change_note": data["change_note"],
                "obsolete_reason": obsolete_reason,
                "ordered": data["ordered"],
                "members": data["members"],
                "ordered_members": data["ordered_members"],
                "replaced_by_iri": data["replaced_by_iri"],
                "is_deprecated": data["is_deprecated"],
            }

    return dict(collections_by_iri_lang)


def extract_mappings_from_rdf(graph: Graph) -> dict[str, dict]:
    """Extract mapping relations from an RDF graph.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Dict: {concept_iri: {related_matches: [], close_matches: [], ...}}
    """
    mappings: dict[str, dict] = defaultdict(
        lambda: {
            "related_matches": [],
            "close_matches": [],
            "exact_matches": [],
            "narrower_matches": [],
            "broader_matches": [],
        }
    )

    for s in graph.subjects(RDF.type, SKOS.Concept):
        iri = str(s)
        has_mappings = False

        for p, o in graph.predicate_objects(s):
            if p == SKOS.relatedMatch:
                mappings[iri]["related_matches"].append(str(o))
                has_mappings = True
            elif p == SKOS.closeMatch:
                mappings[iri]["close_matches"].append(str(o))
                has_mappings = True
            elif p == SKOS.exactMatch:
                mappings[iri]["exact_matches"].append(str(o))
                has_mappings = True
            elif p == SKOS.narrowMatch:
                mappings[iri]["narrower_matches"].append(str(o))
                has_mappings = True
            elif p == SKOS.broadMatch:
                mappings[iri]["broader_matches"].append(str(o))
                has_mappings = True

        # Only keep entries that have at least one mapping
        if not has_mappings and iri in mappings:
            del mappings[iri]

    return dict(mappings)


def build_concept_to_collections_map(graph: Graph) -> dict[str, list[str]]:
    """Build a mapping from concept IRIs to the collections they belong to.

    This inverts the skos:member relationship.

    Args:
        graph: The RDF graph to analyze.

    Returns:
        Dict: {concept_iri: [collection_iris]}
    """
    concept_to_collections: dict[str, list[str]] = defaultdict(list)

    for collection_iri in graph.subjects(RDF.type, SKOS.Collection):
        for member in graph.objects(collection_iri, SKOS.member):
            member_iri = str(member)
            # Only map if member is a concept (not another collection)
            if (member, RDF.type, SKOS.Concept) in graph:
                concept_to_collections[member_iri].append(str(collection_iri))

    return dict(concept_to_collections)


def build_collection_hierarchy_map(graph: Graph) -> dict[str, list[str]]:
    """Build a mapping from collection IRIs to their parent collections.

    Collections can be members of other collections (hierarchy).

    Args:
        graph: The RDF graph to analyze.

    Returns:
        Dict: {child_collection_iri: [parent_collection_iris]}
    """
    collection_to_parents: dict[str, list[str]] = defaultdict(list)

    for parent_iri in graph.subjects(RDF.type, SKOS.Collection):
        for member in graph.objects(parent_iri, SKOS.member):
            member_iri = str(member)
            # Only map if member is a collection (not a concept)
            if (member, RDF.type, SKOS.Collection) in graph:
                collection_to_parents[member_iri].append(str(parent_iri))

    return dict(collection_to_parents)


def build_concept_to_ordered_collections_map(
    graph: Graph,
) -> dict[str, dict[str, int]]:
    """Build mapping from concept IRIs to ordered collections with positions.

    Args:
        graph: The RDF graph to analyze.

    Returns:
        Dict: {concept_iri: {collection_iri: position}}
        Position is 1-indexed (first member is position 1).
    """
    from rdflib.collection import Collection as RDFCollection

    concept_to_ordered: dict[str, dict[str, int]] = defaultdict(dict)

    for collection_iri in graph.subjects(RDF.type, SKOS.OrderedCollection):
        # Get the memberList
        member_list_node = graph.value(collection_iri, SKOS.memberList)
        if member_list_node:
            try:
                rdf_list = RDFCollection(graph, member_list_node)
                for position, member in enumerate(rdf_list, start=1):
                    member_iri = str(member)
                    # Only map if member is a concept
                    if (member, RDF.type, SKOS.Concept) in graph:
                        concept_to_ordered[member_iri][str(collection_iri)] = position
            except Exception:
                # If parsing fails, skip this collection
                pass

    return dict(concept_to_ordered)


# =============================================================================
# Model Conversion Functions
# =============================================================================


def rdf_concept_scheme_to_v1(data: dict) -> ConceptSchemeV1:
    """Convert extracted concept scheme data to ConceptSchemeV1 model.

    Args:
        data: Dictionary with concept scheme fields.

    Returns:
        ConceptSchemeV1 model instance.
    """
    return ConceptSchemeV1(
        template_version=TEMPLATE_VERSION,
        vocabulary_iri=data.get("vocabulary_iri", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        created_date=data.get("created_date", ""),
        modified_date=data.get("modified_date", ""),
        creator=data.get("creator", ""),
        publisher=data.get("publisher", ""),
        version=data.get("version", ""),
        change_note=data.get("change_note", ""),
        custodian=data.get("custodian", ""),
        catalogue_pid=data.get("catalogue_pid", ""),
    )


def config_to_concept_scheme_v1(
    vocab_config: "config.Vocab",
    rdf_scheme: ConceptSchemeV1 | None = None,
) -> ConceptSchemeV1:
    """Build ConceptSchemeV1 from idranges.toml config with optional RDF fallback.

    Config values override RDF values. RDF fills gaps for empty config fields.
    Warnings are logged for required fields (vocabulary_iri, title) that are
    empty in both sources.

    Args:
        vocab_config: Vocab configuration from idranges.toml.
        rdf_scheme: Optional ConceptSchemeV1 extracted from RDF (for fallback).

    Returns:
        ConceptSchemeV1 model instance with merged data.
    """

    def get_field(
        config_val: str, rdf_val: str, field_name: str, required: bool = False
    ) -> str:
        """Get field value, preferring config over RDF."""
        result = config_val.strip() if config_val else ""
        if not result and rdf_val:
            result = rdf_val.strip() if rdf_val else ""
        if not result and required:
            logger.warning(
                "ConceptScheme field '%s' is empty in both config and RDF.", field_name
            )
        return result

    # Get RDF values (or empty defaults)
    rdf = rdf_scheme or ConceptSchemeV1()

    return ConceptSchemeV1(
        template_version=TEMPLATE_VERSION,
        vocabulary_iri=get_field(
            vocab_config.vocabulary_iri,
            rdf.vocabulary_iri,
            "vocabulary_iri",
            required=True,
        ),
        prefix=get_field(vocab_config.prefix, rdf.prefix, "prefix"),
        title=get_field(vocab_config.title, rdf.title, "title", required=True),
        description=get_field(vocab_config.description, rdf.description, "description"),
        created_date=get_field(
            vocab_config.created_date, rdf.created_date, "created_date"
        ),
        # Auto-generated fields come from RDF only (not in config)
        modified_date=rdf.modified_date,
        version=rdf.version,
        contributor=rdf.contributor,
        # Multi-line fields from config
        creator=get_field(vocab_config.creator, rdf.creator, "creator"),
        publisher=get_field(vocab_config.publisher, rdf.publisher, "publisher"),
        custodian=get_field(vocab_config.custodian, rdf.custodian, "custodian"),
        # URL fields
        catalogue_pid=get_field(
            vocab_config.catalogue_pid, rdf.catalogue_pid, "catalogue_pid"
        ),
        documentation=get_field(
            vocab_config.documentation, rdf.documentation, "documentation"
        ),
        issue_tracker=get_field(
            vocab_config.issue_tracker, rdf.issue_tracker, "issue_tracker"
        ),
        helpdesk=get_field(vocab_config.helpdesk, rdf.helpdesk, "helpdesk"),
        repository=get_field(vocab_config.repository, rdf.repository, "repository"),
        homepage=get_field(vocab_config.homepage, rdf.homepage, "homepage"),
        conforms_to=get_field(vocab_config.conforms_to, rdf.conforms_to, "conforms_to"),
        # Change note from RDF only (not in config)
        change_note=rdf.change_note,
    )


def rdf_concepts_to_v1(
    concepts_data: dict[str, dict[str, dict]],
    concept_to_collections: dict[str, list[str]],
    concept_to_ordered_collections: dict[str, dict[str, int]] | None = None,
    vocab_name: str = "",
) -> list[ConceptV1]:
    """Convert extracted concepts to ConceptV1 models.

    Creates one ConceptV1 row per (concept_iri, language) combination.
    The first row for each concept includes: parent_iris, member_of_collections,
    member_of_ordered_collection, source_vocab_iri/license/rights_holder,
    change_note, obsolete_reason, influenced_by_iris, provenance.
    Subsequent rows (other languages) have structural fields empty but include
    editorial_note per language.

    Args:
        concepts_data: Nested dict from extract_concepts_from_rdf.
        concept_to_collections: Mapping from concept IRI to collection IRIs.
        concept_to_ordered_collections: Mapping from concept IRI to
            {ordered_collection_iri: position}.
        vocab_name: Vocabulary name for provenance URL generation.

    Returns:
        List of ConceptV1 model instances.
    """
    concepts_v1 = []
    concept_to_ordered_collections = concept_to_ordered_collections or {}

    # Use curies converter to compress IRIs
    converter = config.curies_converter

    for concept_iri, lang_data in concepts_data.items():
        is_first_row = True

        # Generate provenance URL (same for all language rows)
        entity_id = extract_entity_id_from_iri(concept_iri)
        provenance_url = build_provenance_url(entity_id, vocab_name)

        # Get deprecation info from any language (it's the same for all)
        first_lang_data = next(iter(lang_data.values()), {})
        is_deprecated = first_lang_data.get("is_deprecated", False)
        obsolete_reason_raw = first_lang_data.get("obsolete_reason", "")
        replaced_by_iri = first_lang_data.get("replaced_by_iri", "")

        # Validate and fix English prefLabel if needed
        en_pref_label = lang_data.get("en", {}).get("preferred_label", "")
        if en_pref_label:
            corrected_label, errors = validate_deprecation(
                pref_label=en_pref_label,
                is_deprecated=is_deprecated,
                history_note=obsolete_reason_raw,
                valid_reasons=OBSOLETION_REASONS_CONCEPTS,
                entity_iri=concept_iri,
                entity_type="concept",
            )
            for error in errors:
                logger.error(error)
            # Update the English prefLabel in the data
            if "en" in lang_data:
                lang_data["en"]["preferred_label"] = corrected_label

        for lang, data in lang_data.items():
            # Compress the concept IRI
            concept_iri_display = converter.compress(concept_iri, passthrough=True)

            # Format alternate labels (join with | separator, no spaces around |)
            alt_labels = data.get("alternate_labels", [])
            alt_labels_str = " | ".join(alt_labels) if alt_labels else ""

            # Editorial note is per-language
            editorial_note = data.get("editorial_note", "")

            # Only include structural data in first row
            if is_first_row:
                # Format parent IRIs
                parent_iris = data.get("parent_iris", [])
                parent_iris_strs = [
                    converter.compress(p, passthrough=True) for p in parent_iris
                ]
                parent_iris_str = " ".join(parent_iris_strs)

                # Format member_of_collections (regular collections only)
                collections = concept_to_collections.get(concept_iri, [])
                collections_strs = [
                    converter.compress(c, passthrough=True) for c in collections
                ]
                member_of_collections_str = " ".join(collections_strs)

                # Format member_of_ordered_collection (format: collIRI # pos)
                ordered_colls = concept_to_ordered_collections.get(concept_iri, {})
                ordered_parts = []
                for coll_iri, position in ordered_colls.items():
                    coll_display = converter.compress(coll_iri, passthrough=True)
                    ordered_parts.append(f"{coll_display} # {position}")
                member_of_ordered_collection_str = " ".join(ordered_parts)

                # Source vocab attribution
                source_vocab_iri = data.get("source_vocab_iri", "")
                source_vocab_license = data.get("source_vocab_license", "")
                source_vocab_rights_holder = data.get("source_vocab_rights_holder", "")

                # Notes - handle replaced_by_iri
                change_note = data.get("change_note", "")
                if replaced_by_iri:
                    # Format change_note with replaced_by notation
                    compressed_replacement = converter.compress(
                        replaced_by_iri, passthrough=True
                    )
                    change_note = format_change_note_with_replaced_by(
                        compressed_replacement
                    )
                obsolete_reason = data.get("obsolete_reason", "")

                # Influenced by IRIs
                influenced_iris = data.get("influenced_by_iris", [])
                influenced_iris_strs = [
                    converter.compress(i, passthrough=True) for i in influenced_iris
                ]
                influenced_by_iris_str = " ".join(influenced_iris_strs)

                provenance = provenance_url
                is_first_row = False
            else:
                parent_iris_str = ""
                member_of_collections_str = ""
                member_of_ordered_collection_str = ""
                source_vocab_iri = ""
                source_vocab_license = ""
                source_vocab_rights_holder = ""
                change_note = ""
                obsolete_reason = ""
                influenced_by_iris_str = ""
                provenance = ""

            concepts_v1.append(
                ConceptV1(
                    concept_iri=concept_iri_display,
                    language_code=lang,
                    preferred_label=data.get("preferred_label", ""),
                    definition=data.get("definition", ""),
                    alternate_labels=alt_labels_str,
                    parent_iris=parent_iris_str,
                    member_of_collections=member_of_collections_str,
                    member_of_ordered_collection=member_of_ordered_collection_str,
                    provenance=provenance,
                    change_note=change_note,
                    editorial_note=editorial_note,
                    obsolete_reason=obsolete_reason,
                    influenced_by_iris=influenced_by_iris_str,
                    source_vocab_iri=source_vocab_iri,
                    source_vocab_license=source_vocab_license,
                    source_vocab_rights_holder=source_vocab_rights_holder,
                )
            )

    return concepts_v1


def rdf_collections_to_v1(
    collections_data: dict[str, dict[str, dict]],
    collection_to_parents: dict[str, list[str]],
    vocab_name: str = "",
) -> list[CollectionV1]:
    """Convert extracted collections to CollectionV1 models.

    Creates one CollectionV1 row per (collection_iri, language) combination.
    The first row includes: parent_collection_iris, ordered, change_note,
    obsolete_reason, provenance.
    Subsequent rows (other languages) have structural fields empty but include
    editorial_note per language.

    Args:
        collections_data: Nested dict from extract_collections_from_rdf.
        collection_to_parents: Mapping from collection IRI to parent collection IRIs.
        vocab_name: Vocabulary name for provenance URL generation.

    Returns:
        List of CollectionV1 model instances.
    """
    collections_v1 = []

    converter = config.curies_converter

    for collection_iri, lang_data in collections_data.items():
        is_first_row = True

        # Generate provenance URL (same for all language rows)
        entity_id = extract_entity_id_from_iri(collection_iri)
        provenance_url = build_provenance_url(entity_id, vocab_name)

        # Get deprecation info from any language (it's the same for all)
        first_lang_data = next(iter(lang_data.values()), {})
        is_deprecated = first_lang_data.get("is_deprecated", False)
        obsolete_reason_raw = first_lang_data.get("obsolete_reason", "")
        replaced_by_iri = first_lang_data.get("replaced_by_iri", "")

        # Validate and fix English prefLabel if needed
        en_pref_label = lang_data.get("en", {}).get("preferred_label", "")
        if en_pref_label:
            corrected_label, errors = validate_deprecation(
                pref_label=en_pref_label,
                is_deprecated=is_deprecated,
                history_note=obsolete_reason_raw,
                valid_reasons=OBSOLETION_REASONS_COLLECTIONS,
                entity_iri=collection_iri,
                entity_type="collection",
            )
            for error in errors:
                logger.error(error)
            # Update the English prefLabel in the data
            if "en" in lang_data:
                lang_data["en"]["preferred_label"] = corrected_label

        for lang, data in lang_data.items():
            collection_iri_display = converter.compress(
                collection_iri, passthrough=True
            )

            # Editorial note is per-language
            editorial_note = data.get("editorial_note", "")

            if is_first_row:
                # Format parent collection IRIs
                parents = collection_to_parents.get(collection_iri, [])
                parents_strs = [
                    converter.compress(p, passthrough=True) for p in parents
                ]
                parent_iris_str = " ".join(parents_strs)

                # Ordered flag
                ordered = "Yes" if data.get("ordered", False) else ""

                # Notes - handle replaced_by_iri
                change_note = data.get("change_note", "")
                if replaced_by_iri:
                    # Format change_note with replaced_by notation
                    compressed_replacement = converter.compress(
                        replaced_by_iri, passthrough=True
                    )
                    change_note = format_change_note_with_replaced_by(
                        compressed_replacement
                    )
                obsolete_reason = data.get("obsolete_reason", "")

                provenance = provenance_url
                is_first_row = False
            else:
                parent_iris_str = ""
                ordered = ""
                change_note = ""
                obsolete_reason = ""
                provenance = ""

            collections_v1.append(
                CollectionV1(
                    collection_iri=collection_iri_display,
                    language_code=lang,
                    preferred_label=data.get("preferred_label", ""),
                    definition=data.get("definition", ""),
                    parent_collection_iris=parent_iris_str,
                    ordered=ordered,
                    provenance=provenance,
                    change_note=change_note,
                    editorial_note=editorial_note,
                    obsolete_reason=obsolete_reason,
                )
            )

    return collections_v1


def rdf_mappings_to_v1(mappings_data: dict[str, dict]) -> list[MappingV1]:
    """Convert extracted mappings to MappingV1 models.

    Args:
        mappings_data: Dict from extract_mappings_from_rdf.

    Returns:
        List of MappingV1 model instances.
    """
    mappings_v1 = []

    converter = config.curies_converter

    for concept_iri, data in mappings_data.items():
        concept_iri_display = converter.compress(concept_iri, passthrough=True)

        # Format each mapping type as space-separated IRIs
        related = " ".join(
            converter.compress(m, passthrough=True)
            for m in data.get("related_matches", [])
        )
        close = " ".join(
            converter.compress(m, passthrough=True)
            for m in data.get("close_matches", [])
        )
        exact = " ".join(
            converter.compress(m, passthrough=True)
            for m in data.get("exact_matches", [])
        )
        narrower = " ".join(
            converter.compress(m, passthrough=True)
            for m in data.get("narrower_matches", [])
        )
        broader = " ".join(
            converter.compress(m, passthrough=True)
            for m in data.get("broader_matches", [])
        )

        mappings_v1.append(
            MappingV1(
                concept_iri=concept_iri_display,
                related_matches=related,
                close_matches=close,
                exact_matches=exact,
                narrower_matches=narrower,
                broader_matches=broader,
            )
        )

    return mappings_v1


def build_prefixes_v1() -> list[PrefixV1]:
    """Build prefix list from the current curies converter.

    Returns:
        List of PrefixV1 model instances.
    """
    prefixes_v1 = []

    for prefix, namespace in config.curies_converter.prefix_map.items():
        prefixes_v1.append(PrefixV1(prefix=prefix, namespace=namespace))

    return prefixes_v1


# =============================================================================
# ID Range Info Functions
# =============================================================================


def extract_used_ids(
    concepts: list[ConceptV1],
    collections: list[CollectionV1],
    vocab_config: "config.Vocab",
) -> set[int]:
    """Extract numeric IDs used by concepts and collections.

    Parses concept and collection IRIs to extract numeric IDs that match
    the vocabulary's ID pattern (based on permanent_iri_part and id_length).

    Args:
        concepts: List of ConceptV1 model instances.
        collections: List of CollectionV1 model instances.
        vocab_config: Vocab config with permanent_iri_part and id_length.

    Returns:
        Set of integer IDs that are in use.
    """
    import re

    used_ids: set[int] = set()

    # Build regex pattern for extracting numeric IDs
    # IDs are at the end of the IRI and have a fixed length
    id_length = vocab_config.id_length
    pattern = re.compile(rf"(\d{{{id_length}}})$")

    # Get permanent IRI part for filtering
    permanent_iri = str(vocab_config.permanent_iri_part).rstrip("/")

    # Get curies converter for expanding CURIEs
    converter = config.curies_converter

    # Process concepts - extract from concept_iri field
    seen_iris: set[str] = set()
    for concept in concepts:
        iri = concept.concept_iri
        if not iri or iri in seen_iris:
            continue
        seen_iris.add(iri)

        # Expand CURIE if needed
        expanded_iri = expand_curie(iri, converter)

        # Check if IRI belongs to this vocabulary
        if not expanded_iri.startswith(permanent_iri):
            continue

        # Extract numeric ID
        match = pattern.search(expanded_iri)
        if match:
            used_ids.add(int(match.group(1)))

    # Process collections - extract from collection_iri field
    seen_iris.clear()
    for collection in collections:
        iri = collection.collection_iri
        if not iri or iri in seen_iris:
            continue
        seen_iris.add(iri)

        # Expand CURIE if needed
        expanded_iri = expand_curie(iri, converter)

        # Check if IRI belongs to this vocabulary
        if not expanded_iri.startswith(permanent_iri):
            continue

        # Extract numeric ID
        match = pattern.search(expanded_iri)
        if match:
            used_ids.add(int(match.group(1)))

    return used_ids


def build_id_range_info(
    vocab_config: "config.Vocab",
    used_ids: set[int],
) -> list[IDRangeInfoV1]:
    """Build ID range info rows from config and usage data.

    Args:
        vocab_config: Vocab config with id_range list and id_length.
        used_ids: Set of integer IDs that are in use.

    Returns:
        List of IDRangeInfoV1 model instances.
    """
    rows: list[IDRangeInfoV1] = []
    id_length = vocab_config.id_length

    for idr in vocab_config.id_range:
        # Determine identifier: gh_name or orcid fallback
        if idr.gh_name:
            identifier = idr.gh_name
        elif idr.orcid:
            identifier = str(idr.orcid)
        else:
            identifier = "unknown"

        # Format range string with zero-padding
        range_str = f"{idr.first_id:0{id_length}d} - {idr.last_id:0{id_length}d}"

        # Calculate unused IDs in this range
        range_ids = set(range(idr.first_id, idr.last_id + 1))
        unused_in_range = range_ids - used_ids

        if not unused_in_range:
            unused_str = "all used"
        else:
            first_unused = min(unused_in_range)
            unused_str = (
                f"next unused: {first_unused:0{id_length}d}, "
                f"unused: {len(unused_in_range)}"
            )

        rows.append(
            IDRangeInfoV1(
                gh_name=identifier,
                id_range=range_str,
                unused_ids=unused_str,
            )
        )

    return rows


# =============================================================================
# Excel Export Function
# =============================================================================


def export_vocabulary_v1(
    concept_scheme: ConceptSchemeV1,
    concepts: list[ConceptV1],
    collections: list[CollectionV1],
    mappings: list[MappingV1],
    prefixes: list[PrefixV1],
    output_path: Path,
    id_ranges: list[IDRangeInfoV1] | None = None,
) -> None:
    """Export v1.0 vocabulary data to Excel.

    Uses export_to_xlsx() for each sheet.

    Args:
        concept_scheme: ConceptSchemeV1 model instance.
        concepts: List of ConceptV1 model instances.
        collections: List of CollectionV1 model instances.
        mappings: List of MappingV1 model instances.
        prefixes: List of PrefixV1 model instances.
        output_path: Path to save the Excel file.
        id_ranges: Optional list of IDRangeInfoV1 model instances. If provided,
                  an "ID Ranges" sheet is added showing contributor allocations.
    """
    # 1. Concept Scheme (key-value format, read-only)
    kv_config = XLSXKeyValueConfig(title=CONCEPT_SCHEME_SHEET_TITLE)
    export_to_xlsx(
        concept_scheme,
        output_path,
        format_type="keyvalue",
        config=kv_config,
        sheet_name=CONCEPT_SCHEME_SHEET_NAME,
    )

    # 2. Concepts (table format)
    if concepts:
        table_config = XLSXTableConfig(title="Concepts", freeze_panes=True)
        export_to_xlsx(
            concepts,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Concepts",
        )
    else:
        # Export empty concepts sheet with just headers
        empty_concept = [ConceptV1()]
        table_config = XLSXTableConfig(title="Concepts", freeze_panes=True)
        export_to_xlsx(
            empty_concept,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Concepts",
        )

    # 3. Collections (table format)
    if collections:
        table_config = XLSXTableConfig(title="Collections")
        export_to_xlsx(
            collections,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Collections",
        )
    else:
        empty_collection = [CollectionV1()]
        table_config = XLSXTableConfig(title="Collections")
        export_to_xlsx(
            empty_collection,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Collections",
        )

    # 4. Mappings (table format)
    if mappings:
        table_config = XLSXTableConfig(title="Mappings")
        export_to_xlsx(
            mappings,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Mappings",
        )
    else:
        empty_mapping = [MappingV1()]
        table_config = XLSXTableConfig(title="Mappings")
        export_to_xlsx(
            empty_mapping,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name="Mappings",
        )

    # 5. ID Ranges (table format, read-only)
    if id_ranges:
        table_config = XLSXTableConfig(title=ID_RANGES_SHEET_TITLE)
        export_to_xlsx(
            id_ranges,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name=ID_RANGES_SHEET_NAME,
        )
    else:
        # Export empty ID Ranges sheet with just headers
        empty_id_range = [IDRangeInfoV1()]
        table_config = XLSXTableConfig(title=ID_RANGES_SHEET_TITLE)
        export_to_xlsx(
            empty_id_range,
            output_path,
            format_type="table",
            config=table_config,
            sheet_name=ID_RANGES_SHEET_NAME,
        )

    # 6. Prefixes (table format)
    table_config = XLSXTableConfig(title=PREFIXES_SHEET_TITLE)
    export_to_xlsx(
        prefixes,
        output_path,
        format_type="table",
        config=table_config,
        sheet_name=PREFIXES_SHEET_NAME,
    )

    # Reorder sheets and set freeze panes
    from openpyxl import load_workbook

    wb = load_workbook(output_path)
    _reorder_sheets(wb)

    # Set freeze panes for Concepts sheet
    if "Concepts" in wb.sheetnames:
        wb["Concepts"].freeze_panes = "A5"

    wb.save(output_path)
    wb.close()


def _reorder_sheets(wb) -> None:
    """Reorder sheets to match expected template order."""
    expected_order = [
        CONCEPT_SCHEME_SHEET_NAME,
        "Concepts",
        "Collections",
        "Mappings",
        ID_RANGES_SHEET_NAME,
        PREFIXES_SHEET_NAME,
    ]

    current_sheets = wb.sheetnames

    new_order = []
    for sheet_name in expected_order:
        if sheet_name in current_sheets:
            new_order.append(sheet_name)
    for sheet_name in current_sheets:
        if sheet_name not in new_order:
            new_order.append(sheet_name)

    for idx, sheet_name in enumerate(new_order):
        wb.move_sheet(sheet_name, offset=idx - wb.sheetnames.index(sheet_name))


# =============================================================================
# Main Converter Function
# =============================================================================


def rdf_to_excel_v1(
    file_to_convert_path: Path,
    output_file_path: Path | None = None,
    vocab_config: "config.Vocab | None" = None,
) -> Path:
    """Convert an RDF vocabulary to v1.0 Excel template.

    If vocab_config is provided, ConceptScheme metadata is merged from config
    (config values override RDF, RDF fills gaps). The "Concept Scheme (read-only)"
    sheet is populated from this merged data.

    Args:
        file_to_convert_path: Path to the RDF file (.ttl, .rdf, etc.).
        output_file_path: Optional path for output Excel file.
                         Defaults to same name with .xlsx extension.
        vocab_config: Optional Vocab config from idranges.toml. If provided,
                     scheme metadata is merged (config overrides RDF).

    Returns:
        Path to the generated Excel file.

    Raises:
        ValueError: If the input file is not a supported RDF format.
    """
    if file_to_convert_path.suffix.lower() not in RDF_FILE_ENDINGS:
        msg = (
            "Files for conversion must end with one of the RDF file formats: "
            f"'{', '.join(RDF_FILE_ENDINGS.keys())}'"
        )
        raise ValueError(msg)

    vocab_name = file_to_convert_path.stem.lower()

    # Set up curies converter for this vocabulary
    config.curies_converter = config.CURIES_CONVERTER_MAP.get(
        vocab_name, config.curies_converter
    )

    # Parse RDF file
    logger.info("Parsing RDF file: %s", file_to_convert_path)
    graph = Graph().parse(
        str(file_to_convert_path),
        format=RDF_FILE_ENDINGS[file_to_convert_path.suffix.lower()],
    )

    # Extract data from RDF
    logger.debug("Extracting concept scheme...")
    cs_data = extract_concept_scheme_from_rdf(graph)

    logger.debug("Extracting concepts...")
    concepts_data = extract_concepts_from_rdf(graph)

    logger.debug("Extracting collections...")
    collections_data = extract_collections_from_rdf(graph)

    logger.debug("Extracting mappings...")
    mappings_data = extract_mappings_from_rdf(graph)

    logger.debug("Building concept-to-collections map...")
    concept_to_collections = build_concept_to_collections_map(graph)

    logger.debug("Building concept-to-ordered-collections map...")
    concept_to_ordered_collections = build_concept_to_ordered_collections_map(graph)

    logger.debug("Building collection hierarchy map...")
    collection_to_parents = build_collection_hierarchy_map(graph)

    # Convert to v1.0 models
    logger.debug("Converting to v1.0 models...")

    # Build ConceptScheme - either from config (merged with RDF) or RDF only
    if vocab_config is not None:
        logger.debug(
            "Using vocab config for ConceptScheme metadata (config overrides RDF)."
        )
        rdf_scheme = rdf_concept_scheme_to_v1(cs_data)
        concept_scheme_v1 = config_to_concept_scheme_v1(vocab_config, rdf_scheme)
    else:
        concept_scheme_v1 = rdf_concept_scheme_to_v1(cs_data)

    concepts_v1 = rdf_concepts_to_v1(
        concepts_data,
        concept_to_collections,
        concept_to_ordered_collections,
        vocab_name,
    )
    collections_v1 = rdf_collections_to_v1(
        collections_data, collection_to_parents, vocab_name
    )
    mappings_v1 = rdf_mappings_to_v1(mappings_data)
    prefixes_v1 = build_prefixes_v1()

    # Build ID range info if vocab_config is provided
    id_ranges_v1: list[IDRangeInfoV1] | None = None
    if vocab_config is not None and vocab_config.id_range:
        logger.debug("Building ID range info...")
        used_ids = extract_used_ids(concepts_v1, collections_v1, vocab_config)
        id_ranges_v1 = build_id_range_info(vocab_config, used_ids)

    # Determine output path
    if output_file_path is None:
        output_file_path = file_to_convert_path.with_suffix(".xlsx")

    # Export to Excel
    logger.info("Exporting to Excel: %s", output_file_path)
    export_vocabulary_v1(
        concept_scheme_v1,
        concepts_v1,
        collections_v1,
        mappings_v1,
        prefixes_v1,
        output_file_path,
        id_ranges=id_ranges_v1,
    )

    logger.info("Conversion complete: %s", output_file_path)
    return output_file_path


# =============================================================================
# XLSX -> RDF Conversion (Step 3)
# =============================================================================

# --- Aggregated Data Structures ---

# TODO Do we need these dataclasses, or can we just use pydantic models?


@dataclass
class AggregatedConcept:
    """Aggregated concept data from multiple XLSX rows (one per language)."""

    iri: str
    pref_labels: dict[str, str] = field(default_factory=dict)  # {lang: label}
    definitions: dict[str, str] = field(default_factory=dict)  # {lang: definition}
    alt_labels: dict[str, list[str]] = field(default_factory=dict)  # {lang: [labels]}
    editorial_notes: dict[str, str] = field(default_factory=dict)  # {lang: note}
    parent_iris: list[str] = field(default_factory=list)
    member_of_collections: list[str] = field(default_factory=list)
    # {ordered_collection_iri: position}
    ordered_collection_positions: dict[str, int] = field(default_factory=dict)
    source_vocab_iri: str = ""
    source_vocab_license: str = ""
    source_vocab_rights_holder: str = ""
    change_note: str = ""
    obsolete_reason: str = ""
    influenced_by_iris: list[str] = field(default_factory=list)
    replaced_by_iri: str = ""


@dataclass
class AggregatedCollection:
    """Aggregated collection data from multiple XLSX rows (one per language)."""

    iri: str
    pref_labels: dict[str, str] = field(default_factory=dict)  # {lang: label}
    definitions: dict[str, str] = field(default_factory=dict)  # {lang: definition}
    editorial_notes: dict[str, str] = field(default_factory=dict)  # {lang: note}
    parent_collection_iris: list[str] = field(default_factory=list)
    ordered: bool = False
    change_note: str = ""
    obsolete_reason: str = ""
    replaced_by_iri: str = ""


# --- XLSX Reading Functions ---


def read_concept_scheme_v1(filepath: Path) -> ConceptSchemeV1:
    """Read ConceptScheme data from v1.0 XLSX file.

    Args:
        filepath: Path to the XLSX file.

    Returns:
        ConceptSchemeV1 model instance.
    """
    return import_from_xlsx(
        filepath,
        ConceptSchemeV1,
        format_type="keyvalue",
        sheet_name=CONCEPT_SCHEME_SHEET_NAME,
    )


def read_concepts_v1(filepath: Path) -> list[ConceptV1]:
    """Read Concepts from v1.0 XLSX file.

    Args:
        filepath: Path to the XLSX file.

    Returns:
        List of ConceptV1 model instances (one per row).
    """
    # Must match the config used during export
    config = XLSXTableConfig(title="Concepts")
    return import_from_xlsx(
        filepath,
        ConceptV1,
        format_type="table",
        config=config,
        sheet_name="Concepts",
    )


def read_collections_v1(filepath: Path) -> list[CollectionV1]:
    """Read Collections from v1.0 XLSX file.

    Args:
        filepath: Path to the XLSX file.

    Returns:
        List of CollectionV1 model instances (one per row).
    """
    # Must match the config used during export
    config = XLSXTableConfig(title="Collections")
    return import_from_xlsx(
        filepath,
        CollectionV1,
        format_type="table",
        config=config,
        sheet_name="Collections",
    )


def read_mappings_v1(filepath: Path) -> list[MappingV1]:
    """Read Mappings from v1.0 XLSX file.

    Args:
        filepath: Path to the XLSX file.

    Returns:
        List of MappingV1 model instances (one per row).
    """
    # Must match the config used during export
    config = XLSXTableConfig(title="Mappings")
    return import_from_xlsx(
        filepath,
        MappingV1,
        format_type="table",
        config=config,
        sheet_name="Mappings",
    )


def read_prefixes_v1(filepath: Path) -> list[PrefixV1]:
    """Read Prefixes from v1.0 XLSX file.

    Args:
        filepath: Path to the XLSX file.

    Returns:
        List of PrefixV1 model instances.
    """
    # Must match the config used during export
    config = XLSXTableConfig(title=PREFIXES_SHEET_TITLE)
    return import_from_xlsx(
        filepath,
        PrefixV1,
        format_type="table",
        config=config,
        sheet_name=PREFIXES_SHEET_NAME,
    )


# --- CURIE Handling ---


def build_curies_converter_from_prefixes(prefixes: list[PrefixV1]) -> curies.Converter:
    """Build a curies converter from prefix list.

    Args:
        prefixes: List of PrefixV1 with prefix and namespace.

    Returns:
        Configured curies.Converter.
    """
    records = [
        curies.Record(prefix=p.prefix, uri_prefix=p.namespace)
        for p in prefixes
        if p.prefix and p.namespace
    ]
    return curies.Converter(records)


def expand_curie(curie_or_iri: str, converter: curies.Converter) -> str:
    """Expand a CURIE to full IRI, or return as-is if already an IRI.

    Args:
        curie_or_iri: CURIE (e.g., "ex:0001") or full IRI.
        converter: Curies converter to use.

    Returns:
        Full IRI string.
    """
    if not curie_or_iri:
        return ""
    # Try to expand; if it fails or returns None, assume it's already an IRI
    expanded = converter.expand(curie_or_iri)
    return expanded if expanded else curie_or_iri


def expand_iri_list(iri_string: str, converter: curies.Converter) -> list[str]:
    """Expand a space-separated string of CURIEs/IRIs to list of full IRIs.

    Args:
        iri_string: Space-separated CURIEs or IRIs.
        converter: Curies converter to use.

    Returns:
        List of full IRI strings.
    """
    if not iri_string or not iri_string.strip():
        return []
    return [expand_curie(part.strip(), converter) for part in iri_string.split()]


# --- Deprecation Handling Functions ---

OBSOLETE_PREFIX = "OBSOLETE "


def parse_replaced_by_from_change_note(change_note: str) -> str | None:
    """Extract IRI from 'replaced_by <IRI>' notation in change note.

    The change note may contain other text. Only lines starting with
    'replaced_by ' are parsed. Returns the first match.

    Args:
        change_note: The change note text to parse.

    Returns:
        The IRI/CURIE string if found, None otherwise.
    """
    if not change_note:
        return None

    for line in change_note.split("\n"):
        line = line.strip()
        if line.lower().startswith("replaced_by "):
            # Extract the IRI (everything after "replaced_by ")
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                return parts[1].strip()
    return None


def format_change_note_with_replaced_by(replaced_by_iri: str) -> str:
    """Format a change note with replaced_by notation.

    Args:
        replaced_by_iri: The IRI of the replacement concept/collection.

    Returns:
        Formatted change note string.
    """
    return f"replaced_by {replaced_by_iri}"


def validate_deprecation(
    pref_label: str,
    is_deprecated: bool,
    history_note: str,
    valid_reasons: list[str],
    entity_iri: str,
    entity_type: str,
) -> tuple[str, list[str]]:
    """Validate deprecation consistency and optionally fix prefLabel.

    Validation rules:
    1. If prefLabel starts with "OBSOLETE " but owl:deprecated is NOT true -> ERROR
    2. If owl:deprecated true but historyNote not in valid_reasons -> ERROR
    3. If owl:deprecated true + valid historyNote + no "OBSOLETE " prefix -> add prefix

    Args:
        pref_label: The English preferred label.
        is_deprecated: Whether owl:deprecated is true.
        history_note: The skos:historyNote value (obsoletion reason).
        valid_reasons: List of valid obsoletion reason strings.
        entity_iri: IRI of the concept/collection (for error messages).
        entity_type: "concept" or "collection" (for error messages).

    Returns:
        Tuple of (corrected_pref_label, list_of_error_messages).
        The corrected_pref_label may have "OBSOLETE " prefix added if needed.
    """
    errors: list[str] = []
    corrected_label = pref_label
    has_obsolete_prefix = pref_label.startswith(OBSOLETE_PREFIX)

    # Rule 1: OBSOLETE prefix without owl:deprecated -> ERROR
    if has_obsolete_prefix and not is_deprecated:
        errors.append(
            f"{entity_type.capitalize()} {entity_iri}: prefLabel starts with "
            f"'{OBSOLETE_PREFIX}' but owl:deprecated is not set to true."
        )

    # Rule 2: owl:deprecated true without valid historyNote -> ERROR
    if is_deprecated and history_note not in valid_reasons:
        errors.append(
            f"{entity_type.capitalize()} {entity_iri}: owl:deprecated is true but "
            f"skos:historyNote '{history_note}' is not a valid obsoletion reason."
        )

    # Rule 3: owl:deprecated true + valid historyNote + no prefix -> add prefix
    if is_deprecated and history_note in valid_reasons and not has_obsolete_prefix:
        corrected_label = OBSOLETE_PREFIX + pref_label

    return corrected_label, errors


# --- Aggregation Functions ---


def parse_ordered_collection_positions(
    position_string: str, converter: curies.Converter
) -> dict[str, int]:
    """Parse ordered collection position string to dict.

    Format: "collIRI # pos" or "collIRI#pos" with optional whitespace.
    Multiple entries are space-separated (outside the # separator).

    Args:
        position_string: String like "ex:coll1 # 1 ex:coll2 # 2"
        converter: Curies converter for IRI expansion.

    Returns:
        Dict mapping collection IRI to position (1-indexed).
    """
    if not position_string or not position_string.strip():
        return {}

    result: dict[str, int] = {}

    # Split by whitespace, but we need to handle "collIRI # pos" as a unit
    # Strategy: first split by "#" to find each entry
    parts = position_string.split("#")

    # Each part except first has: "pos [collIRI...]"
    # Each part except last has: "[...collIRI]"
    for i in range(len(parts) - 1):
        # Get the collection IRI (last token before #)
        left_tokens = parts[i].strip().split()
        if not left_tokens:
            continue
        coll_curie = left_tokens[-1]

        # Get the position (first token after #)
        right_tokens = parts[i + 1].strip().split()
        if not right_tokens:
            continue
        try:
            position = int(right_tokens[0])
        except ValueError:
            continue

        coll_iri = expand_curie(coll_curie, converter)
        result[coll_iri] = position

    return result


def aggregate_concepts(
    concept_rows: list[ConceptV1], converter: curies.Converter
) -> dict[str, AggregatedConcept]:
    """Aggregate multi-row concept data into single AggregatedConcept per IRI.

    The v1.0 template has one row per (concept_iri, language). This function
    merges them back:
    - First row for each IRI contains structural data (parent_iris, etc.)
    - All rows contribute language-specific data (pref_label, definition,
      alt_labels, editorial_note)

    Also validates deprecation consistency and auto-adds "OBSOLETE " prefix
    to English prefLabel if needed.

    Args:
        concept_rows: List of ConceptV1 from XLSX.
        converter: Curies converter for IRI expansion.

    Returns:
        Dict mapping full IRI to AggregatedConcept.
    """
    concepts: dict[str, AggregatedConcept] = {}

    for row in concept_rows:
        # Skip empty rows
        if not row.concept_iri:
            continue

        iri = expand_curie(row.concept_iri, converter)

        if iri not in concepts:
            # First row for this concept - create new entry with structural data
            # Parse replaced_by from change_note
            change_note = row.change_note or ""
            replaced_by_curie = parse_replaced_by_from_change_note(change_note)
            replaced_by_iri = (
                expand_curie(replaced_by_curie, converter) if replaced_by_curie else ""
            )

            concepts[iri] = AggregatedConcept(
                iri=iri,
                parent_iris=expand_iri_list(row.parent_iris, converter),
                member_of_collections=expand_iri_list(
                    row.member_of_collections, converter
                ),
                ordered_collection_positions=parse_ordered_collection_positions(
                    row.member_of_ordered_collection, converter
                ),
                source_vocab_iri=expand_curie(row.source_vocab_iri, converter)
                if row.source_vocab_iri
                else "",
                source_vocab_license=row.source_vocab_license or "",
                source_vocab_rights_holder=row.source_vocab_rights_holder or "",
                change_note=change_note,
                obsolete_reason=row.obsolete_reason or "",
                influenced_by_iris=expand_iri_list(row.influenced_by_iris, converter),
                replaced_by_iri=replaced_by_iri,
            )

        concept = concepts[iri]

        # Add language-specific data
        lang = row.language_code or "en"
        if row.preferred_label:
            concept.pref_labels[lang] = row.preferred_label
        if row.definition:
            concept.definitions[lang] = row.definition
        if row.alternate_labels:
            # Split by "|" separator (with or without spaces), trim each label
            labels = [lbl.strip() for lbl in row.alternate_labels.split("|")]
            labels = [lbl for lbl in labels if lbl]  # Remove empty strings
            concept.alt_labels[lang] = labels
        if row.editorial_note:
            concept.editorial_notes[lang] = row.editorial_note

    # Second pass: validate deprecation for English prefLabels
    for iri, concept in concepts.items():
        en_pref_label = concept.pref_labels.get("en", "")
        if en_pref_label:
            is_deprecated = bool(concept.obsolete_reason)
            corrected_label, errors = validate_deprecation(
                pref_label=en_pref_label,
                is_deprecated=is_deprecated,
                history_note=concept.obsolete_reason,
                valid_reasons=OBSOLETION_REASONS_CONCEPTS,
                entity_iri=iri,
                entity_type="concept",
            )
            for error in errors:
                logger.error(error)
            # Update the English prefLabel
            concept.pref_labels["en"] = corrected_label

    return concepts


def aggregate_collections(
    collection_rows: list[CollectionV1], converter: curies.Converter
) -> dict[str, AggregatedCollection]:
    """Aggregate multi-row collection data into single AggregatedCollection per IRI.

    The v1.0 template has one row per (collection_iri, language). This function
    merges them back:
    - First row for each IRI contains structural data (parent_iris, ordered, etc.)
    - All rows contribute language-specific data (pref_label, definition,
      editorial_note)

    Also validates deprecation consistency and auto-adds "OBSOLETE " prefix
    to English prefLabel if needed.

    Args:
        collection_rows: List of CollectionV1 from XLSX.
        converter: Curies converter for IRI expansion.

    Returns:
        Dict mapping full IRI to AggregatedCollection.
    """
    collections: dict[str, AggregatedCollection] = {}

    for row in collection_rows:
        # Skip empty rows
        if not row.collection_iri:
            continue

        iri = expand_curie(row.collection_iri, converter)

        if iri not in collections:
            # First row for this collection - create new entry with structural data
            # Parse "Yes" as True for ordered flag
            is_ordered = row.ordered.strip().lower() == "yes" if row.ordered else False

            # Parse replaced_by from change_note
            change_note = row.change_note or ""
            replaced_by_curie = parse_replaced_by_from_change_note(change_note)
            replaced_by_iri = (
                expand_curie(replaced_by_curie, converter) if replaced_by_curie else ""
            )

            collections[iri] = AggregatedCollection(
                iri=iri,
                parent_collection_iris=expand_iri_list(
                    row.parent_collection_iris, converter
                ),
                ordered=is_ordered,
                change_note=change_note,
                obsolete_reason=row.obsolete_reason or "",
                replaced_by_iri=replaced_by_iri,
            )

        collection = collections[iri]

        # Add language-specific data
        lang = row.language_code or "en"
        if row.preferred_label:
            collection.pref_labels[lang] = row.preferred_label
        if row.definition:
            collection.definitions[lang] = row.definition
        if row.editorial_note:
            collection.editorial_notes[lang] = row.editorial_note

    # Second pass: validate deprecation for English prefLabels
    for iri, collection in collections.items():
        en_pref_label = collection.pref_labels.get("en", "")
        if en_pref_label:
            is_deprecated = bool(collection.obsolete_reason)
            corrected_label, errors = validate_deprecation(
                pref_label=en_pref_label,
                is_deprecated=is_deprecated,
                history_note=collection.obsolete_reason,
                valid_reasons=OBSOLETION_REASONS_COLLECTIONS,
                entity_iri=iri,
                entity_type="collection",
            )
            for error in errors:
                logger.error(error)
            # Update the English prefLabel
            collection.pref_labels["en"] = corrected_label

    return collections


# --- Inverse Relationship Builders ---


def build_collection_members_from_concepts(
    concepts: dict[str, AggregatedConcept],
) -> dict[str, list[str]]:
    """Build collection -> members map from concept membership data.

    Inverts the concept.member_of_collections relationship.

    Args:
        concepts: Dict of aggregated concepts.

    Returns:
        Dict: {collection_iri: [member_concept_iris]}
    """
    collection_members: dict[str, list[str]] = defaultdict(list)

    for concept_iri, concept in concepts.items():
        for collection_iri in concept.member_of_collections:
            collection_members[collection_iri].append(concept_iri)

    return dict(collection_members)


def build_narrower_map(
    concepts: dict[str, AggregatedConcept],
) -> dict[str, list[str]]:
    """Build parent -> children (narrower) map from broader relationships.

    Inverts the concept.parent_iris (broader) relationship.

    Args:
        concepts: Dict of aggregated concepts.

    Returns:
        Dict: {parent_iri: [child_iris]}
    """
    narrower: dict[str, list[str]] = defaultdict(list)

    for concept_iri, concept in concepts.items():
        for parent_iri in concept.parent_iris:
            narrower[parent_iri].append(concept_iri)

    return dict(narrower)


def build_ordered_collection_members(
    concepts: dict[str, AggregatedConcept],
) -> dict[str, list[str]]:
    """Build ordered collection -> ordered members list from concept positions.

    Uses the concept.ordered_collection_positions to build ordered member lists.

    Args:
        concepts: Dict of aggregated concepts.

    Returns:
        Dict: {ordered_collection_iri: [member_iris_in_order]}
        Members are sorted by their position values.
    """
    # Collect members with positions
    collection_members: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for concept_iri, concept in concepts.items():
        for coll_iri, position in concept.ordered_collection_positions.items():
            collection_members[coll_iri].append((position, concept_iri))

    # Sort by position and return just the IRIs
    result: dict[str, list[str]] = {}
    for coll_iri, members in collection_members.items():
        members.sort(key=lambda x: x[0])  # Sort by position
        result[coll_iri] = [iri for _, iri in members]

    return result


# --- Identifier Extraction ---


def extract_identifier(iri: str) -> str:
    """Extract dcterms:identifier value from IRI.

    For 'https://example.org/0000004' -> '0000004'
    For 'https://example.org/' -> 'example.org'

    Args:
        iri: Full IRI string.

    Returns:
        Identifier string suitable for dcterms:identifier.
    """
    if "#" in iri:
        return iri.split("#")[-1]

    # Remove trailing slash for processing
    cleaned = iri.rstrip("/")
    last_segment = cleaned.split("/")[-1]

    # If the last segment is empty (e.g., just "https://example.org/"),
    # use the domain
    if not last_segment:
        # Extract domain from URL
        parts = cleaned.split("//")
        if len(parts) > 1:
            return parts[1].split("/")[0]
        return cleaned

    return last_segment


# --- RDF Graph Building Functions ---


def build_organization_graph(org_iri: str) -> Graph:
    """Build RDF graph for an Organization.

    Args:
        org_iri: IRI of the organization (creator or publisher).

    Returns:
        Graph with Organization triples.
    """
    g = Graph()
    org = URIRef(org_iri)

    g.add((org, RDF.type, SDO.Organization))

    # Use the IRI itself as name (could be improved with lookup)
    g.add((org, SDO.name, Literal(org_iri, lang="en")))
    g.add((org, SDO.url, Literal(org_iri, datatype=XSD.anyURI)))

    return g


def build_concept_scheme_graph(
    cs: ConceptSchemeV1,
    concepts: dict[str, AggregatedConcept],
    collections: dict[str, AggregatedCollection],
) -> Graph:
    """Build RDF graph for ConceptScheme.

    Args:
        cs: ConceptSchemeV1 data.
        concepts: Aggregated concepts (to compute hasTopConcept).
        collections: Aggregated collections (to compute hasPart).

    Returns:
        Graph with ConceptScheme triples.
    """
    g = Graph()
    scheme_iri = URIRef(cs.vocabulary_iri)

    # Type
    g.add((scheme_iri, RDF.type, SKOS.ConceptScheme))

    # Identifier
    identifier = extract_identifier(cs.vocabulary_iri)
    g.add((scheme_iri, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

    # Basic metadata
    if cs.title:
        g.add((scheme_iri, SKOS.prefLabel, Literal(cs.title, lang="en")))
    if cs.description:
        g.add((scheme_iri, SKOS.definition, Literal(cs.description, lang="en")))

    # Dates
    if cs.created_date:
        g.add(
            (
                scheme_iri,
                DCTERMS.created,
                Literal(cs.created_date, datatype=XSD.date),
            )
        )
    if cs.modified_date:
        g.add(
            (
                scheme_iri,
                DCTERMS.modified,
                Literal(cs.modified_date, datatype=XSD.date),
            )
        )

    # Creator and Publisher (with Organization triples)
    if cs.creator:
        creator_ref = URIRef(cs.creator)
        g.add((scheme_iri, DCTERMS.creator, creator_ref))
        g += build_organization_graph(cs.creator)

    if cs.publisher:
        publisher_ref = URIRef(cs.publisher)
        g.add((scheme_iri, DCTERMS.publisher, publisher_ref))
        # Only add org graph if different from creator
        if cs.publisher != cs.creator:
            g += build_organization_graph(cs.publisher)

    # Version
    if cs.version:
        g.add((scheme_iri, OWL.versionInfo, Literal(cs.version)))

    # Change note / history note
    if cs.change_note:
        g.add((scheme_iri, SKOS.historyNote, Literal(cs.change_note, lang="en")))

    # Custodian
    if cs.custodian:
        g.add((scheme_iri, DCAT.contactPoint, Literal(cs.custodian)))

    # Catalogue PID
    if cs.catalogue_pid:
        if cs.catalogue_pid.startswith("http"):
            g.add((scheme_iri, RDFS.seeAlso, URIRef(cs.catalogue_pid)))
        else:
            g.add((scheme_iri, RDFS.seeAlso, Literal(cs.catalogue_pid)))

    # hasTopConcept - concepts with no broader
    for concept_iri, concept in concepts.items():
        if not concept.parent_iris:
            g.add((scheme_iri, SKOS.hasTopConcept, URIRef(concept_iri)))

    # hasPart - links to collections
    for collection_iri in collections:
        g.add((scheme_iri, DCTERMS.hasPart, URIRef(collection_iri)))

    return g


def build_concept_graph(
    concept: AggregatedConcept,
    scheme_iri: URIRef,
    narrower_map: dict[str, list[str]],
    vocab_name: str = "",
) -> Graph:
    """Build RDF graph for a single Concept.

    Args:
        concept: Aggregated concept data.
        scheme_iri: URIRef of the ConceptScheme.
        narrower_map: Map of parent -> children for narrower relationships.
        vocab_name: Vocabulary name for provenance URL generation.

    Returns:
        Graph with Concept triples.
    """
    g = Graph()
    c = URIRef(concept.iri)

    # Type
    g.add((c, RDF.type, SKOS.Concept))

    # Identifier
    identifier = extract_identifier(concept.iri)
    g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

    # Labels per language
    for lang, label in concept.pref_labels.items():
        g.add((c, SKOS.prefLabel, Literal(label, lang=lang)))

    for lang, definition in concept.definitions.items():
        g.add((c, SKOS.definition, Literal(definition, lang=lang)))

    for lang, labels in concept.alt_labels.items():
        for label in labels:
            g.add((c, SKOS.altLabel, Literal(label, lang=lang)))

    # Editorial notes per language
    for lang, note in concept.editorial_notes.items():
        g.add((c, SKOS.editorialNote, Literal(note, lang=lang)))

    # Broader (parent)
    for parent_iri in concept.parent_iris:
        g.add((c, SKOS.broader, URIRef(parent_iri)))

    # Narrower (computed inverse)
    for child_iri in narrower_map.get(concept.iri, []):
        g.add((c, SKOS.narrower, URIRef(child_iri)))

    # In scheme
    g.add((c, SKOS.inScheme, scheme_iri))

    # Source vocabulary attribution (verbatim copy)
    if concept.source_vocab_iri:
        g.add((c, PROV.hadPrimarySource, URIRef(concept.source_vocab_iri)))
    if concept.source_vocab_license:
        g.add((c, DCTERMS.license, URIRef(concept.source_vocab_license)))
    if concept.source_vocab_rights_holder:
        g.add((c, DCTERMS.rightsHolder, Literal(concept.source_vocab_rights_holder)))

    # Influenced by IRIs (prov:wasInfluencedBy)
    for influenced_iri in concept.influenced_by_iris:
        g.add((c, PROV.wasInfluencedBy, URIRef(influenced_iri)))

    # Top concept of (if no broader)
    if not concept.parent_iris:
        g.add((c, SKOS.topConceptOf, scheme_iri))

    # Change note
    if concept.change_note:
        g.add((c, SKOS.changeNote, Literal(concept.change_note, lang="en")))

    # Obsoletion (deprecated concept)
    if concept.obsolete_reason:
        g.add((c, OWL.deprecated, Literal(True)))
        g.add((c, SKOS.historyNote, Literal(concept.obsolete_reason, lang="en")))

    # Replaced by (dct:isReplacedBy)
    if concept.replaced_by_iri:
        g.add((c, DCTERMS.isReplacedBy, URIRef(concept.replaced_by_iri)))

    # Provenance (git blame URL)
    entity_id = extract_entity_id_from_iri(concept.iri)
    provenance_url = build_provenance_url(entity_id, vocab_name)
    if provenance_url:
        provenance_uri = URIRef(provenance_url)
        g.add((c, DCTERMS.provenance, provenance_uri))
        g.add((c, RDFS.seeAlso, provenance_uri))

    return g


def build_collection_graph(
    collection: AggregatedCollection,
    scheme_iri: URIRef,
    collection_members: dict[str, list[str]],
    ordered_collection_members: dict[str, list[str]] | None = None,
    vocab_name: str = "",
) -> Graph:
    """Build RDF graph for a single Collection.

    Args:
        collection: Aggregated collection data.
        scheme_iri: URIRef of the ConceptScheme.
        collection_members: Map of collection -> member IRIs (unordered).
        ordered_collection_members: Map of ordered collection -> member IRIs
            in order. Used for building skos:memberList.
        vocab_name: Vocabulary name for provenance URL generation.

    Returns:
        Graph with Collection triples.
    """
    from rdflib import BNode
    from rdflib.collection import Collection as RDFCollection

    ordered_collection_members = ordered_collection_members or {}
    g = Graph()
    c = URIRef(collection.iri)

    # Type - either OrderedCollection or Collection
    if collection.ordered:
        g.add((c, RDF.type, SKOS.OrderedCollection))
    else:
        g.add((c, RDF.type, SKOS.Collection))

    # Identifier
    identifier = extract_identifier(collection.iri)
    g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

    # Labels per language
    for lang, label in collection.pref_labels.items():
        g.add((c, SKOS.prefLabel, Literal(label, lang=lang)))

    for lang, definition in collection.definitions.items():
        g.add((c, SKOS.definition, Literal(definition, lang=lang)))

    # Editorial notes per language
    for lang, note in collection.editorial_notes.items():
        g.add((c, SKOS.editorialNote, Literal(note, lang=lang)))

    # Members - different handling for ordered vs unordered collections
    if collection.ordered:
        # OrderedCollection uses skos:memberList with RDF List
        ordered_members = ordered_collection_members.get(collection.iri, [])
        if ordered_members:
            list_node = BNode()
            member_refs = [URIRef(m) for m in ordered_members]
            RDFCollection(g, list_node, member_refs)
            g.add((c, SKOS.memberList, list_node))
    else:
        # Regular Collection uses skos:member
        for member_iri in collection_members.get(collection.iri, []):
            g.add((c, SKOS.member, URIRef(member_iri)))

    # In scheme
    g.add((c, SKOS.inScheme, scheme_iri))

    # rdfs:isDefinedBy - points to ConceptScheme (convention)
    g.add((c, RDFS.isDefinedBy, scheme_iri))

    # isPartOf
    g.add((c, DCTERMS.isPartOf, scheme_iri))

    # Change note
    if collection.change_note:
        g.add((c, SKOS.changeNote, Literal(collection.change_note, lang="en")))

    # Obsoletion (deprecated collection)
    if collection.obsolete_reason:
        g.add((c, OWL.deprecated, Literal(True)))
        g.add((c, SKOS.historyNote, Literal(collection.obsolete_reason, lang="en")))

    # Replaced by (dct:isReplacedBy)
    if collection.replaced_by_iri:
        g.add((c, DCTERMS.isReplacedBy, URIRef(collection.replaced_by_iri)))

    # Provenance (git blame URL)
    entity_id = extract_entity_id_from_iri(collection.iri)
    provenance_url = build_provenance_url(entity_id, vocab_name)
    if provenance_url:
        provenance_uri = URIRef(provenance_url)
        g.add((c, DCTERMS.provenance, provenance_uri))
        g.add((c, RDFS.seeAlso, provenance_uri))

    return g


def build_mappings_graph(
    mappings: list[MappingV1], converter: curies.Converter
) -> Graph:
    """Build RDF graph for all mappings.

    Args:
        mappings: List of MappingV1 from XLSX.
        converter: Curies converter for IRI expansion.

    Returns:
        Graph with mapping triples.
    """
    g = Graph()

    for mapping in mappings:
        if not mapping.concept_iri:
            continue

        concept_iri = URIRef(expand_curie(mapping.concept_iri, converter))

        # Related matches
        for match_iri in expand_iri_list(mapping.related_matches, converter):
            g.add((concept_iri, SKOS.relatedMatch, URIRef(match_iri)))

        # Close matches
        for match_iri in expand_iri_list(mapping.close_matches, converter):
            g.add((concept_iri, SKOS.closeMatch, URIRef(match_iri)))

        # Exact matches
        for match_iri in expand_iri_list(mapping.exact_matches, converter):
            g.add((concept_iri, SKOS.exactMatch, URIRef(match_iri)))

        # Narrower matches
        for match_iri in expand_iri_list(mapping.narrower_matches, converter):
            g.add((concept_iri, SKOS.narrowMatch, URIRef(match_iri)))

        # Broader matches
        for match_iri in expand_iri_list(mapping.broader_matches, converter):
            g.add((concept_iri, SKOS.broadMatch, URIRef(match_iri)))

    return g


# --- Main XLSX -> RDF Converter ---


def excel_to_rdf_v1(
    file_to_convert_path: Path,
    output_file_path: Path | None = None,
    output_format: TypingLiteral["turtle", "xml", "json-ld"] = "turtle",
    output_type: TypingLiteral["file", "graph"] = "file",
    *,
    vocab_config: "config.Vocab",
) -> Path | Graph:
    """Convert a v1.0 Excel template to RDF vocabulary.

    ConceptScheme metadata is read from vocab_config (idranges.toml).
    The "Concept Scheme" sheet in Excel is read-only and never read.

    Args:
        file_to_convert_path: Path to the XLSX file.
        output_file_path: Optional path for output RDF file.
                         Defaults to same name with .ttl extension.
        output_format: RDF serialization format ("turtle", "xml", "json-ld").
        output_type: "file" to serialize to file, "graph" to return Graph object.
        vocab_config: Vocab config from idranges.toml with scheme metadata.

    Returns:
        Path to the generated RDF file, or Graph object if output_type="graph".

    Raises:
        ValueError: If the input file is not a supported Excel format.
    """
    if file_to_convert_path.suffix.lower() not in EXCEL_FILE_ENDINGS:
        msg = (
            "Files for conversion must end with one of the Excel file formats: "
            f"'{', '.join(EXCEL_FILE_ENDINGS)}'"
        )
        raise ValueError(msg)

    logger.info("Reading XLSX file: %s", file_to_convert_path)

    # Get vocabulary name from filename (used for provenance URLs)
    vocab_name = file_to_convert_path.stem.lower()

    # Build ConceptScheme from config (Excel sheet is read-only, never read)
    concept_scheme = config_to_concept_scheme_v1(vocab_config)

    logger.debug("Reading Prefixes...")
    prefixes = read_prefixes_v1(file_to_convert_path)

    logger.debug("Reading Concepts...")
    concept_rows = read_concepts_v1(file_to_convert_path)

    logger.debug("Reading Collections...")
    collection_rows = read_collections_v1(file_to_convert_path)

    logger.debug("Reading Mappings...")
    mapping_rows = read_mappings_v1(file_to_convert_path)

    # Build curies converter from prefixes
    converter = build_curies_converter_from_prefixes(prefixes)

    # Aggregate multi-row data
    logger.debug("Aggregating concepts...")
    concepts = aggregate_concepts(concept_rows, converter)

    logger.debug("Aggregating collections...")
    collections = aggregate_collections(collection_rows, converter)

    # Build inverse relationships
    logger.debug("Building inverse relationships...")
    collection_members = build_collection_members_from_concepts(concepts)
    ordered_collection_members = build_ordered_collection_members(concepts)
    narrower_map = build_narrower_map(concepts)

    # Build the complete graph
    logger.debug("Building RDF graph...")
    scheme_iri = URIRef(concept_scheme.vocabulary_iri)

    graph = build_concept_scheme_graph(concept_scheme, concepts, collections)

    for concept in concepts.values():
        graph += build_concept_graph(concept, scheme_iri, narrower_map, vocab_name)

    for collection in collections.values():
        graph += build_collection_graph(
            collection,
            scheme_iri,
            collection_members,
            ordered_collection_members,
            vocab_name,
        )

    graph += build_mappings_graph(mapping_rows, converter)

    # Bind prefixes for nice serialization
    for prefix_model in prefixes:
        if prefix_model.prefix and prefix_model.namespace:
            graph.bind(prefix_model.prefix, Namespace(prefix_model.namespace))

    logger.info("Built graph with %d triples", len(graph))

    if output_type == "graph":
        return graph

    # Serialize to file
    if output_file_path is None:
        if output_format == "xml":
            suffix = ".rdf"
        elif output_format == "json-ld":
            suffix = ".json-ld"
        else:
            suffix = ".ttl"
        output_file_path = file_to_convert_path.with_suffix(suffix)

    logger.info("Serializing to: %s", output_file_path)
    graph.serialize(destination=str(output_file_path), format=output_format)

    logger.info("Conversion complete: %s", output_file_path)
    return output_file_path


# --- Debugging Utilities ---


def compare_graphs(g1: Graph, g2: Graph) -> dict:
    """Compare two graphs and return differences.

    Useful for debugging round-trip conversion issues.

    Args:
        g1: First graph (e.g., original).
        g2: Second graph (e.g., round-tripped).

    Returns:
        Dict with "only_in_g1" and "only_in_g2" triple lists.
    """
    only_in_g1 = list(g1 - g2)
    only_in_g2 = list(g2 - g1)

    return {
        "only_in_g1": only_in_g1,
        "only_in_g2": only_in_g2,
        "g1_count": len(g1),
        "g2_count": len(g2),
        "common_count": len(g1) - len(only_in_g1),
    }


# =============================================================================
# 043 to v1.0 RDF Conversion
# =============================================================================

# Predicates that are transformed from 043 to v1.0
PREDICATES_043_TO_V1 = {
    # On concepts: rdfs:isDefinedBy -> prov:hadPrimarySource
    # (handled specially - only for concepts)
    # Change notes: various 043 predicates -> skos:changeNote
    SKOS.historyNote: SKOS.changeNote,
    DCTERMS.provenance: SKOS.changeNote,
    PROV.wasDerivedFrom: SKOS.changeNote,
}

# Predicates that are preserved as-is (known/expected in v1.0)
PREDICATES_PRESERVED = {
    # RDF basics
    RDF.type,
    # SKOS core
    SKOS.ConceptScheme,
    SKOS.Concept,
    SKOS.Collection,
    SKOS.prefLabel,
    SKOS.altLabel,
    SKOS.definition,
    SKOS.broader,
    SKOS.narrower,
    SKOS.related,
    SKOS.inScheme,
    SKOS.topConceptOf,
    SKOS.hasTopConcept,
    SKOS.member,
    SKOS.note,
    SKOS.scopeNote,
    SKOS.example,
    SKOS.changeNote,
    SKOS.editorialNote,
    SKOS.historyNote,  # Will be transformed, but listed for completeness
    SKOS.notation,
    # SKOS mappings
    SKOS.exactMatch,
    SKOS.closeMatch,
    SKOS.broadMatch,
    SKOS.narrowMatch,
    SKOS.relatedMatch,
    # Dublin Core
    DCTERMS.identifier,
    DCTERMS.created,
    DCTERMS.modified,
    DCTERMS.creator,
    DCTERMS.publisher,
    DCTERMS.contributor,
    DCTERMS.license,
    DCTERMS.rightsHolder,
    DCTERMS.source,
    DCTERMS.hasPart,
    DCTERMS.isPartOf,
    DCTERMS.provenance,  # Will be transformed
    # OWL
    OWL.versionInfo,
    OWL.deprecated,
    # PROV
    PROV.hadPrimarySource,
    PROV.wasInfluencedBy,
    PROV.wasDerivedFrom,  # Will be transformed
    # RDFS
    RDFS.isDefinedBy,  # Will be transformed for concepts
    RDFS.label,
    RDFS.comment,
    RDFS.seeAlso,
    # DCAT
    DCAT.contactPoint,
}


def convert_rdf_043_to_v1(
    input_path: Path,
    output_path: Path | None = None,
    output_format: TypingLiteral["turtle", "xml", "json-ld"] = "turtle",
) -> Path:
    """Convert a 0.4.3 format RDF vocabulary to v1.0 RDF format.

    This performs predicate transformations:
    - rdfs:isDefinedBy (on concepts) -> prov:hadPrimarySource
    - skos:historyNote (non-obsolete) -> skos:changeNote
    - dcterms:provenance -> skos:changeNote
    - prov:wasDerivedFrom -> skos:changeNote

    Unknown predicates are dropped with a warning.

    Args:
        input_path: Path to the 043 RDF file.
        output_path: Optional path for output. Defaults to input with _v1 suffix.
        output_format: RDF serialization format.

    Returns:
        Path to the generated v1.0 RDF file.
    """
    if input_path.suffix.lower() not in RDF_FILE_ENDINGS:
        msg = (
            "Files for conversion must end with one of the RDF file formats: "
            f"'{', '.join(RDF_FILE_ENDINGS.keys())}'"
        )
        raise ValueError(msg)

    logger.info("Converting 043 RDF to v1.0: %s", input_path)

    # Parse input
    input_graph = Graph().parse(
        str(input_path),
        format=RDF_FILE_ENDINGS[input_path.suffix.lower()],
    )

    # Create output graph
    output_graph = Graph()

    # Copy namespace bindings
    for prefix, namespace in input_graph.namespaces():
        output_graph.bind(prefix, namespace)

    # Ensure prov namespace is bound (needed for new predicates)
    output_graph.bind("prov", PROV)

    # Get all concepts for special handling of rdfs:isDefinedBy
    concepts = set(input_graph.subjects(RDF.type, SKOS.Concept))

    # Track unknown predicates for warning
    unknown_predicates: set[URIRef] = set()

    # Process each triple
    for s, p, o in input_graph:
        new_triple = _transform_triple_043_to_v1(s, p, o, concepts, unknown_predicates)
        if new_triple:
            output_graph.add(new_triple)

    # Log warnings for unknown predicates
    if unknown_predicates:
        logger.warning(
            "Dropped %d unknown predicate type(s) during 043->v1.0 conversion:",
            len(unknown_predicates),
        )
        for pred in sorted(unknown_predicates, key=str):
            count = len(list(input_graph.triples((None, pred, None))))
            logger.warning("  - %s (%d triples)", pred, count)

    # Determine output path
    if output_path is None:
        if output_format == "xml":
            suffix = ".rdf"
        elif output_format == "json-ld":
            suffix = ".jsonld"
        else:
            suffix = ".ttl"
        # Add _v1 suffix before extension
        output_path = input_path.with_stem(f"{input_path.stem}_v1").with_suffix(suffix)

    # Serialize
    logger.info("Writing v1.0 RDF to: %s", output_path)
    output_graph.serialize(destination=str(output_path), format=output_format)

    logger.info(
        "Conversion complete: %d triples in, %d triples out",
        len(input_graph),
        len(output_graph),
    )

    return output_path


def _transform_triple_043_to_v1(
    s: URIRef,
    p: URIRef,
    o,
    concepts: set[URIRef],
    unknown_predicates: set[URIRef],
) -> tuple | None:
    """Transform a single triple from 043 to v1.0 format.

    Args:
        s: Subject
        p: Predicate
        o: Object
        concepts: Set of concept IRIs (for rdfs:isDefinedBy handling)
        unknown_predicates: Set to collect unknown predicates

    Returns:
        Transformed triple (s, p, o) or None if dropped.
    """
    # Special case: rdfs:isDefinedBy on concepts -> prov:hadPrimarySource
    # For non-concepts (collections, scheme), preserve rdfs:isDefinedBy as-is
    if p == RDFS.isDefinedBy:
        if s in concepts:
            return (s, PROV.hadPrimarySource, o)
        return (s, p, o)  # Preserve for collections/scheme

    # Check for predicates that need transformation
    if p in PREDICATES_043_TO_V1:
        new_predicate = PREDICATES_043_TO_V1[p]
        return (s, new_predicate, o)

    # Check if predicate is known/preserved
    if p in PREDICATES_PRESERVED:
        return (s, p, o)

    # Check for schema.org predicates (used for organizations)
    if str(p).startswith("https://schema.org/"):
        return (s, p, o)

    # Unknown predicate - collect for warning and drop
    unknown_predicates.add(p)
    return None
