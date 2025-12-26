"""Helper functions for v1.0 vocabulary conversion.

This module provides utility functions used by convert_v1.py:
- Provenance URL generation (GitHub blame URLs)
- ID range management and usage tracking
- Contributor derivation from ID ranges
- Deprecation validation and formatting
- CURIE expansion utilities
"""

from __future__ import annotations

import logging
import os
import re
from enum import Enum
from typing import TYPE_CHECKING

import curies
from jinja2 import Template

from voc4cat import config
from voc4cat.models_v1 import (
    CollectionV1,
    ConceptV1,
    IDRangeInfoV1,
)

if TYPE_CHECKING:
    from voc4cat.config import IdrangeItem, Vocab

logger = logging.getLogger(__name__)


# =============================================================================
# CURIE Utilities
# =============================================================================


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


# =============================================================================
# Creator Field Utilities
# =============================================================================


def extract_creator_names(creator_field: str) -> list[str]:
    """Extract names from creator field.

    The creator field format is '<URL> <name>' per line, where URL is an
    ORCID or ROR identifier.

    Examples:
        'https://orcid.org/0000-0001-2345-6789 John Doe\\n...' -> ['John Doe', ...]

    Args:
        creator_field: Multi-line string with creator entries.

    Returns:
        List of extracted names (empty list if no names found).
    """
    if not creator_field:
        return []

    names = []
    for iline in creator_field.strip().split("\n"):
        line = iline.strip()
        if not line:
            continue
        # Split by whitespace - name is everything after the URL
        parts = line.split()
        # Find the URL (starts with http) and take everything after it
        for i, part in enumerate(parts):
            if part.startswith("http"):
                name = " ".join(parts[i + 1 :])
                if name:
                    names.append(name)
                break
    return names


def generate_history_note(created_date: str, creator_names: list[str]) -> str:
    """Generate a history note from creation date and creator names.

    Format: "Created {date}." or "Created {date} by {name1}, {name2}."

    Args:
        created_date: Creation date string (e.g., "2025" or "2025-01-15").
        creator_names: List of creator names.

    Returns:
        Generated history note, or empty string if no created_date.
    """
    if not created_date:
        return ""

    note = f"Created {created_date}"
    if creator_names:
        names_str = ", ".join(creator_names)
        note += f" by {names_str}"
    note += "."
    return note


# =============================================================================
# Provenance URL Helpers
# =============================================================================


def extract_github_repo_from_url(repository_url: str) -> str:
    """Extract owner/repo from a GitHub repository URL.

    Args:
        repository_url: GitHub URL like "https://github.com/owner/repo"
            or "https://github.com/owner/repo.git".

    Returns:
        The owner/repo string (e.g., "owner/repo"), or empty string if not
        a valid GitHub URL.
    """
    if not repository_url:
        return ""

    # Match GitHub URLs: https://github.com/owner/repo or https://github.com/owner/repo.git
    pattern = r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$"
    match = re.match(pattern, repository_url.strip())
    if match:
        return match.group(1)
    return ""


# Default Jinja template for GitHub blame URLs
DEFAULT_PROVENANCE_TEMPLATE = (
    "https://github.com/{{ github_repo }}/blame/{{ version }}"
    "/vocabularies/{{ vocab_name }}/{{ entity_id }}.ttl"
)


def build_provenance_url(
    entity_id: str,
    vocab_name: str,
    provenance_template: str = "",
    repository_url: str = "",
) -> str:
    """Build a provenance URL using Jinja template.

    Uses the provided template or falls back to the default GitHub blame URL
    format when a GitHub repository can be detected.

    Args:
        entity_id: The concept or collection ID (e.g., "0000004").
        vocab_name: The vocabulary name from idranges.toml (e.g., "voc4cat").
        provenance_template: Optional Jinja template for the URL. If provided,
            this template is used instead of the default GitHub format.
        repository_url: Optional repository URL from idranges.toml. Used for
            GitHub auto-detection when GITHUB_REPOSITORY env var is not set.

    Template variables available:
        entity_id: The concept/collection ID
        vocab_name: The vocabulary name
        version: Git version/tag (from VOC4CAT_VERSION env var, or "main")
        github_repo: The GitHub owner/repo (if detected from env var or URL)

    Returns:
        The provenance URL, or empty string if no template is provided and
        no GitHub repository can be detected.
    """
    version = os.getenv("VOC4CAT_VERSION", "") or "main"
    if version.lower().startswith("v_"):  # hash version identifier
        version = "main"

    # Determine github_repo (for default template and as template variable)
    github_repo = os.getenv("GITHUB_REPOSITORY", "")
    if not github_repo and repository_url:
        github_repo = extract_github_repo_from_url(repository_url)

    # Select template
    if provenance_template:
        template_str = provenance_template
    elif github_repo:
        template_str = DEFAULT_PROVENANCE_TEMPLATE
    else:
        return ""  # No template and no GitHub repo detected

    # Render template
    template = Template(template_str)
    return template.render(
        entity_id=entity_id,
        vocab_name=vocab_name,
        version=version,
        github_repo=github_repo,
    )


