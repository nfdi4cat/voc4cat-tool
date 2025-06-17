#!/usr/bin/env python3
"""
Demo: Vocabulary Template using Unified XLSX Processor

This demo reproduces the structure of the blank_1.0_min.xlsx template using
the unified XLSX processor system. It creates the following sheets:
- ConceptScheme (key-value format)
- Concepts (multi-language joined model format)
- Collections (table format)
- Mappings (table format)
- Prefixes (table format)

The demo uses multi-language concepts as the primary concept model with
proper SKOS meanings and enum validation for obsoletion fields.
Units are not used as specified.
"""

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from voc4cat.xlsx_api import XLSXProcessorFactory, export_to_xlsx
from voc4cat.xlsx_common import XLSXConverters, XLSXMetadata
from voc4cat.xlsx_keyvalue import XLSXKeyValueConfig
from voc4cat.xlsx_table import JoinConfiguration, XLSXTableConfig


# Enums for validation
class ObsoletionReason(Enum):
    """Reasons for obsoleting vocabulary elements."""

    UNCLEAR_DEFINITION = "Not clearly defined or inconsistent usage."
    ADDED_IN_ERROR = "Added in error."
    MORE_SPECIFIC_CREATED = "More specific concepts created."
    CONVERTED_TO_COLLECTION = "Converted to a collection."
    AMBIGUOUS_MEANING = "The meaning was ambiguous."
    LACK_OF_EVIDENCE = "Lack of evidence that this function/process/component exists."


# class MappingTypeObsoletionReason(Enum):
class MappingType(Enum):
    """Type of SKOS mapping relation."""

    EXACT_MATCH = "skos:exactMatch"
    CLOSE_MATCH = "skos:closeMatch"
    NARROW_MATCH = "skos:narrowMatch"
    BROAD_MATCH = "skos:broadMatch"
    RELATED_MATCH = "skos:relatedMatch"


class CollectionObsoletionReason(Enum):
    """Reasons for obsoleting collections."""

    UNCLEAR_DEFINITION = "Not clearly defined or inconsistent usage."
    ADDED_IN_ERROR = "Added in error."
    MORE_SPECIFIC_CREATED = "More specific colllections were created."
    CONVERTED_TO_CONCEPT = "Converted to a concept."


# Models
class ConceptScheme(BaseModel):
    """Concept scheme metadata (key-value format)."""

    template_version: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:hasVersion",
            description="Gets increments only on structural changes. Its general pattern is major.minor.rev-JJJJ-MM[a-z].",
        ),
    ] = Field(default="1.0.rev-2025-06a")

    vocabulary_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Vocabulary IRI",
            meaning="skos:conceptScheme",
            description="IRI for this vocabulary",
        ),
    ] = Field(...)

    prefix: Annotated[
        str,
        XLSXMetadata(
            meaning="vann:preferredNamespacePrefix",
            description="Registered (or preferred) prefix to be used in CURIES for this vocabulary",
        ),
    ] = Field(...)

    title: Annotated[
        str,
        XLSXMetadata(meaning="dcterms:title", description="Title of the vocabulary"),
    ] = Field(...)

    description: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:description",
            description="General description of the vocabulary",
        ),
    ] = Field(...)

    version: Annotated[
        str,
        XLSXMetadata(
            meaning="owl:versionInfo",
            description="Automatically added version specifier for the vocabulary",
        ),
    ] = Field(...)

    modified_date: Annotated[
        date,
        XLSXMetadata(
            meaning="dcterms:modified",
            description="Automatically added date of last modification",
        ),
    ] = Field(default_factory=date.today)


class Mapping(BaseModel):
    """External mapping between concepts (table format)."""

    concept_iri: Annotated[
        str, XLSXMetadata(meaning="skos:Concept", description="IRI of Voc4Cat Concept")
    ] = Field(...)

    mapping_relation: Annotated[
        MappingType | None,
        XLSXMetadata(
            meaning="skos:mappingRelation", description="Type of mapping relation."
        ),
    ] = Field(None)

    mapped_external_concept: str | None = Field(
        None,
        description="IRI of mapped external concept",
    )


