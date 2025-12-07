"""Pydantic models for voc4cat v1.0 template.

These models define the structure of the v1.0 Excel template using XLSXMetadata
annotations to specify column headers, SKOS meanings, and field descriptions.
"""

from typing import Annotated

from pydantic import BaseModel

from voc4cat.xlsx_common import XLSXMetadata

TEMPLATE_VERSION = "1.0.rev-2025-06a"


# === Obsoletion Reason Enums ===

OBSOLETION_REASONS_CONCEPTS = [
    "The concept is not clearly defined and usage has been inconsistent.",
    "This concept was added in error.",
    "More specific concepts were created.",
    "This concept was converted to a collection.",
    "The meaning of the concept is ambiguous.",
    "Lack of evidence that this function/process/component exists.",
]

OBSOLETION_REASONS_COLLECTIONS = [
    "The collection is not clearly defined and usage has been inconsistent.",
    "This collection was added in error.",
    "More collections were created.",
    "This collection was converted to a concept.",
]


# === Concept Scheme (key-value format) ===


class ConceptSchemeV1(BaseModel):
    """Concept Scheme metadata - rendered as key-value pairs in Excel."""

    template_version: Annotated[
        str,
        XLSXMetadata(
            display_name="Template version",
            description=(
                "The version number changes only on structural changes. "
                "The version number is of type major.minor.rev-JJJJ-MM[a-z]."
            ),
        ),
    ] = TEMPLATE_VERSION

    vocabulary_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Vocabulary IRI",
            description="IRI for this vocabulary",
            meaning="skos:ConceptScheme",
        ),
    ] = ""

    prefix: Annotated[
        str,
        XLSXMetadata(
            display_name="Prefix",
            description="Registered (or preferred) prefix to be used in CURIES for this vocabulary",
        ),
    ] = ""

    title: Annotated[
        str,
        XLSXMetadata(
            display_name="Title",
            description="Title of the vocabulary",
        ),
    ] = ""

    description: Annotated[
        str,
        XLSXMetadata(
            display_name="Description",
            description="General description of the vocabulary",
        ),
    ] = ""

    version: Annotated[
        str,
        XLSXMetadata(
            display_name="Version",
            description="Automatically added version specifier for the vocabulary",
            meaning="owl:versionInfo",
        ),
    ] = ""

    modified_date: Annotated[
        str,
        XLSXMetadata(
            display_name="Modified Date",
            description="Automatically added date of last modification",
            meaning="dct:modified",
        ),
    ] = ""

    created_date: Annotated[
        str,
        XLSXMetadata(
            display_name="Created Date",
            description="Date of creation (ISO-8601-format: YYYY-MM-DD)",
            meaning="dct:created",
        ),
    ] = ""

    creator: Annotated[
        str,
        XLSXMetadata(
            display_name="Creator",
            description='Multi line text; each line must contain: "<orcid-URL or ror> <name>"',
            meaning="dct:creator",
        ),
    ] = ""

    contributor: Annotated[
        str,
        XLSXMetadata(
            display_name="Contributor",
            description="Automatically generated list of contributors",
        ),
    ] = ""

    publisher: Annotated[
        str,
        XLSXMetadata(
            display_name="Publisher",
            description='Multi line text; each line must contain: "<orcid-URL or ror> <name>"',
            meaning="dct:publisher",
        ),
    ] = ""

    change_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Change Note",
            description="A note on the Vocabulary source",
        ),
    ] = ""

    custodian: Annotated[
        str,
        XLSXMetadata(
            display_name="Custodian",
            description='Multi line text; each line contains: "<name> <gh-profile-URL> <orcid-URL>"',
        ),
    ] = ""

    catalogue_pid: Annotated[
        str,
        XLSXMetadata(
            display_name="Catalogue PID",
            description="DOI or other catalogue PID",
        ),
    ] = ""

    documentation: Annotated[
        str,
        XLSXMetadata(
            display_name="Documentation",
            description="URL of documentation or guidelines",
        ),
    ] = ""

    issue_tracker: Annotated[
        str,
        XLSXMetadata(
            display_name="Issue tracker",
            description="URL of issue tracker",
        ),
    ] = ""

    helpdesk: Annotated[
        str,
        XLSXMetadata(
            display_name="Helpdesk",
            description="URL of helpdesk",
        ),
    ] = ""

    repository: Annotated[
        str,
        XLSXMetadata(
            display_name="Repository",
            description="URL of repository or online vocabulary editor",
        ),
    ] = ""

    homepage: Annotated[
        str,
        XLSXMetadata(
            display_name="Homepage",
            description="URL of homepage",
        ),
    ] = ""

    conforms_to: Annotated[
        str,
        XLSXMetadata(
            display_name="Conforms to",
            description="URL of SHACL profile",
        ),
    ] = ""


