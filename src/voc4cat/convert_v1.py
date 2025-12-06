"""Converter for RDF vocabularies to/from v1.0 Excel template format.

This module provides functions to convert between RDF vocabularies and
the v1.0 Excel template structure, supporting bidirectional conversion:
- RDF -> XLSX: Extract data from RDF graphs into v1.0 template
- XLSX -> RDF: Read v1.0 template and generate RDF graph

The two-way conversion is designed to be lossless (isomorphic graphs).
"""

import logging
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
    TEMPLATE_VERSION,
    CollectionV1,
    ConceptSchemeV1,
    ConceptV1,
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


def extract_concepts_from_rdf(graph: Graph) -> dict[str, dict[str, dict]]:
    """Extract Concepts from an RDF graph, grouped by IRI and language.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Nested dict: {concept_iri: {language: concept_data_dict}}
        Each concept_data_dict contains: preferred_label, definition,
        alternate_labels, parent_iris, source_vocab_iri, change_note.
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
            "parent_iris": [],
            "source_vocab_iri": "",
            "change_note": "",
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
            elif p == SKOS.broader:
                data["parent_iris"].append(str(o))
            elif p == RDFS.isDefinedBy:
                data["source_vocab_iri"] = str(o)
            elif p in [SKOS.historyNote, DCTERMS.provenance, PROV.wasDerivedFrom]:
                data["change_note"] = str(o)

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
            concepts_by_iri_lang[iri][lang] = {
                "preferred_label": data["pref_labels"].get(lang, ""),
                "definition": data["definitions"].get(lang, ""),
                "alternate_labels": data["alt_labels"].get(lang, []),
                "parent_iris": data["parent_iris"],
                "source_vocab_iri": data["source_vocab_iri"],
                "change_note": data["change_note"],
            }

    return dict(concepts_by_iri_lang)


def extract_collections_from_rdf(graph: Graph) -> dict[str, dict[str, dict]]:
    """Extract Collections from an RDF graph, grouped by IRI and language.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Nested dict: {collection_iri: {language: collection_data_dict}}
        Each collection_data_dict contains: preferred_label, definition, change_note.
    """
    collections_by_iri_lang: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(dict)
    )

    # First pass: collect all data per collection
    collection_data: dict[str, dict] = defaultdict(
        lambda: {
            "pref_labels": {},  # {lang: label}
            "definitions": {},  # {lang: definition}
            "change_note": "",
            "members": [],  # member IRIs (concepts or collections)
        }
    )

    for s in graph.subjects(RDF.type, SKOS.Collection):
        iri = str(s)
        data = collection_data[iri]

        for p, o in graph.predicate_objects(s):
            if p == SKOS.prefLabel:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["pref_labels"][lang] = str(o)
            elif p == SKOS.definition:
                lang = o.language if isinstance(o, Literal) and o.language else "en"
                data["definitions"][lang] = str(o)
            elif p in [SKOS.historyNote, DCTERMS.provenance, PROV.wasDerivedFrom]:
                data["change_note"] = str(o)
            elif p == SKOS.member:
                data["members"].append(str(o))

    # Second pass: organize by IRI and language
    for iri, data in collection_data.items():
        all_langs = set(data["pref_labels"].keys()) | set(data["definitions"].keys())

        langs_ordered = sorted(all_langs)
        if "en" in langs_ordered:
            langs_ordered.remove("en")
            langs_ordered.insert(0, "en")

        for lang in langs_ordered:
            collections_by_iri_lang[iri][lang] = {
                "preferred_label": data["pref_labels"].get(lang, ""),
                "definition": data["definitions"].get(lang, ""),
                "change_note": data["change_note"],
                "members": data["members"],
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


def rdf_concepts_to_v1(
    concepts_data: dict[str, dict[str, dict]],
    concept_to_collections: dict[str, list[str]],
) -> list[ConceptV1]:
    """Convert extracted concepts to ConceptV1 models.

    Creates one ConceptV1 row per (concept_iri, language) combination.
    The first row for each concept includes: parent_iris, member_of_collections.
    Subsequent rows (other languages) have these fields empty.

    Args:
        concepts_data: Nested dict from extract_concepts_from_rdf.
        concept_to_collections: Mapping from concept IRI to collection IRIs.

    Returns:
        List of ConceptV1 model instances.
    """
    concepts_v1 = []

    # Use curies converter to compress IRIs
    converter = config.curies_converter

    for concept_iri, lang_data in concepts_data.items():
        is_first_row = True

        for lang, data in lang_data.items():
            # Compress the concept IRI
            concept_iri_display = converter.compress(concept_iri, passthrough=True)

            # Format alternate labels (join with separator)
            alt_labels = data.get("alternate_labels", [])
            alt_labels_str = " | ".join(alt_labels) if alt_labels else ""

            # Only include structural data in first row
            if is_first_row:
                # Format parent IRIs
                parent_iris = data.get("parent_iris", [])
                parent_iris_strs = [
                    converter.compress(p, passthrough=True) for p in parent_iris
                ]
                parent_iris_str = " ".join(parent_iris_strs)

                # Format member_of_collections
                collections = concept_to_collections.get(concept_iri, [])
                collections_strs = [
                    converter.compress(c, passthrough=True) for c in collections
                ]
                member_of_collections_str = " ".join(collections_strs)

                source_vocab_iri = data.get("source_vocab_iri", "")
                change_note = data.get("change_note", "")

                is_first_row = False
            else:
                parent_iris_str = ""
                member_of_collections_str = ""
                source_vocab_iri = ""
                change_note = ""

            concepts_v1.append(
                ConceptV1(
                    concept_iri=concept_iri_display,
                    language_code=lang,
                    preferred_label=data.get("preferred_label", ""),
                    definition=data.get("definition", ""),
                    alternate_labels=alt_labels_str,
                    parent_iris=parent_iris_str,
                    member_of_collections=member_of_collections_str,
                    source_vocab_iri=source_vocab_iri,
                    change_note=change_note,
                )
            )

    return concepts_v1


def rdf_collections_to_v1(
    collections_data: dict[str, dict[str, dict]],
    collection_to_parents: dict[str, list[str]],
) -> list[CollectionV1]:
    """Convert extracted collections to CollectionV1 models.

    Creates one CollectionV1 row per (collection_iri, language) combination.

    Args:
        collections_data: Nested dict from extract_collections_from_rdf.
        collection_to_parents: Mapping from collection IRI to parent collection IRIs.

    Returns:
        List of CollectionV1 model instances.
    """
    collections_v1 = []

    converter = config.curies_converter

    for collection_iri, lang_data in collections_data.items():
        is_first_row = True

        for lang, data in lang_data.items():
            collection_iri_display = converter.compress(
                collection_iri, passthrough=True
            )

            if is_first_row:
                # Format parent collection IRIs
                parents = collection_to_parents.get(collection_iri, [])
                parents_strs = [
                    converter.compress(p, passthrough=True) for p in parents
                ]
                parent_iris_str = " ".join(parents_strs)

                change_note = data.get("change_note", "")

                is_first_row = False
            else:
                parent_iris_str = ""
                change_note = ""

            collections_v1.append(
                CollectionV1(
                    collection_iri=collection_iri_display,
                    language_code=lang,
                    preferred_label=data.get("preferred_label", ""),
                    definition=data.get("definition", ""),
                    parent_collection_iris=parent_iris_str,
                    change_note=change_note,
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
# Excel Export Function
# =============================================================================


def export_vocabulary_v1(
    concept_scheme: ConceptSchemeV1,
    concepts: list[ConceptV1],
    collections: list[CollectionV1],
    mappings: list[MappingV1],
    prefixes: list[PrefixV1],
    output_path: Path,
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
    """
    # 1. Concept Scheme (key-value format)
    kv_config = XLSXKeyValueConfig(title="Concept Scheme")
    export_to_xlsx(
        concept_scheme,
        output_path,
        format_type="keyvalue",
        config=kv_config,
        sheet_name="Concept Scheme",
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

    # 5. Prefixes (table format)
    table_config = XLSXTableConfig(title="Prefix mappings")
    export_to_xlsx(
        prefixes,
        output_path,
        format_type="table",
        config=table_config,
        sheet_name="Prefixes",
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
        "Concept Scheme",
        "Concepts",
        "Collections",
        "Mappings",
        "Prefixes",
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
) -> Path:
    """Convert an RDF vocabulary to v1.0 Excel template.

    Args:
        file_to_convert_path: Path to the RDF file (.ttl, .rdf, etc.).
        output_file_path: Optional path for output Excel file.
                         Defaults to same name with .xlsx extension.

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

    logger.debug("Building collection hierarchy map...")
    collection_to_parents = build_collection_hierarchy_map(graph)

    # Convert to v1.0 models
    logger.debug("Converting to v1.0 models...")
    concept_scheme_v1 = rdf_concept_scheme_to_v1(cs_data)
    concepts_v1 = rdf_concepts_to_v1(concepts_data, concept_to_collections)
    collections_v1 = rdf_collections_to_v1(collections_data, collection_to_parents)
    mappings_v1 = rdf_mappings_to_v1(mappings_data)
    prefixes_v1 = build_prefixes_v1()

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
    parent_iris: list[str] = field(default_factory=list)
    member_of_collections: list[str] = field(default_factory=list)
    source_vocab_iri: str = ""
    change_note: str = ""


@dataclass
class AggregatedCollection:
    """Aggregated collection data from multiple XLSX rows (one per language)."""

    iri: str
    pref_labels: dict[str, str] = field(default_factory=dict)  # {lang: label}
    definitions: dict[str, str] = field(default_factory=dict)  # {lang: definition}
    parent_collection_iris: list[str] = field(default_factory=list)
    change_note: str = ""


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
        sheet_name="Concept Scheme",
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
    config = XLSXTableConfig(title="Prefix mappings")
    return import_from_xlsx(
        filepath,
        PrefixV1,
        format_type="table",
        config=config,
        sheet_name="Prefixes",
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


# --- Aggregation Functions ---


def aggregate_concepts(
    concept_rows: list[ConceptV1], converter: curies.Converter
) -> dict[str, AggregatedConcept]:
    """Aggregate multi-row concept data into single AggregatedConcept per IRI.

    The v1.0 template has one row per (concept_iri, language). This function
    merges them back:
    - First row for each IRI contains structural data (parent_iris, etc.)
    - All rows contribute language-specific data (pref_label, definition, alt_labels)

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
            # First row for this concept - create new entry
            concepts[iri] = AggregatedConcept(
                iri=iri,
                parent_iris=expand_iri_list(row.parent_iris, converter),
                member_of_collections=expand_iri_list(
                    row.member_of_collections, converter
                ),
                source_vocab_iri=expand_curie(row.source_vocab_iri, converter)
                if row.source_vocab_iri
                else "",
                change_note=row.change_note or "",
            )

        concept = concepts[iri]

        # Add language-specific data
        lang = row.language_code or "en"
        if row.preferred_label:
            concept.pref_labels[lang] = row.preferred_label
        if row.definition:
            concept.definitions[lang] = row.definition
        if row.alternate_labels:
            # Split by " | " separator
            labels = [lbl.strip() for lbl in row.alternate_labels.split(" | ")]
            concept.alt_labels[lang] = labels

    return concepts


def aggregate_collections(
    collection_rows: list[CollectionV1], converter: curies.Converter
) -> dict[str, AggregatedCollection]:
    """Aggregate multi-row collection data into single AggregatedCollection per IRI.

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
            # First row for this collection
            collections[iri] = AggregatedCollection(
                iri=iri,
                parent_collection_iris=expand_iri_list(
                    row.parent_collection_iris, converter
                ),
                change_note=row.change_note or "",
            )

        collection = collections[iri]

        # Add language-specific data
        lang = row.language_code or "en"
        if row.preferred_label:
            collection.pref_labels[lang] = row.preferred_label
        if row.definition:
            collection.definitions[lang] = row.definition

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
) -> Graph:
    """Build RDF graph for a single Concept.

    Args:
        concept: Aggregated concept data.
        scheme_iri: URIRef of the ConceptScheme.
        narrower_map: Map of parent -> children for narrower relationships.

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

    # Broader (parent)
    for parent_iri in concept.parent_iris:
        g.add((c, SKOS.broader, URIRef(parent_iri)))

    # Narrower (computed inverse)
    for child_iri in narrower_map.get(concept.iri, []):
        g.add((c, SKOS.narrower, URIRef(child_iri)))

    # In scheme
    g.add((c, SKOS.inScheme, scheme_iri))

    # rdfs:isDefinedBy - only add if source_vocab_iri is specified
    # It indicates the vocabulary that defines the concept. If not provided,
    # the concept is understood to be defined by the current scheme.
    if concept.source_vocab_iri:
        g.add((c, RDFS.isDefinedBy, URIRef(concept.source_vocab_iri)))

    # Top concept of (if no broader)
    if not concept.parent_iris:
        g.add((c, SKOS.topConceptOf, scheme_iri))

    # Change note / history note
    if concept.change_note:
        g.add((c, SKOS.historyNote, Literal(concept.change_note, lang="en")))

    return g


def build_collection_graph(
    collection: AggregatedCollection,
    scheme_iri: URIRef,
    collection_members: dict[str, list[str]],
) -> Graph:
    """Build RDF graph for a single Collection.

    Args:
        collection: Aggregated collection data.
        scheme_iri: URIRef of the ConceptScheme.
        collection_members: Map of collection -> member IRIs.

    Returns:
        Graph with Collection triples.
    """
    g = Graph()
    c = URIRef(collection.iri)

    # Type
    g.add((c, RDF.type, SKOS.Collection))

    # Identifier
    identifier = extract_identifier(collection.iri)
    g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

    # Labels per language
    for lang, label in collection.pref_labels.items():
        g.add((c, SKOS.prefLabel, Literal(label, lang=lang)))

    for lang, definition in collection.definitions.items():
        g.add((c, SKOS.definition, Literal(definition, lang=lang)))

    # Members (from inverted concept membership)
    for member_iri in collection_members.get(collection.iri, []):
        g.add((c, SKOS.member, URIRef(member_iri)))

    # In scheme
    g.add((c, SKOS.inScheme, scheme_iri))

    # rdfs:isDefinedBy - points to ConceptScheme (convention)
    g.add((c, RDFS.isDefinedBy, scheme_iri))

    # isPartOf
    g.add((c, DCTERMS.isPartOf, scheme_iri))

    # Change note / history note
    if collection.change_note:
        g.add((c, SKOS.historyNote, Literal(collection.change_note, lang="en")))

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
) -> Path | Graph:
    """Convert a v1.0 Excel template to RDF vocabulary.

    Args:
        file_to_convert_path: Path to the XLSX file.
        output_file_path: Optional path for output RDF file.
                         Defaults to same name with .ttl extension.
        output_format: RDF serialization format ("turtle", "xml", "json-ld").
        output_type: "file" to serialize to file, "graph" to return Graph object.

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

    # Read all sheets
    logger.debug("Reading Concept Scheme...")
    concept_scheme = read_concept_scheme_v1(file_to_convert_path)

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
    narrower_map = build_narrower_map(concepts)

    # Build the complete graph
    logger.debug("Building RDF graph...")
    scheme_iri = URIRef(concept_scheme.vocabulary_iri)

    graph = build_concept_scheme_graph(concept_scheme, concepts, collections)

    for concept in concepts.values():
        graph += build_concept_graph(concept, scheme_iri, narrower_map)

    for collection in collections.values():
        graph += build_collection_graph(collection, scheme_iri, collection_members)

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