class Collection(BaseModel):
    """Collection of concepts (table format)."""

    collection_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Collection, skos:orderedCollection",
            description="Collection IRI",
        ),
    ] = Field(...)

    language_code: Annotated[
        str, XLSXMetadata(meaning="dcterms:language", description="Language Code")
    ] = Field(default="en")

    preferred_label: Annotated[
        str, XLSXMetadata(meaning="skos:preferredLabel", description="Preferred Label")
    ] = Field(...)

    definition: Annotated[
        str, XLSXMetadata(meaning="skos:definition", description="Definition")
    ] = Field(...)

    # Your specific example: left_spacing=" ", separator="|", right_spacing="\n"
    # custom_pattern = SeparatorPattern("|", " ", "\n", EscapeMode.BACKSLASH)
    parent_collection_iris: (
        Annotated[
            list[str],
            XLSXMetadata(
                separator_pattern=XLSXConverters.PIPE_ESCAPED,
                meaning="skos:member",
                description="Parent Collection IRIs",
            ),
        ]
        | None
    ) = Field(default=None)

    is_ordered: bool = Field(
        default=False,
        description="Ordered? Yes or No (default)",
    )

    change_note: (
        Annotated[
            str, XLSXMetadata(meaning="skos:changeNote", description="Change Note")
        ]
        | None
    ) = Field(None)

    editorial_note: (
        Annotated[
            str,
            XLSXMetadata(meaning="skos:editorialNote", description="Editorial Note"),
        ]
        | None
    ) = Field(None)

    obsoletion_reason: CollectionObsoletionReason | None = Field(
        None, description="Reason for obsoletion if applicable"
    )


class Prefix(BaseModel):
    """Namespace prefix mapping (table format)."""

    prefix: Annotated[
        str, XLSXMetadata(meaning="vann:preferredNamespacePrefix", description="Prefix")
    ] = Field(...)

    namespace: Annotated[
        str, XLSXMetadata(meaning="vann:preferredNamespaceUri", description="Namespace")
    ] = Field(...)


# Multi-language models for joined demonstration
class ConceptTranslation(BaseModel):
    """Translation of a concept in a specific language."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Concept",
            description="IRI of the concept being translated",
        ),
    ] = Field(...)

    language_code: Annotated[
        str,
        XLSXMetadata(
            meaning="dcterms:language",
            description="ISO 639-1 language code (e.g., 'en', 'de', 'fr')",
        ),
    ] = Field(...)

    preferred_label: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:prefLabel",
            description="Preferred label in this language",
        ),
    ] = Field(...)

    alternate_labels: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.COMMA,
            meaning="skos:altLabel",
            description="Alternative labels in this language",
        ),
    ] = Field(default_factory=list)

    definition: Annotated[
        str | None,
        XLSXMetadata(
            meaning="skos:definition",
            description="Definition of the concept in this language",
        ),
    ] = Field(None)

    scope_note: Annotated[
        str | None,
        XLSXMetadata(
            meaning="skos:scopeNote",
            description="Scope note in this language",
        ),
    ] = Field(None)


class MultiLingualConcept(BaseModel):
    """Concept with multi-language support for joined model demonstration."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            meaning="skos:Concept",
            description="Unique IRI identifier for this concept",
        ),
    ] = Field(...)

    # Related concepts and collections remain language-independent
    parent_iris: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.PIPE,
            meaning="skos:broader",
            description="Parent concept IRIs",
        ),
    ] = Field(default_factory=list)

    collection_membership: Annotated[
        list[str],
        XLSXMetadata(
            separator_pattern=XLSXConverters.PIPE,
            meaning="skos:member",
            description="Collection IRIs this concept belongs to",
        ),
    ] = Field(default_factory=list)

    # Administrative metadata
    created_date: Annotated[
        date,
        XLSXMetadata(
            meaning="dcterms:created",
            description="Date when this concept was created",
        ),
    ] = Field(default_factory=date.today)

    status: Annotated[
        str,
        XLSXMetadata(
            meaning="adms:status",
            description="Status of this concept (draft, published, deprecated)",
        ),
    ] = Field(default="draft")

    # Translations will be joined from ConceptTranslation
    translations: list[ConceptTranslation] = Field(default_factory=list)