def extract_entity_id_from_iri(iri: str, vocab_name: str) -> str:
    """Extract the entity ID from a full IRI.

    Handles both slash-based and hash-based IRIs. Strips the vocabulary
    prefix (e.g., 'voc4cat_') from the extracted ID when present.

    Examples:
        'https://w3id.org/nfdi4cat/voc4cat/0000004', 'voc4cat' -> '0000004'
        'https://w3id.org/nfdi4cat/voc4cat_0000004', 'voc4cat' -> '0000004'
        'https://example.org/vocab#concept123', 'vocab' -> 'concept123'

    Args:
        iri: Full IRI string.
        vocab_name: Vocabulary name used to strip prefix from the ID.

    Returns:
        The entity ID portion (with vocab prefix stripped if applicable).
    """
    if "#" in iri:  # noqa: SIM108
        entity_id = iri.split("#")[-1]
    else:
        entity_id = iri.rstrip("/").split("/")[-1]

    # Strip vocabulary prefix if present (e.g., 'voc4cat_0000004' -> '0000004')
    prefix = f"{vocab_name}_"
    if entity_id.startswith(prefix):
        entity_id = entity_id[len(prefix) :]

    return entity_id


def add_provenance_triples_to_graph(
    graph,  # rdflib.Graph - not typed to avoid circular import
    entity_iri,  # URIRef
    vocab_name: str,
    provenance_template: str = "",
    repository_url: str = "",
) -> bool:
    """Add provenance triples (dcterms:provenance, rdfs:seeAlso) for an entity.

    Generates a provenance URL (git blame link) and adds both dcterms:provenance
    and rdfs:seeAlso triples pointing to it.

    Args:
        graph: The RDF graph to modify (mutated in place).
        entity_iri: The IRI of the entity (concept or collection) as URIRef.
        vocab_name: The vocabulary name from idranges.toml.
        provenance_template: Optional Jinja template for the provenance URL.
        repository_url: Optional repository URL for GitHub auto-detection.

    Returns:
        True if provenance triples were added, False if no URL could be generated.
    """
    # Import here to avoid circular dependency
    from rdflib import DCTERMS, RDFS, URIRef  # noqa: PLC0415

    entity_id = extract_entity_id_from_iri(str(entity_iri), vocab_name)
    provenance_url = build_provenance_url(
        entity_id, vocab_name, provenance_template, repository_url
    )
    if provenance_url:
        provenance_uri = URIRef(provenance_url)
        graph.add((entity_iri, DCTERMS.provenance, provenance_uri))
        graph.add((entity_iri, RDFS.seeAlso, provenance_uri))
        return True
    return False


def format_iri_with_label(
    iri: str,
    concepts_data: dict[str, dict[str, dict]],
    collections_data: dict[str, dict[str, dict]] | None = None,
) -> str:
    """Format IRI as 'curie (english_label)' if label is available.

    Looks up the English preferred label for the given IRI in concepts_data
    and optionally collections_data. If found, returns the format
    "curie (label)", otherwise returns just the compressed curie.

    Args:
        iri: Full IRI string to format.
        concepts_data: Nested dict from extract_concepts_from_rdf,
            mapping concept_iri -> lang -> data dict.
        collections_data: Optional nested dict from extract_collections_from_rdf,
            mapping collection_iri -> lang -> data dict.

    Returns:
        Formatted string like "voc4cat:0000016 (catalyst form)" or just
        "voc4cat:0000016" if no English label is available.
    """
    converter = config.curies_converter
    curie = converter.compress(iri, passthrough=True)

    # Try to find English label in concepts
    if iri in concepts_data:
        en_data = concepts_data[iri].get("en", {})
        label = en_data.get("preferred_label", "")
        if label:
            return f"{curie} ({label})"

    # Try to find English label in collections
    if collections_data and iri in collections_data:
        en_data = collections_data[iri].get("en", {})
        label = en_data.get("preferred_label", "")
        if label:
            return f"{curie} ({label})"

    return curie


# =============================================================================
# ID Range Info Functions
# =============================================================================


