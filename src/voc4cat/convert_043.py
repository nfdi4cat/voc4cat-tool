"""Converter for 0.4.3 format RDF vocabularies to v1.0 RDF format.

This module handles migration of legacy vocabulary files:
- Predicate transformations (e.g., rdfs:isDefinedBy -> prov:hadPrimarySource)
- ConceptScheme metadata enrichment from config
- Unknown predicate handling with warnings

The 043 format was used in earlier versions of voc4cat-tool and differs
from v1.0 in several predicate choices and structural conventions.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal as TypingLiteral

from rdflib import (
    DCAT,
    DCTERMS,
    FOAF,
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
from voc4cat.convert_v1 import (
    build_entity_graph,
    config_to_concept_scheme_v1,
    extract_concept_scheme_from_rdf,
    parse_name_url,
    rdf_concept_scheme_to_v1,
)
from voc4cat.convert_v1_helpers import add_provenance_triples_to_graph
from voc4cat.utils import RDF_FILE_ENDINGS

if TYPE_CHECKING:
    from voc4cat.config import Vocab

logger = logging.getLogger(__name__)

# schema.org namespace (not in rdflib by default)
SDO = Namespace("https://schema.org/")


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
    # FOAF
    FOAF.homepage,
}


def _enrich_concept_scheme_from_config(
    graph: Graph,
    vocab_config: Vocab,
) -> None:
    """Enrich ConceptScheme metadata in graph using config values.

    Updates ConceptScheme triples in-place. Config values override existing
    RDF values where provided.

    Args:
        graph: The RDF graph to modify (mutated in place).
        vocab_config: Vocab configuration from idranges.toml.
    """
    # Find the ConceptScheme subject
    scheme_iri = None
    for s in graph.subjects(RDF.type, SKOS.ConceptScheme):
        scheme_iri = s
        break

    if scheme_iri is None:
        logger.warning("No ConceptScheme found in graph, skipping metadata enrichment")
        return

    # Extract existing RDF data and merge with config
    rdf_data = extract_concept_scheme_from_rdf(graph)
    rdf_scheme = rdf_concept_scheme_to_v1(rdf_data)
    enriched = config_to_concept_scheme_v1(vocab_config, rdf_scheme)

    # Override version from environment variable if present (takes precedence)
    env_version = os.getenv("VOC4CAT_VERSION", "")
    if env_version:
        enriched = enriched.model_copy(update={"version": env_version})

    # Define predicate-to-field mappings for update
    # Each tuple: (predicate, field_name, is_literal, lang_or_datatype)
    metadata_mappings = [
        (SKOS.prefLabel, "title", True, "en"),
        (SKOS.definition, "description", True, "en"),
        (DCTERMS.created, "created_date", True, XSD.date),
        (DCTERMS.modified, "modified_date", True, XSD.date),
        (OWL.versionInfo, "version", True, None),
        (SKOS.historyNote, "history_note", True, "en"),
    ]

    # Update metadata triples
    for predicate, field_name, is_literal, type_or_lang in metadata_mappings:
        value = getattr(enriched, field_name, "")
        if not value:
            continue

        # Remove existing triple(s) for this predicate
        graph.remove((scheme_iri, predicate, None))

        # Add new triple
        if is_literal:
            if type_or_lang == "en":
                obj = Literal(value, lang="en")
            elif type_or_lang is not None:
                obj = Literal(value, datatype=type_or_lang)
            else:
                obj = Literal(value)
            graph.add((scheme_iri, predicate, obj))

    # Handle URI-valued predicates separately (creator, publisher, custodian)
    # These fields may contain multi-line text with format "<name> <URL>" per line
    for predicate, field_name in [
        (DCTERMS.creator, "creator"),
        (DCTERMS.publisher, "publisher"),
        (DCAT.contactPoint, "custodian"),
    ]:
        value = getattr(enriched, field_name, "")
        if not value:
            continue

        # Remove existing triples for this predicate
        graph.remove((scheme_iri, predicate, None))

        # Parse each line and add triples for all entries
        for iline in value.strip().split("\n"):
            name, url = parse_name_url(iline)
            if url:
                # Add the predicate triple (dcterms:creator, dcterms:publisher, or dcat:contactPoint)
                graph.add((scheme_iri, predicate, URIRef(url)))
                # Remove existing schema:name for this entity (may have wrong value from 043)
                entity_ref = URIRef(url)
                graph.remove((entity_ref, SDO.name, None))
                # Add entity graph (schema:Person or schema:Organization with name)
                graph += build_entity_graph(url, name, field_name)
            elif iline.strip() and predicate == DCAT.contactPoint:
                # Fallback to literal for custodian if no URL (matches convert_v1 behavior)
                graph.add((scheme_iri, predicate, Literal(iline.strip())))

    # Handle homepage -> foaf:homepage
    if enriched.homepage:
        graph.remove((scheme_iri, FOAF.homepage, None))
        if enriched.homepage.startswith("http"):
            graph.add((scheme_iri, FOAF.homepage, URIRef(enriched.homepage)))
        else:
            graph.add((scheme_iri, FOAF.homepage, Literal(enriched.homepage)))

    # Handle catalogue_pid -> dcterms:identifier and rdfs:seeAlso
    if enriched.catalogue_pid:
        # Replace existing identifier with catalogue_pid
        graph.remove((scheme_iri, DCTERMS.identifier, None))
        graph.add((scheme_iri, DCTERMS.identifier, Literal(enriched.catalogue_pid)))
        # Also add as rdfs:seeAlso
        graph.remove((scheme_iri, RDFS.seeAlso, None))
        if enriched.catalogue_pid.startswith("http"):
            graph.add((scheme_iri, RDFS.seeAlso, URIRef(enriched.catalogue_pid)))
        else:
            graph.add((scheme_iri, RDFS.seeAlso, Literal(enriched.catalogue_pid)))

    # Handle conforms_to -> dcterms:conformsTo (multi-line, one profile per line)
    if enriched.conforms_to:
        graph.remove((scheme_iri, DCTERMS.conformsTo, None))
        for iline in enriched.conforms_to.strip().split("\n"):
            line = iline.strip()
            if not line:
                continue
            if line.startswith("http"):
                graph.add((scheme_iri, DCTERMS.conformsTo, URIRef(line)))
            else:
                graph.add((scheme_iri, DCTERMS.conformsTo, Literal(line)))

    logger.debug("Enriched ConceptScheme metadata from config")


def _add_provenance_triples(
    graph: Graph,
    concepts: set[URIRef],
    collections: set[URIRef],
    vocab_name: str,
    vocab_config: Vocab,
) -> None:
    """Add provenance triples for concepts and collections.

    Uses the shared helper to generate git blame URLs and add
    dcterms:provenance and rdfs:seeAlso triples.

    Args:
        graph: The RDF graph to modify (mutated in place).
        concepts: Set of concept IRIs.
        collections: Set of collection IRIs.
        vocab_name: The vocabulary name (from input file stem).
        vocab_config: Vocab configuration from idranges.toml.
    """
    repository_url = vocab_config.repository or ""
    provenance_template = vocab_config.provenance_url_template or ""

    # Add provenance for concepts
    for concept_iri in concepts:
        add_provenance_triples_to_graph(
            graph, concept_iri, vocab_name, provenance_template, repository_url
        )

    # Add provenance for collections
    for collection_iri in collections:
        add_provenance_triples_to_graph(
            graph, collection_iri, vocab_name, provenance_template, repository_url
        )

    logger.debug(
        "Added provenance triples for %d concepts and %d collections",
        len(concepts),
        len(collections),
    )


def convert_rdf_043_to_v1(
    input_path: Path,
    output_path: Path | None = None,
    output_format: TypingLiteral["turtle", "xml", "json-ld"] = "turtle",
    vocab_config: Vocab | None = None,
) -> Path:
    """Convert a 0.4.3 format RDF vocabulary to v1.0 RDF format.

    This performs predicate transformations:
    - rdfs:isDefinedBy (on concepts) -> prov:hadPrimarySource
    - skos:historyNote (non-obsolete) -> skos:changeNote
    - dcterms:provenance -> skos:changeNote
    - prov:wasDerivedFrom -> skos:changeNote
    - dcterms:hasPart (on ConceptScheme) -> dropped (not used in v1.0)

    If vocab_config is provided, ConceptScheme metadata is enriched from
    the config (config values override RDF values).

    Unknown predicates are dropped with a warning.

    Args:
        input_path: Path to the 043 RDF file.
        output_path: Optional path for output. Defaults to input with _v1 suffix.
        output_format: RDF serialization format.
        vocab_config: Optional Vocab config for metadata enrichment.

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

    # Bind vocabulary prefixes from config if provided
    if vocab_config is not None and vocab_config.prefix_map:
        for prefix, namespace_uri in vocab_config.prefix_map.items():
            output_graph.bind(prefix, Namespace(str(namespace_uri)))

    # Get all concepts for special handling of rdfs:isDefinedBy
    concepts = set(input_graph.subjects(RDF.type, SKOS.Concept))

    # Get all collections for special handling of dcterms:isPartOf
    collections = set(input_graph.subjects(RDF.type, SKOS.Collection))

    # Get ConceptScheme(s) for special handling of dcterms:hasPart
    concept_schemes = set(input_graph.subjects(RDF.type, SKOS.ConceptScheme))

    # Track unknown predicates for warning
    unknown_predicates: set[URIRef] = set()

    # Get ID pattern for identifier transformation
    vocab_name = input_path.stem.lower()
    id_pattern = config.ID_PATTERNS.get(vocab_name)
    if not id_pattern and vocab_config:
        # Fall back to compiling pattern from vocab_config.id_length
        id_pattern = re.compile(rf"(?P<identifier>[0-9]{{{vocab_config.id_length}}})$")

    # Process each triple
    for s, p, o in input_graph:
        new_triple = _transform_triple_043_to_v1(
            s,
            p,
            o,
            concepts,
            collections,
            concept_schemes,
            unknown_predicates,
            id_pattern,
        )
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

    # Enrich ConceptScheme metadata from config if provided
    if vocab_config is not None:
        _enrich_concept_scheme_from_config(output_graph, vocab_config)

        # Add provenance triples for concepts and collections
        vocab_name = input_path.stem.lower()
        _add_provenance_triples(
            output_graph, concepts, collections, vocab_name, vocab_config
        )

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