def create_sample_data():
    """Create sample vocabulary data."""

    # Concept Scheme (single record)
    concept_scheme = ConceptScheme(
        vocabulary_iri="https://example.org/photocatalysis/",
        prefix="photo",
        title="Photocatalysis Vocabulary",
        description="A controlled vocabulary for photocatalysis research and applications",
        version="1.0.0",
    )

    # Mappings (external concept mappings)
    mappings = [
        Mapping(
            concept_iri="https://example.org/photocatalysis/TiO2",
            mapping_relation=MappingType.EXACT_MATCH,
            mapped_external_concept="http://purl.obolibrary.org/obo/CHEBI_32234",
        ),
        Mapping(
            concept_iri="https://example.org/photocatalysis/Semiconductor",
            mapping_relation=MappingType.CLOSE_MATCH,
            mapped_external_concept="https://dbpedia.org/resource/Semiconductor",
        ),
        Mapping(
            concept_iri="https://example.org/photocatalysis/Semiconductor",
            mapping_relation=MappingType.RELATED_MATCH,
            mapped_external_concept="http://purl.obolibrary.org/obo/CHEBI_26278",
        ),
    ]

    # Collections (concept groupings)
    collections = [
        Collection(
            collection_iri="https://example.org/photocatalysis/PhotocatalystMaterials",
            preferred_label="Photocatalyst Materials",
            definition="Collection of materials used as photocatalysts",
            is_ordered=True,
        ),
        Collection(
            collection_iri="https://example.org/photocatalysis/OpticalProperties",
            preferred_label="Optical Properties",
            definition="Collection of optical properties relevant to photocatalysis",
            parent_collection_iris=[
                "https://example.org/photocatalysis/MaterialProperties",
                "https://example.org/photocatalysis/PhysicalProperties",
            ],
        ),
        Collection(
            collection_iri="https://example.org/photocatalysis/ObsoleteCollection",
            preferred_label="Obsolete Collection",
            definition="This collection is no longer used",
            obsoletion_reason=CollectionObsoletionReason.CONVERTED_TO_CONCEPT,
        ),
    ]

    # Prefixes (namespace mappings)
    prefixes = [
        Prefix(prefix="skos", namespace="http://www.w3.org/2004/02/skos/core#"),
        Prefix(prefix="dcterms", namespace="http://purl.org/dc/terms/"),
        Prefix(prefix="owl", namespace="http://www.w3.org/2002/07/owl#"),
        Prefix(prefix="rdf", namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
        Prefix(prefix="rdfs", namespace="http://www.w3.org/2000/01/rdf-schema#"),
        Prefix(prefix="vann", namespace="http://purl.org/vocab/vann/"),
        Prefix(prefix="photo", namespace="https://example.org/photocatalysis/"),
        Prefix(prefix="chebi", namespace="http://purl.obolibrary.org/obo/CHEBI_"),
    ]

    return concept_scheme, mappings, collections, prefixes


def create_multilingual_sample_data():
    """Create sample multi-language vocabulary data."""

    # Create concepts with multiple language translations
    multilingual_concepts = [
        MultiLingualConcept(
            concept_iri="https://example.org/photocatalysis/TiO2",
            parent_iris=["https://example.org/photocatalysis/PhotocatalystMaterials"],
            collection_membership=["https://example.org/photocatalysis/Materials"],
            status="published",
            translations=[
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/TiO2",
                    language_code="en",
                    preferred_label="Titanium Dioxide",
                    alternate_labels=["Titania", "Titanium(IV) oxide", "TiO₂"],
                    definition="A widely used photocatalyst material with the chemical formula TiO2, known for its excellent photocatalytic properties and UV absorption.",
                    scope_note="Commonly used in self-cleaning surfaces and air purification applications.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/TiO2",
                    language_code="de",
                    preferred_label="Titandioxid",
                    alternate_labels=["Titania", "Titan(IV)-oxid"],
                    definition="Ein weit verbreitetes Photokatalysator-Material mit der chemischen Formel TiO2, bekannt für seine ausgezeichneten photokatalytischen Eigenschaften.",
                    scope_note="Häufig verwendet in selbstreinigenden Oberflächen und Luftreinigungsanwendungen.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/TiO2",
                    language_code="fr",
                    preferred_label="Dioxyde de titane",
                    alternate_labels=["Titania", "Oxyde de titane(IV)"],
                    definition="Un matériau photocatalyseur largement utilisé avec la formule chimique TiO2, connu pour ses excellentes propriétés photocatalytiques.",
                    scope_note="Couramment utilisé dans les surfaces autonettoyantes et les applications de purification de l'air.",
                ),
            ],
        ),
        MultiLingualConcept(
            concept_iri="https://example.org/photocatalysis/BandGap",
            parent_iris=[
                "https://example.org/photocatalysis/MaterialProperty",
                "https://example.org/photocatalysis/ElectronicProperty",
            ],
            collection_membership=[
                "https://example.org/photocatalysis/OpticalProperties"
            ],
            status="published",
            translations=[
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/BandGap",
                    language_code="en",
                    preferred_label="Band Gap",
                    alternate_labels=[
                        "Energy gap",
                        "Forbidden gap",
                        "Electronic band gap",
                    ],
                    definition="The energy difference between the valence and conduction bands in a material, determining its electrical and optical properties.",
                    scope_note="Critical parameter for photocatalytic activity and light absorption characteristics.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/BandGap",
                    language_code="de",
                    preferred_label="Bandlücke",
                    alternate_labels=[
                        "Energielücke",
                        "Verbotene Zone",
                        "Elektronische Bandlücke",
                    ],
                    definition="Der Energieunterschied zwischen Valenz- und Leitungsband in einem Material, der seine elektrischen und optischen Eigenschaften bestimmt.",
                    scope_note="Kritischer Parameter für photokatalytische Aktivität und Lichtabsorptionseigenschaften.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/BandGap",
                    language_code="fr",
                    preferred_label="Bande interdite",
                    alternate_labels=[
                        "Gap énergétique",
                        "Zone interdite",
                        "Bande interdite électronique",
                    ],
                    definition="La différence d'énergie entre les bandes de valence et de conduction dans un matériau, déterminant ses propriétés électriques et optiques.",
                    scope_note="Paramètre critique pour l'activité photocatalytique et les caractéristiques d'absorption de la lumière.",
                ),
            ],
        ),
        MultiLingualConcept(
            concept_iri="https://example.org/photocatalysis/Photolysis",
            parent_iris=["https://example.org/photocatalysis/PhotochemicalProcess"],
            collection_membership=[
                "https://example.org/photocatalysis/ChemicalProcesses"
            ],
            status="draft",
            translations=[
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/Photolysis",
                    language_code="en",
                    preferred_label="Photolysis",
                    alternate_labels=[
                        "Photodecomposition",
                        "Light-induced decomposition",
                    ],
                    definition="The decomposition or breakdown of chemical compounds by the action of light energy.",
                    scope_note="Fundamental process in photocatalytic reactions and environmental remediation.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/Photolysis",
                    language_code="de",
                    preferred_label="Photolyse",
                    alternate_labels=[
                        "Photodekomposition",
                        "Lichtinduzierte Zersetzung",
                    ],
                    definition="Die Zersetzung oder der Abbau chemischer Verbindungen durch die Einwirkung von Lichtenergie.",
                    scope_note="Grundlegender Prozess in photokatalytischen Reaktionen und Umweltsanierung.",
                ),
            ],
        ),
        MultiLingualConcept(
            concept_iri="https://example.org/photocatalysis/Semiconductor",
            parent_iris=[],
            collection_membership=["https://example.org/photocatalysis/Materials"],
            status="published",
            translations=[
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/Semiconductor",
                    language_code="en",
                    preferred_label="Semiconductor",
                    alternate_labels=["Semiconducting material"],
                    definition="A material with electrical conductivity between that of a conductor and insulator.",
                    scope_note="Essential component in photocatalytic systems.",
                ),
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/Semiconductor",
                    language_code="de",
                    preferred_label="Halbleiter",
                    alternate_labels=["Halbleitermaterial"],
                    definition="Ein Material mit einer elektrischen Leitfähigkeit zwischen der eines Leiters und eines Isolators.",
                    scope_note="Wesentlicher Bestandteil in photokatalytischen Systemen.",
                ),
            ],
        ),
        MultiLingualConcept(
            concept_iri="https://example.org/photocatalysis/ObsoleteConcept",
            parent_iris=[],
            collection_membership=[],
            status="deprecated",
            translations=[
                ConceptTranslation(
                    concept_iri="https://example.org/photocatalysis/ObsoleteConcept",
                    language_code="en",
                    preferred_label="Obsolete Concept",
                    alternate_labels=[],
                    definition="This concept is no longer used.",
                    scope_note="Deprecated due to unclear definition.",
                ),
            ],
        ),
    ]

    return multilingual_concepts


