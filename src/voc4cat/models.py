import datetime
from itertools import chain
from typing import List, Union

from curies import Converter
from openpyxl import Workbook
from pydantic import AnyHttpUrl, BaseModel, validator
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCAT, DCTERMS, OWL, RDF, RDFS, SKOS, XSD, NamespaceManager

ORGANISATIONS = {
    "CGI": URIRef("https://linked.data.gov.au/org/cgi"),
    "GA": URIRef("https://linked.data.gov.au/org/ga"),
    "GGIC": URIRef("https://linked.data.gov.au/org/ggic"),
    "GSQ": URIRef("https://linked.data.gov.au/org/gsq"),
    "ICSM": URIRef("https://linked.data.gov.au/org/icsm"),
    "DES": URIRef("https://linked.data.gov.au/org/des"),
    "BITRE": URIRef("https://linked.data.gov.au/org/bitre"),
    "CASA": URIRef("https://linked.data.gov.au/org/casa"),
    "ATSB": URIRef("https://linked.data.gov.au/org/atsb"),
}

ORGANISATIONS_INVERSE = {uref: name for name, uref in ORGANISATIONS.items()}

namespace_manager = NamespaceManager(Graph())
# Initialize curies-converter with default namespace of rdflib.Graph
curies_converter = Converter.from_prefix_map(
    {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
)


def reset_curies(curies_map={}):
    global namespace_manager  # noqa: PLW0603
    global curies_converter  # noqa: PLW0603

    namespace_manager = NamespaceManager(Graph())
    # Initialize curies-converter with default namespace of rdflib.Graph
    curies_converter = Converter.from_prefix_map(
        {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
    )
    for prefix, url in curies_map.items():
        curies_converter.add_prefix(prefix, url)  # , prefix_synonyms=[...])
        namespace_manager.bind(prefix, url)


# === "External" validators used by more than one pydantic model ===


def split_curie_list(cls, v):
    if v is None:
        return []
    if type(v) is list:
        return v
    return (p.strip() for p in v.split(","))


def normalise_curie_to_uri(cls, v):
    v = curies_converter.standardize_curie(v) or v
    v_as_uri = curies_converter.expand(v) or v
    if not v_as_uri.startswith("http"):
        msg = f'"{v}" is not a valid URI or CURIE.'
        raise ValueError(msg)
    return v_as_uri


# === Pydantic models ===


class ConceptScheme(BaseModel):
    uri: AnyHttpUrl
    title: str
    description: str
    created: datetime.date
    modified: datetime.date = None
    creator: str
    publisher: str
    provenance: str
    version: str = None
    custodian: str = None
    pid: str = None

    @validator("creator")
    def creator_must_be_from_list(cls, v):
        if v not in ORGANISATIONS.keys():
            msg = f"Organisations must be selected from the Organisations list: {', '.join(ORGANISATIONS)}"
            raise ValueError(msg)
        return v

    @validator("publisher")
    def publisher_must_be_from_list(cls, v):
        if v not in ORGANISATIONS.keys():
            msg = f"Organisations must be selected from the Organisations list: {', '.join(ORGANISATIONS)}"
            raise ValueError(msg)
        return v

    def to_graph(self):
        g = Graph()
        v = URIRef(self.uri)
        # For dcterms:identifier
        identifier = v.split("#")[-1] if "#" in v else v.split("/")[-1]
        g.add((v, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

        g.add((v, RDF.type, SKOS.ConceptScheme))
        g.add((v, SKOS.prefLabel, Literal(self.title, lang="en")))
        g.add((v, SKOS.definition, Literal(self.description, lang="en")))
        g.add((v, DCTERMS.created, Literal(self.created, datatype=XSD.date)))
        if self.modified is not None:
            g.add((v, DCTERMS.modified, Literal(self.created, datatype=XSD.date)))
        else:
            g.add(
                (
                    v,
                    DCTERMS.modified,
                    Literal(
                        datetime.datetime.now().strftime("%Y-%m-%d"), datatype=XSD.date
                    ),
                )
            )
        g.add((v, DCTERMS.creator, ORGANISATIONS[self.creator]))
        g.add((v, DCTERMS.publisher, ORGANISATIONS[self.publisher]))
        if self.version is not None:
            g.add((v, OWL.versionInfo, Literal(self.version)))
        g.add((v, DCTERMS.provenance, Literal(self.provenance, lang="en")))
        if self.custodian is not None:
            g.add((v, DCAT.contactPoint, Literal(self.custodian)))
        if self.pid is not None:
            if self.pid.startswith("http"):
                g.add((v, RDFS.seeAlso, URIRef(self.pid)))
            else:
                g.add((v, RDFS.seeAlso, Literal(self.pid)))

        # By default the standard prefixes are defined including SKOS, DCAT etc.
        # https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.namespace.html#rdflib.namespace.NamespaceManager

        namespace_manager.bind("cs", v)
        namespace_manager.bind(  # what is this bind good for?
            "",
            str(v).split("#")[0] if "#" in str(v) else "/".join(str(v).split("/")[:-1]),
        )
        g.namespace_manager = namespace_manager

        return g

    def to_excel(self, wb: Workbook):
        ws = wb["Concept Scheme"]
        ws["B2"] = curies_converter.compress(self.uri) or self.uri
        ws["B3"] = self.title
        ws["B4"] = self.description
        ws["B5"] = self.created.isoformat()
        ws["B6"] = self.modified.isoformat()
        ws["B7"] = self.creator
        ws["B8"] = self.publisher
        ws["B9"] = self.version
        ws["B10"] = self.provenance
        ws["B11"] = self.custodian
        ws["B12"] = self.pid


class Concept(BaseModel):
    uri: AnyHttpUrl
    pref_label: Union[str, List[str]]
    alt_labels: List[str] = []
    pl_language_code: List[str] = []
    definition: Union[str, List[str]]
    def_language_code: List[str] = []
    children: List[AnyHttpUrl] = []
    home_vocab_uri: AnyHttpUrl | None = None
    provenance: str = None
    related_match: List[AnyHttpUrl] = []
    close_match: List[AnyHttpUrl] = []
    exact_match: List[AnyHttpUrl] = []
    narrow_match: List[AnyHttpUrl] = []
    broad_match: List[AnyHttpUrl] = []

    # We validate with a reusable (external) validators. With a pre-validator,
    # which is applied before all others, we split and to convert from CURIE to URI.
    _uri_list_fields = [
        "children",
        "related_match",
        "close_match",
        "exact_match",
        "narrow_match",
        "broad_match",
    ]
    _split_uri_list = validator(*_uri_list_fields, pre=True, allow_reuse=True)(
        split_curie_list
    )
    _normalize_uri = validator(
        "uri", *_uri_list_fields, each_item=True, pre=True, allow_reuse=True
    )(normalise_curie_to_uri)

    def to_graph(self):
        g = Graph()
        c = URIRef(self.uri)

        g.add((c, RDF.type, SKOS.Concept))
        # For dcterms:identifier
        identifier = c.split("#")[-1] if "#" in c else c.split("/")[-1]
        g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

        if not self.pl_language_code:
            g.add((c, SKOS.prefLabel, Literal(self.pref_label, lang="en")))
        else:
            for lang_code in self.pl_language_code:
                g.add((c, SKOS.prefLabel, Literal(self.pref_label, lang=lang_code)))
        if self.alt_labels is not None:
            for alt_label in self.alt_labels:
                g.add((c, SKOS.altLabel, Literal(alt_label, lang="en")))
        if not self.def_language_code:
            g.add((c, SKOS.definition, Literal(self.definition, lang="en")))
        else:
            for lang_code in self.def_language_code:
                g.add((c, SKOS.definition, Literal(self.definition, lang=lang_code)))
        for child in self.children:
            g.add((c, SKOS.narrower, URIRef(child)))
            g.add((URIRef(child), SKOS.broader, c))
        if self.home_vocab_uri is not None:
            g.add((c, RDFS.isDefinedBy, URIRef(self.home_vocab_uri)))
        if self.provenance is not None:
            g.add((c, DCTERMS.provenance, Literal(self.provenance, lang="en")))
        if self.related_match is not None:
            for related_match in self.related_match:
                g.add((c, SKOS.relatedMatch, URIRef(related_match)))
        if self.close_match:
            for close_match in self.close_match:
                g.add((c, SKOS.closeMatch, URIRef(close_match)))
        if self.exact_match is not None:
            for exact_match in self.exact_match:
                g.add((c, SKOS.exactMatch, URIRef(exact_match)))
        if self.narrow_match is not None:
            for narrow_match in self.narrow_match:
                g.add((c, SKOS.narrowMatch, URIRef(narrow_match)))
        if self.broad_match is not None:
            for broad_match in self.broad_match:
                g.add((c, SKOS.broadMatch, URIRef(broad_match)))

        return g

    def to_excel(self, wb: Workbook, row_no_features: int, row_no_concepts: int):
        """ "
        Export Concept to Excel using on row per language

        Non-labels like Children, Provenance are reported only for the first
        language. If "en" is among the used languages, it is reported first.
        """
        ws = wb["Concepts"]

        # determine the languages with full and patial translation
        pref_labels = {
            lang: pl for pl, lang in zip(self.pref_label, self.pl_language_code)
        }
        definitions = {
            lang: d for d, lang in zip(self.definition, self.def_language_code)
        }
        fully_translated = [lbl for lbl in pref_labels if lbl in definitions]
        partially_translated = [
            lbl
            for lbl in chain(pref_labels.keys(), definitions.keys())
            if lbl not in fully_translated
        ]

        # put "en" first if available
        if "en" in fully_translated:
            fully_translated.remove("en")
            fully_translated.insert(0, "en")

        first_row_exported = False
        for lang in chain(fully_translated, partially_translated):
            ws[f"A{row_no_concepts}"] = curies_converter.compress(self.uri) or self.uri
            ws[f"B{row_no_concepts}"] = pref_labels.get(lang, "")
            ws[f"C{row_no_concepts}"] = lang
            ws[f"D{row_no_concepts}"] = definitions.get(lang, "")
            ws[f"E{row_no_concepts}"] = lang
            ws[f"H{row_no_concepts}"] = self.provenance

            if first_row_exported:
                row_no_concepts += 1
                continue

            first_row_exported = True
            ws[f"F{row_no_concepts}"] = ",\n".join(self.alt_labels)
            ws[f"G{row_no_concepts}"] = ",\n".join(
                [(curies_converter.compress(uri) or uri) for uri in self.children]
            )
            ws[f"I{row_no_concepts}"] = (
                (curies_converter.compress(self.home_vocab_uri) or self.home_vocab_uri)
                if self.home_vocab_uri
                else None
            )
            row_no_concepts += 1

        ws = wb["Additional Concept Features"]

        ws[f"A{row_no_features}"] = curies_converter.compress(self.uri) or self.uri
        ws[f"B{row_no_features}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.related_match]
        )
        ws[f"C{row_no_features}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.close_match]
        )
        ws[f"D{row_no_features}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.exact_match]
        )
        ws[f"E{row_no_features}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.narrow_match]
        )
        ws[f"F{row_no_features}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.broad_match]
        )

        return row_no_concepts


class Collection(BaseModel):
    uri: AnyHttpUrl
    pref_label: str
    definition: str
    members: List[AnyHttpUrl]
    provenance: str = None

    _split_uri_list = validator("members", pre=True, allow_reuse=True)(split_curie_list)
    _normalize_uri = validator(
        "uri", "members", each_item=True, pre=True, allow_reuse=True
    )(normalise_curie_to_uri)

    def to_graph(self):
        g = Graph()
        c = URIRef(self.uri)
        g.add((c, RDF.type, SKOS.Collection))
        # for dcterms:identifier
        identifier = c.split("#")[-1] if "#" in c else c.split("/")[-1]
        g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

        g.add((c, SKOS.prefLabel, Literal(self.pref_label, lang="en")))
        g.add((c, SKOS.definition, Literal(self.definition, lang="en")))
        for member in self.members:
            g.add((c, SKOS.member, URIRef(member)))
        if self.provenance is not None:
            g.add((c, DCTERMS.provenance, Literal(self.provenance, lang="en")))

        return g

    def to_excel(self, wb: Workbook, row_no: int):
        ws = wb["Collections"]
        ws[f"A{row_no}"] = curies_converter.compress(self.uri) or self.uri
        ws[f"B{row_no}"] = self.pref_label
        ws[f"C{row_no}"] = self.definition
        ws[f"D{row_no}"] = ",\n".join(
            [(curies_converter.compress(uri) or uri) for uri in self.members]
        )
        ws[f"E{row_no}"] = self.provenance


class Vocabulary(BaseModel):
    concept_scheme: ConceptScheme
    concepts: List[Concept]
    collections: List[Collection]

    def to_graph(self):
        g = self.concept_scheme.to_graph()
        cs = URIRef(self.concept_scheme.uri)
        for concept in self.concepts:
            g += concept.to_graph()
            g.add((URIRef(concept.uri), SKOS.inScheme, cs))
        for collection in self.collections:
            g += collection.to_graph()
            g.add((URIRef(collection.uri), DCTERMS.isPartOf, cs))
            g.add((cs, DCTERMS.hasPart, URIRef(collection.uri)))

        # create as Top Concepts those Concepts that have no skos:narrower properties with them as objects
        for s in g.subjects(SKOS.inScheme, cs):
            is_tc = True
            for _ in g.objects(s, SKOS.broader):
                is_tc = False
            if is_tc:
                g.add((cs, SKOS.hasTopConcept, s))
                g.add((s, SKOS.topConceptOf, cs))

        return g
