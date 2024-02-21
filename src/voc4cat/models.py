import datetime
import logging
import os
from itertools import chain
from typing import List, Union

from curies import Converter
from openpyxl import Workbook
from pydantic import AnyHttpUrl, BaseModel, Field, root_validator, validator
from rdflib import (
    DCAT,
    DCTERMS,
    OWL,
    RDF,
    RDFS,
    SDO,
    SKOS,
    XSD,
    Graph,
    Literal,
    URIRef,
)
from rdflib.namespace import NamespaceManager

from voc4cat import config
from voc4cat.fields import Orcid, Ror

logger = logging.getLogger(__name__)

# If defined here the key can be used in xlsx instead of an URI.
ORGANISATIONS = {
    "NFDI4Cat": URIRef("http://example.org/nfdi4cat/"),
    "LIKAT": URIRef("https://ror.org/029hg0311"),
    # from rdflib.vocexcel (used in old tests)
    "CGI": URIRef("https://linked.data.gov.au/org/cgi-gtwg"),
    "GSQ": URIRef("https://linked.data.gov.au/org/gsq"),
}

ORGANISATIONS_INVERSE = {uref: name for name, uref in ORGANISATIONS.items()}


def reset_curies(curies_map: dict) -> None:
    """
    Reset prefix-map to rdflib's default plus the ones given in curies_map.

    Lit: https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.namespace.html#rdflib.namespace.NamespaceManager
    """
    namespace_manager = NamespaceManager(Graph())
    curies_converter = Converter.from_prefix_map(
        {prefix: str(url) for prefix, url in namespace_manager.namespaces()}
    )
    for prefix, url in curies_map.items():
        if prefix in curies_converter.prefix_map:
            if curies_converter.prefix_map[prefix] != url:
                msg = f'Prefix "{prefix}" is already used for "{curies_converter.prefix_map[prefix]}".'
                raise ValueError(msg)
            continue
        curies_converter.add_prefix(prefix, url)
        namespace_manager.bind(prefix, url)
    # Update voc4at.config
    config.curies_converter = curies_converter
    config.namespace_manager = namespace_manager


# === Pydantic validators used by more than one model ===