def main():
    """Main demo function."""
    print("🔬 Vocabulary Template Demo using Unified XLSX Processor")
    print("=" * 60)

    # Create sample data
    concept_scheme, mappings, collections, prefixes = create_sample_data()

    # Create multi-language concepts
    multilingual_concepts = create_multilingual_sample_data()

    # Output file
    output_file = Path("vocabulary_template_demo.xlsx")

    # Remove existing file to avoid sheet name conflicts
    if output_file.exists():
        output_file.unlink()

    # Configuration for key-value format (ConceptScheme)
    # Note: Units disabled, descriptions and meanings enabled
    kv_config = XLSXKeyValueConfig(
        title="Concept Scheme Metadata",
    )

    # Configuration for table format (other sheets)
    # Note: All metadata (descriptions, meanings, units) are always shown
    table_config = XLSXTableConfig()

    print("📊 Exporting vocabulary data...")

    # Export ConceptScheme (key-value format)
    print("  ✓ ConceptScheme (key-value format)")
    export_to_xlsx(
        concept_scheme,
        output_file,
        format_type="keyvalue",
        config=kv_config,
        sheet_name="ConceptScheme",
    )

    # Configure the join between MultiLingualConcept and ConceptTranslation
    join_config = JoinConfiguration(
        primary_model=MultiLingualConcept,
        related_models={"translations": ConceptTranslation},
        join_keys={"translations": "concept_iri"},
        flattened_fields=[
            "concept_iri",
            "language_code",
            "preferred_label",
            "alternate_labels",
            "definition",
            "scope_note",
            "parent_iris",
            "collection_membership",
            "created_date",
            "status",
        ],
        field_mappings={
            "concept_iri": ("primary", "concept_iri"),
            "language_code": ("related", "language_code"),
            "preferred_label": ("related", "preferred_label"),
            "alternate_labels": ("related", "alternate_labels"),
            "definition": ("related", "definition"),
            "scope_note": ("related", "scope_note"),
            "parent_iris": ("primary", "parent_iris"),
            "collection_membership": ("primary", "collection_membership"),
            "created_date": ("primary", "created_date"),
            "status": ("primary", "status"),
        },
        list_fields={"alternate_labels", "parent_iris", "collection_membership"},
    )

    # Configure the joined table with enhanced styling
    concepts_config = XLSXTableConfig(
        title="Multi-Language Concepts",
    )

    # Create the joined table processor
    joined_processor = XLSXProcessorFactory.create_joined_table_processor(
        join_config, concepts_config
    )

    # Export the multi-language concepts as the main Concepts sheet
    joined_processor.export(multilingual_concepts, output_file, "Concepts")
    print("  ✓ Concepts (multi-language joined model format)")

    # Export Collections (table format)
    print("  ✓ Collections (table format)")
    table_config.title = "Collections"
    export_to_xlsx(
        collections,
        output_file,
        format_type="table",
        config=table_config,
        sheet_name="Collections",
    )

    # Export Mappings (table format)
    print("  ✓ Mappings (table format)")
    table_config.title = "External Mappings"
    export_to_xlsx(
        mappings,
        output_file,
        format_type="table",
        config=table_config,
        sheet_name="Mappings",
    )

    # Export Prefixes (table format)
    print("  ✓ Prefixes (table format)")
    prefixes_config = XLSXTableConfig(
        title="Prefix mappings",
    )
    export_to_xlsx(
        prefixes,
        output_file,
        format_type="table",
        config=prefixes_config,
        sheet_name="Prefixes",
    )

    print(f"\n✅ Vocabulary template exported to: {output_file}")
    print("\nSheet structure:")
    print(
        "📋 ConceptScheme - Key-value format with Field|Value|Description|Meaning columns"
    )
    print("📊 Concepts - Multi-language joined model format with translations")
    print("📊 Collections - Table format with Meaning, Description, HEADER-ROW")
    print("📊 Mappings - Table format with Meaning, Description, HEADER-ROW")
    print("📊 Prefixes - Table format with Meaning, Description, HEADER-ROW")
    print("\n🔧 Features demonstrated:")
    print("  • Key-value vs table format selection")
    print("  • SKOS meanings for vocabulary fields")
    print("  • Enum validation for obsoletion reasons")
    print("  • Multiple sheets in single workbook")
    print("  • Joined model approach for concept translations")
    print("  • Flattened hierarchical data representation")


if __name__ == "__main__":
    main()