# === Concepts (table format) ===


class ConceptV1(BaseModel):
    """Single concept row in the Concepts table."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Concept IRI*",
            meaning="skos:Concept",
        ),
    ] = ""

    language_code: Annotated[
        str,
        XLSXMetadata(
            display_name="Language Code*",
        ),
    ] = ""

    preferred_label: Annotated[
        str,
        XLSXMetadata(
            display_name="Preferred Label*",
            meaning="skos:preferredLabel",
        ),
    ] = ""

    definition: Annotated[
        str,
        XLSXMetadata(
            display_name="Definition*",
            meaning="skos:definition",
        ),
    ] = ""

    alternate_labels: Annotated[
        str,
        XLSXMetadata(
            display_name="Alternate Labels",
            meaning="skos:altLabel",
        ),
    ] = ""

    parent_iris: Annotated[
        str,
        XLSXMetadata(
            display_name="Parent IRIs",
            meaning="skos:broader,\nskos:broaderTransitive",
        ),
    ] = ""

    member_of_collections: Annotated[
        str,
        XLSXMetadata(
            display_name="Member of collection(s)",
            meaning="skos:Collection,\nskos:member",
        ),
    ] = ""

    member_of_ordered_collection: Annotated[
        str,
        XLSXMetadata(
            display_name="Member of ordered collection # position",
            meaning="skos:OrderedCollection,\nskos:member",
        ),
    ] = ""

    change_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Change Note",
            meaning="skos:changeNote",
        ),
    ] = ""

    editorial_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Editorial Note",
            meaning="skos:editorialNote",
        ),
    ] = ""

    obsolete_reason: Annotated[
        str,
        XLSXMetadata(
            display_name="Obsoletion reason",
            meaning="owl:deprecated,\nskos:historyNote",
        ),
    ] = ""

    influenced_by_iris: Annotated[
        str,
        XLSXMetadata(
            display_name="Influenced by IRIs",
            meaning="prov:wasInfluencedBy",
        ),
    ] = ""

    source_vocab_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Source Vocab IRI or URL",
            meaning="prov:hadPrimarySource",
        ),
    ] = ""

    source_vocab_license: Annotated[
        str,
        XLSXMetadata(
            display_name="Source Vocab License",
            meaning="dct:license",
        ),
    ] = ""

    source_vocab_rights_holder: Annotated[
        str,
        XLSXMetadata(
            display_name="Source Vocab Rights Holder",
            meaning="dct:rightsHolder",
        ),
    ] = ""


# === Collections (table format) ===


class CollectionV1(BaseModel):
    """Single collection row in the Collections table."""

    collection_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Collection IRI",
            meaning="skos:Collection,\nskos:orderedCollection",
        ),
    ] = ""

    language_code: Annotated[
        str,
        XLSXMetadata(
            display_name="Language Code*",
        ),
    ] = ""

    preferred_label: Annotated[
        str,
        XLSXMetadata(
            display_name="Preferred Label",
            meaning="skos:preferredLabel",
        ),
    ] = ""

    definition: Annotated[
        str,
        XLSXMetadata(
            display_name="Definition",
            meaning="skos:definition",
        ),
    ] = ""

    parent_collection_iris: Annotated[
        str,
        XLSXMetadata(
            display_name="Parent Collection IRIs",
            meaning="skos:member",
        ),
    ] = ""

    ordered: Annotated[
        str,
        XLSXMetadata(
            display_name="Ordered? Yes or No (default)",
        ),
    ] = ""

    change_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Change Note*",
            meaning="skos:changeNote",
        ),
    ] = ""

    editorial_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Editorial Note",
            meaning="skos:editorialNote",
        ),
    ] = ""

    obsolete_reason: Annotated[
        str,
        XLSXMetadata(
            display_name="Obsoletion reason",
            meaning="owl:deprecated,\nskos:historyNote",
        ),
    ] = ""


# === Mappings (table format) ===


class MappingV1(BaseModel):
    """External mappings row in the Mappings table."""

    concept_iri: Annotated[
        str,
        XLSXMetadata(
            display_name="Concept IRI*",
            meaning="skos:Concept",
        ),
    ] = ""

    related_matches: Annotated[
        str,
        XLSXMetadata(
            display_name="Related Matches",
            meaning="skos:relatedMatch",
        ),
    ] = ""

    close_matches: Annotated[
        str,
        XLSXMetadata(
            display_name="Close Matches",
            meaning="skos:closeMatch",
        ),
    ] = ""

    exact_matches: Annotated[
        str,
        XLSXMetadata(
            display_name="Exact Matches",
            meaning="skos:exactMatch",
        ),
    ] = ""

    narrower_matches: Annotated[
        str,
        XLSXMetadata(
            display_name="Narrower Matches",
            meaning="skos:narrowMatch",
        ),
    ] = ""

    broader_matches: Annotated[
        str,
        XLSXMetadata(
            display_name="Broader Matches",
            meaning="skos:broadMatch",
        ),
    ] = ""

    editorial_note: Annotated[
        str,
        XLSXMetadata(
            display_name="Editorial Note",
            meaning="not in RDF!",
        ),
    ] = ""


# === Prefixes (table format) ===


class PrefixV1(BaseModel):
    """Prefix namespace mapping row in the Prefixes table."""

    prefix: Annotated[
        str,
        XLSXMetadata(
            display_name="Prefix",
        ),
    ] = ""

    namespace: Annotated[
        str,
        XLSXMetadata(
            display_name="Namespace",
        ),
    ] = ""


# === Default prefix data ===

DEFAULT_PREFIXES = [
    PrefixV1(prefix="ex", namespace="https://example.org/"),
    PrefixV1(prefix="skos", namespace="http://www.w3.org/2004/02/skos/core#"),
]


# === Example data for template ===

EXAMPLE_CONCEPT_SCHEME = ConceptSchemeV1(
    vocabulary_iri="https://example.org/vocab/",
    prefix="ex",
    title="Example Vocabulary",
    description="An example vocabulary to demonstrate the template structure.",
    created_date="2025-01-01",
)

EXAMPLE_CONCEPTS = [
    ConceptV1(
        concept_iri="ex:0001001",
        language_code="en",
        preferred_label="Example Concept",
        definition="An example concept to demonstrate the template structure.",
    ),
    ConceptV1(
        concept_iri="ex:0001001",
        language_code="de",
        preferred_label="Beispielkonzept",
        definition="Ein Beispielkonzept zur Demonstration der Vorlagenstruktur.",
    ),
]

EXAMPLE_COLLECTIONS = [
    CollectionV1(
        collection_iri="ex:collection001",
        language_code="en",
        preferred_label="Example Collection",
        definition="An example collection.",
    ),
]

EXAMPLE_MAPPINGS = [
    MappingV1(
        concept_iri="ex:0001001",
        exact_matches="https://example.org/external/concept1",
    ),
]
