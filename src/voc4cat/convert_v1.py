"""Converter for RDF vocabularies to v1.0 Excel template format.

This module provides functions to convert existing RDF vocabularies into
the v1.0 Excel template structure. It extracts data from RDF graphs and
outputs to the v1.0 template using the xlsx_api infrastructure.
"""

import logging
from collections import defaultdict
from pathlib import Path

from rdflib import DCAT, DCTERMS, OWL, PROV, RDF, RDFS, SKOS, Graph, Literal

from voc4cat import config
from voc4cat.models_v1 import (
    TEMPLATE_VERSION,
    CollectionV1,
    ConceptSchemeV1,
    ConceptV1,
    MappingV1,
    PrefixV1,
)
from voc4cat.utils import RDF_FILE_ENDINGS
from voc4cat.xlsx_api import export_to_xlsx
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import XLSXTableConfig

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