def _transform_triple_043_to_v1(  # noqa: PLR0911
    s: URIRef,
    p: URIRef,
    o,
    concepts: set[URIRef],
    collections: set[URIRef],
    concept_schemes: set[URIRef],
    unknown_predicates: set[URIRef],
    id_pattern: re.Pattern[str] | None = None,
) -> tuple | None:
    """Transform a single triple from 043 to v1.0 format.

    Args:
        s: Subject
        p: Predicate
        o: Object
        concepts: Set of concept IRIs (for rdfs:isDefinedBy handling)
        collections: Set of collection IRIs (for dcterms:isPartOf handling)
        concept_schemes: Set of ConceptScheme IRIs (for dcterms:hasPart handling)
        unknown_predicates: Set to collect unknown predicates
        id_pattern: Compiled regex pattern for extracting IDs from identifiers.

    Returns:
        Transformed triple (s, p, o) or None if dropped.
    """
    # Drop dcterms:hasPart on ConceptScheme (links to collections not used in v1.0)
    if p == DCTERMS.hasPart and s in concept_schemes:
        return None

    # Drop dcterms:isPartOf on Collections (redundant with skos:inScheme)
    if p == DCTERMS.isPartOf and s in collections:
        return None

    # Drop history/provenance notes on ConceptScheme (replaced by config-generated historyNote)
    # These would otherwise be transformed to skos:changeNote which is not wanted on scheme
    if s in concept_schemes and p in (
        SKOS.historyNote,
        DCTERMS.provenance,
        PROV.wasDerivedFrom,
    ):
        return None

    # Transform dcterms:identifier from "prefix_ID" to just "ID"
    # Only for concepts and collections, not for ConceptScheme
    if p == DCTERMS.identifier and s not in concept_schemes and id_pattern:
        old_value = str(o)
        match = id_pattern.search(old_value)
        if match:
            new_value = match.group("identifier")
            return (s, p, Literal(new_value, datatype=XSD.token))
        # Pattern didn't match - log warning and keep original
        logger.warning(
            "Could not extract ID from identifier '%s' using pattern %s",
            old_value,
            id_pattern.pattern,
        )
        return (s, p, o)

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