def extract_used_ids(
    concepts: list[ConceptV1],
    collections: list[CollectionV1],
    vocab_config: Vocab,
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
    vocab_config: Vocab,
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
            unused_str = "all IDs used. Request a new range!"
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


def format_contributor_string(idr: IdrangeItem) -> str:
    """Format a single IdrangeItem as a contributor string.

    Format priority:
    - If ORCID: "<name> <orcid-URL>" or just "<orcid-URL>" if no name
    - If only gh_name: "<name> https://github.com/<gh_name>" or
      "<gh_name> https://github.com/<gh_name>" if no name

    Args:
        idr: IdrangeItem from config.

    Returns:
        Formatted contributor string.
    """
    name_part = idr.name.strip() if idr.name else ""

    if idr.orcid:
        # ORCID takes priority as the URL
        orcid_url = str(idr.orcid)
        if not orcid_url.startswith("http"):
            orcid_url = f"https://orcid.org/{orcid_url}"
        if name_part:
            return f"{name_part} {orcid_url}"
        return orcid_url
    if idr.gh_name:
        # Use GitHub profile URL
        gh_url = f"https://github.com/{idr.gh_name}"
        if name_part:
            return f"{name_part} {gh_url}"
        return f"{idr.gh_name} {gh_url}"

    return ""  # Should not happen due to validation


def derive_contributors(
    vocab_config: Vocab,
    used_ids: set[int],
) -> str:
    """Derive contributors from ID range usage.

    Creates contributor strings for each person who has used IDs from their
    reserved range. Excludes creators (from vocab_config.creator).

    Args:
        vocab_config: Vocab configuration from idranges.toml.
        used_ids: Set of integer IDs that are in use.

    Returns:
        Multi-line string of contributors, one per line, format:
        "<name> <orcid-URL or github-URL>"
    """
    contributors: list[str] = []

    # Parse creator field to extract identifiers for exclusion
    creator_identifiers: set[str] = set()
    if vocab_config.creator:
        for iline in vocab_config.creator.strip().split("\n"):
            line = iline.strip()
            if not line:
                continue
            # Extract ORCID from creator line
            if "orcid.org/" in line:
                parts = line.split()
                for part in parts:
                    if "orcid.org/" in part:
                        orcid_id = part.split("orcid.org/")[-1].rstrip("/")
                        creator_identifiers.add(orcid_id.lower())
                        creator_identifiers.add(f"https://orcid.org/{orcid_id}".lower())
            # Extract GitHub username if present (via github.com URL)
            if "github.com/" in line:
                parts = line.split()
                for part in parts:
                    if "github.com/" in part:
                        gh = part.split("github.com/")[-1].rstrip("/")
                        creator_identifiers.add(gh.lower())

    for idr in vocab_config.id_range:
        # Check if any IDs from this range are used
        range_ids = set(range(idr.first_id, idr.last_id + 1))
        if not (range_ids & used_ids):
            continue  # No IDs used from this range

        # Skip if this contributor is in the creator list
        skip = False
        if idr.orcid:
            orcid_str = str(idr.orcid).lower()
            if orcid_str in creator_identifiers:
                skip = True
            # Also check ORCID ID without URL prefix
            orcid_id = orcid_str.split("orcid.org/")[-1]
            if orcid_id in creator_identifiers:
                skip = True
        if idr.gh_name and idr.gh_name.lower() in creator_identifiers:
            skip = True
        if skip:
            continue

        # Build contributor string
        contributor_str = format_contributor_string(idr)
        if contributor_str and contributor_str not in contributors:
            contributors.append(contributor_str)

    return "\n".join(contributors)


# =============================================================================
# Deprecation Handling Functions
# =============================================================================

OBSOLETE_PREFIX = "OBSOLETE "


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


def validate_entity_deprecation(
    entity_iri: str,
    lang_data: dict[str, dict],
    vocab_name: str,
    provenance_template: str,
    repository_url: str,
    obsoletion_reason_enum: type[Enum],
    entity_type: str,
) -> str:
    """Validate and fix deprecation info for concept or collection.

    This function handles:
    - Extracting provenance URL from entity IRI
    - Extracting deprecation info from language data
    - Validating English prefLabel against deprecation rules
    - Correcting prefLabel if needed (adding OBSOLETE prefix)
    - Logging validation errors

    Args:
        entity_iri: IRI of the entity (concept or collection).
        lang_data: Dictionary of language code -> field data.
        vocab_name: Name of the vocabulary.
        provenance_template: Template for provenance URL.
        repository_url: Repository URL for provenance.
        obsoletion_reason_enum: Enum class for valid obsoletion reasons
            (ConceptObsoletionReason or CollectionObsoletionReason).
        entity_type: "concept" or "collection".

    Returns:
        Provenance URL for the entity.

    Side effects:
        Modifies lang_data["en"]["preferred_label"] if validation corrects it.
        Logs errors for deprecation validation failures.
    """
    # Generate provenance URL
    entity_id = extract_entity_id_from_iri(entity_iri, vocab_name)
    provenance_url = build_provenance_url(
        entity_id, vocab_name, provenance_template, repository_url
    )

    # Get deprecation info from any language (it's the same for all)
    first_lang_data = next(iter(lang_data.values()), {})
    is_deprecated = first_lang_data.get("is_deprecated", False)
    obsolete_reason_raw = first_lang_data.get("obsolete_reason", "")

    # Validate and fix English prefLabel if needed
    en_pref_label = lang_data.get("en", {}).get("preferred_label", "")
    if en_pref_label:
        corrected_label, errors = validate_deprecation(
            pref_label=en_pref_label,
            is_deprecated=is_deprecated,
            history_note=obsolete_reason_raw,
            valid_reasons=[e.value for e in obsoletion_reason_enum],
            entity_iri=entity_iri,
            entity_type=entity_type,
        )
        for error in errors:
            logger.error(error)
        # Update the English prefLabel in the data
        if "en" in lang_data:
            lang_data["en"]["preferred_label"] = corrected_label

    return provenance_url