def split_curie_list(cls, v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return (p.strip() for p in v.split(","))


def normalise_curie_to_uri(cls, v):
    # Commented out code fails due to a curies issue/behavior for invalid URLs
    # This will fail for e.g. "www.wikipedia.de" (url without protocol)
    # v_as_uri = config.curies_converter.expand(v) or v
    try:
        v = config.curies_converter.standardize_curie(v) or v
        v_as_uri = config.curies_converter.expand(v) or v
    except ValueError:
        # We keep the problematic value and let pydantic validate it.
        v_as_uri = v
    if not v_as_uri.startswith("http"):
        msg = f'"{v}" is not a valid IRI (missing URL scheme).'
        raise ValueError(msg)
    return v_as_uri


def check_uri_vs_config(cls, values):
    """Root validator to check if uri starts with permanent_iri_part.

    Note that it will pass validation if permanent_iri_part is empty.
    """
    voc_conf = config.IDRANGES.vocabs.get(values["vocab_name"], {})
    if not voc_conf:
        return values

    perm_iri_part = getattr(voc_conf, "permanent_iri_part", "")
    iri, *_fragment = values.get("uri", "").split("#", 1)
    if not iri.startswith(perm_iri_part):
        msg = "Invalid IRI %s - It must start with %s"
        raise ValueError(msg % (iri, perm_iri_part))
    id_part_of_iri = iri.split(perm_iri_part)[-1]
    if any(not c.isdigit() for c in id_part_of_iri):
        msg = 'Invalid ID part "%s" in IRI %s. The ID part may only contain digits.'
        raise ValueError(msg % (id_part_of_iri, iri))

    id_pattern = config.ID_PATTERNS.get(values["vocab_name"])
    match = id_pattern.search(iri)
    if not match:
        msg = "ID part of %s is not matching the configured pattern of %s digits."
        raise ValueError(msg % (str(values["uri"]), voc_conf.id_length))

    return values


def check_used_id(cls, values):
    """
    Root validator to check if the ID part of the IRI is allowed for the actor.

    The first entry in provenance is used as relevant actor. For this actor the
    allowed ID range(s) are read from the config.
    """
    voc_conf = config.IDRANGES.vocabs.get(values["vocab_name"], {})
    if not voc_conf:
        return values

    # provenance example value: "0000-0001-2345-6789 Provenance description, ..."
    if values["provenance"] is not None:
        actor = values["provenance"].split(",", 1)[0].split(" ", 1)[0].strip()
    else:
        actor = ""
    iri, *_fragment = str(values.get("uri", "")).split("#", 1)
    id_pattern = config.ID_PATTERNS.get(values["vocab_name"], None)
    if id_pattern is not None:
        match = id_pattern.search(iri)
        if match:
            id_ = int(match["identifier"])
            if actor in config.ID_RANGES_BY_ACTOR:
                actors_ids = config.ID_RANGES_BY_ACTOR[actor]
            else:
                # Because the use of provenance is not well defined and it is not validated
                # a GitHub name may be in incorrect case in the provenance field. (#122)
                # So we look up for lower-cased actor as well:
                actors_ids = config.ID_RANGES_BY_ACTOR[actor.lower()]
            allowed = any(first <= id_ <= last for first, last in actors_ids)
            if not allowed:
                msg = 'ID of IRI %s is not in allowed ID range(s) of actor "%s" (from provenance).'
                raise ValueError(msg % (values["uri"], actor))
    return values


# === Pydantic models ===


class ConceptScheme(BaseModel):
    uri: AnyHttpUrl
    title: str
    description: str
    created: datetime.date
    modified: datetime.date
    creator: Ror | Orcid | str
    publisher: Ror | str
    provenance: str
    version: str = "automatic"
    custodian: str | None = None
    pid: str | None = None
    vocab_name: str = Field("", exclude=True)

    @validator("creator")
    def creator_must_be_from_list(cls, v):
        if isinstance(v, str):
            if v.startswith("http"):
                return v
            if v not in ORGANISATIONS:
                msg = f"Creator must be an ORCID or ROR ID or a string from the organisations list: {', '.join(ORGANISATIONS)}"
                raise ValueError(msg)
        return v

    @validator("modified")
    def set_modified_date_from_env(cls, v):
        if os.getenv("VOC4CAT_MODIFIED") is not None:
            v = datetime.date.fromisoformat(os.getenv("VOC4CAT_MODIFIED", ""))
        return v

    @validator("publisher")
    def publisher_must_be_from_list(cls, v):
        if isinstance(v, str):
            if v.startswith("http"):
                return v
            if v not in ORGANISATIONS:
                msg = f"Publisher must be an ROR ID or a string from the organisations list: {', '.join(ORGANISATIONS)}"
                raise ValueError(msg)
        return v

    @validator("version")
    def version_from_env(cls, v):
        if os.getenv("CI") is not None:  # Don't track version in GitHub.
            v = "automatic"
        version_from_env = os.getenv("VOC4CAT_VERSION")
        if version_from_env is not None:
            if not version_from_env.startswith("v"):
                msg = f'Invalid environment variable VOC4CAT_VERSION "{version_from_env}". Version must start with letter "v".'
                raise ValueError(msg)
            v = version_from_env
        return v

    def to_graph(self):
        g = Graph()

        # <http://example.org/nfdi4cat/> a sdo:Organization ;
        # sdo:name "NFDI4Cat" ;
        # sdo:url "https://nfdi4cat.org"^^xsd:anyURI .
        tg = Graph()
        org = ORGANISATIONS.get(self.publisher, URIRef(self.publisher))
        tg.add((org, RDF.type, SDO.Organization))
        tg.add(
            (
                org,
                SDO.name,
                # should be name but there is no field in the template 0.43
                Literal(
                    ORGANISATIONS.get(self.publisher, self.publisher),
                ),
            )
        )
        tg.add(
            (
                org,
                SDO.url,
                Literal(
                    ORGANISATIONS.get(self.publisher, self.publisher),
                    datatype=URIRef(XSD.anyURI),
                ),
            )
        )
        g += tg

        v = URIRef(self.uri)
        # For dcterms:identifier
        identifier = v.split("#")[-1] if "#" in v else v.split("/")[-1]
        g.add((v, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

        g.add((v, RDF.type, SKOS.ConceptScheme))
        g.add((v, SKOS.prefLabel, Literal(self.title, lang="en")))
        g.add((v, SKOS.definition, Literal(self.description, lang="en")))
        g.add((v, DCTERMS.created, Literal(self.created, datatype=XSD.date)))
        g.add((v, DCTERMS.modified, Literal(self.modified, datatype=XSD.date)))
        g.add(
            (v, DCTERMS.creator, ORGANISATIONS.get(self.creator, URIRef(self.creator)))
        )
        g.add(
            (
                v,
                DCTERMS.publisher,
                ORGANISATIONS.get(self.publisher, URIRef(self.publisher)),
            )
        )
        g.add((v, OWL.versionInfo, Literal(self.version)))
        g.add((v, SKOS.historyNote, Literal(self.provenance, lang="en")))
        if self.custodian is not None:
            g.add((v, DCAT.contactPoint, Literal(self.custodian)))
        if self.pid is not None:
            if self.pid.startswith("http"):
                g.add((v, RDFS.seeAlso, URIRef(self.pid)))
            else:
                g.add((v, RDFS.seeAlso, Literal(self.pid)))

        g.namespace_manager = config.namespace_manager
        return g

    def to_excel(self, wb: Workbook):
        ws = wb["Concept Scheme"]
        ws["B2"] = config.curies_converter.compress(self.uri, passthrough=True)
        ws["B3"] = self.title
        ws["B4"] = self.description
        ws["B5"] = self.created.isoformat()
        ws["B6"] = None if self.modified is None else self.modified.isoformat()
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
    source_vocab: AnyHttpUrl | None = None
    provenance: str | None = None
    related_match: List[AnyHttpUrl] = []
    close_match: List[AnyHttpUrl] = []
    exact_match: List[AnyHttpUrl] = []
    narrow_match: List[AnyHttpUrl] = []
    broad_match: List[AnyHttpUrl] = []
    vocab_name: str = Field("", exclude=True)

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
        "uri",
        "source_vocab",
        *_uri_list_fields,
        each_item=True,
        pre=True,
        allow_reuse=True,
    )(normalise_curie_to_uri)

    _check_uri_vs_config = root_validator(allow_reuse=True)(check_uri_vs_config)
    _check_used_id = root_validator(allow_reuse=True)(check_used_id)

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
        if self.source_vocab is not None:
            g.add((c, RDFS.isDefinedBy, URIRef(self.source_vocab)))
        if self.provenance is not None:
            g.add((c, SKOS.historyNote, Literal(self.provenance, lang="en")))
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
        Export Concept to Excel using one row per language

        Non-labels like Children, Provenance are reported only for the first
        language. If "en" is among the used languages, it is reported first.
        """
        ws = wb["Concepts"]

        # determine the languages with full and partial translation
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
            ws[f"A{row_no_concepts}"] = config.curies_converter.compress(
                self.uri, passthrough=True
            )
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
                [
                    config.curies_converter.compress(uri, passthrough=True)
                    for uri in self.children
                ]
            )
            ws[f"I{row_no_concepts}"] = (
                config.curies_converter.compress(self.source_vocab, passthrough=True)
                if self.source_vocab
                else None
            )
            row_no_concepts += 1

        ws = wb["Additional Concept Features"]

        ws[f"A{row_no_features}"] = config.curies_converter.compress(
            self.uri, passthrough=True
        )
        ws[f"B{row_no_features}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.related_match
            ]
        )
        ws[f"C{row_no_features}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.close_match
            ]
        )
        ws[f"D{row_no_features}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.exact_match
            ]
        )
        ws[f"E{row_no_features}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.narrow_match
            ]
        )
        ws[f"F{row_no_features}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.broad_match
            ]
        )

        return row_no_concepts


class Collection(BaseModel):
    uri: AnyHttpUrl
    pref_label: str
    definition: str
    members: List[AnyHttpUrl]
    provenance: str | None = None
    vocab_name: str = Field("", exclude=True)

    _split_uri_list = validator("members", pre=True, allow_reuse=True)(split_curie_list)
    _normalize_uri = validator(
        "uri", "members", each_item=True, pre=True, allow_reuse=True
    )(normalise_curie_to_uri)

    _check_uri_vs_config = root_validator(allow_reuse=True)(check_uri_vs_config)
    _check_used_id = root_validator(allow_reuse=True)(check_used_id)

    def to_graph(self, cs):
        g = Graph()
        c = URIRef(self.uri)
        g.add((c, RDF.type, SKOS.Collection))

        # rdfs:isDefinedBy <https://example.org> ;
        g.add((c, RDFS.isDefinedBy, cs))
        # skos:inScheme <https://example.org> ;
        g.add((c, SKOS.inScheme, cs))

        # for dcterms:identifier
        identifier = c.split("#")[-1] if "#" in c else c.split("/")[-1]
        g.add((c, DCTERMS.identifier, Literal(identifier, datatype=XSD.token)))

        g.add((c, SKOS.prefLabel, Literal(self.pref_label, lang="en")))
        g.add((c, SKOS.definition, Literal(self.definition, lang="en")))
        for member in self.members:
            g.add((c, SKOS.member, URIRef(member)))
        if self.provenance is not None:
            g.add((c, SKOS.historyNote, Literal(self.provenance, lang="en")))

        return g

    def to_excel(self, wb: Workbook, row_no: int):
        ws = wb["Collections"]
        ws[f"A{row_no}"] = config.curies_converter.compress(self.uri, passthrough=True)
        ws[f"B{row_no}"] = self.pref_label
        ws[f"C{row_no}"] = self.definition
        ws[f"D{row_no}"] = ",\n".join(
            [
                config.curies_converter.compress(uri, passthrough=True)
                for uri in self.members
            ]
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

        # create as Top Concepts those Concepts that have no skos:narrower properties with them as objects
        for s in g.subjects(SKOS.inScheme, cs):
            is_tc = True
            for _ in g.objects(s, SKOS.broader):
                is_tc = False
            if is_tc:
                g.add((cs, SKOS.hasTopConcept, s))
                g.add((s, SKOS.topConceptOf, cs))

        for collection in self.collections:
            g += collection.to_graph(cs)
            g.add((URIRef(collection.uri), DCTERMS.isPartOf, cs))
            g.add((cs, DCTERMS.hasPart, URIRef(collection.uri)))

        return g
