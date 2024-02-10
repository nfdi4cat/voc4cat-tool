# VocPub Profile - Specification

URI
[`https://w3id.org/profile/vocpub/spec`](https://w3id.org/profile/vocpub/spec)

Title
VocPub Profile - Specification Document

Definition
This document specifies the VocPub Profile. It is to be used to inform
people about the requirements that need to be met by data claiming to
conform to the profile.

Created
2020-06-14

Modified
2023-11-15

Version IRI
<https://w3id.org/profile/vocpub/spec/4.6>

Version Information
4.6 Fixed sdo:historyNote-&gt;skos:historyNote bug

4.5 Added suggested predicates of license & copyrightHolder

4.4 Fixed versions across multiple Resources

4.3 Improved validator error messages by using more named Property
Shapes

4.2: Included CONSTRUCT-based pre-validation inference in validator.
First Git tagged version

4.1: Added Requirements 2.1.10, 2.1.11 & 2.1.12 and example RDF

4.0: Added a SPARQL function to allow for the inferenceing of
`skos:inScheme` predicates, `skos:broader` / `skos:narrower` and
`skos:topConceptOf`/`skos:hasTopConcept` pairs of inverse predicates

3.3: Converted validator metadata to schema.org, enabled bibliographic
references for Concepts, enabled DCTERMS or schema.org for many
ConceptScheme predicates; simplified 2.1.6 from two Requirements to one;
included `skos:topConceptOf` in 2.1.8 for Concepts at the top of the
hierarchy; collapsed title & definition requirement pairs to single
requirements

3.2: Allowed `dcterms:provenance` and `skos:historyNote`; removed max
restriction on `dcterms:source` & `prov:wasDerivedFrom`

3.1: Changed `dcterms:provenance` to `skos:historyNote`

3.0: Removed Requirement-2.3.5 (identifiers) as these are auto-generated
in systems like VocPrez; Added Requirement-2.1.10 & 2.1.11 and sub parts
to test for qualifiedDerivation and status of a `ConceptScheme`

Creator
[Nicholas J. Car](https://orcid.org/0000-0002-8742-7730)

Publisher
[Australian Government Linked Data Working
Group](https://linked.data.gov.au/org/agldwg)

Further metadata
This specification is part of the *VocPub Profile*. See that profile's
main document for License & Rights information and other metadata not
given here.

Profile URI
[`https://w3id.org/profile/vocpub`](https://w3id.org/profile/vocpub)

License
[CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Abstract

This is the specification document of the VocPub
[profile](https://www.w3.org/TR/dx-prof/#definitions) of
[SKOS](https://www.w3.org/TR/skos-reference/). It defines the
requirements that data must satisfy to be considered conformant with
this profile.

This specification document cannot be used for testing conformance of
RDF resources to this profile: that role belongs to the *validation*
resource within this profile:

-   <https://w3id.org/profile/vocpub/validation>

For the list of all resources within this profile, see the profile
definition:

-   <https://w3id.org/profile/vocpub>

## Namespaces

This document refers to elements of various ontologies by short codes
using namespace prefixes. The prefixes and their corresponding
namespaces' URIs are:

dcterms
`http://purl.org/dc/terms/`

isorole
`http://def.isotc211.org/iso19115/-1/2018/CitationAndResponsiblePartyInformation/code/CI_RoleCode/`

prof
`http://www.w3.org/ns/dx/prof/`

prov
`http://www.w3.org/ns/prov#`

reg
`http://purl.org/linked-data/registry#>`

sdo
`https://schema.org/`

skos
`http://www.w3.org/2004/02/skos/core#`

rdfs
`http://www.w3.org/2000/01/rdf-schema#`

## 1. Introduction

Many organisations use the Simple Knowledge Organization System
Reference (SKOS)<sup>[ref](#skos)</sup> to represent vocabularies in a
form that can be read by humans and consumed by machines; that is, in
*Semantic Web* form<sup>[ref](#semantic-web)</sup>.

This profile defines a *vocabulary* as a controlled collection of
defined terms - Concepts - that may or may not contain relationships
between Cocnepts and relationships to Concepts in other vocabularies.

This document specifies a *profile* of SKOS and for profile, the
definition of from the *Profiles Vocabulary*<sup>[ref](#prof)</sup> is
used. A *profile* is:

A specification that constrains, extends, combines, or provides guidance
or explanation about the usage of other specifications.

Here, the *other specification* being profiled is SKOS.

In the next section, this document describes how SKOS's elements must be
presented - in certain arrangements with respect to one another and with
certain predicates to indicate properties - to make a vocabulary that
conforms to this profile.

This specification's rules/requirements - are numbered and <span
style="color:darkred;">indicated in red text</span>.

### 1.1 Data Expansion

Some SKOS elements - classes and predicates - can be inferred based on
rules present in the SKOS model. For example, `skos:broader` and
`skos:narrower` are inverse predicates thus if I have
`<A> skos:broader <B>`, I can infer `<B> skos:narrower <A>`.

This profile allows data to be supplied in a minimalist form that is not
conformant to this specification until a series of calculations, based
on certain SKOS rules, are carried out on it through a process known as
data *expansion*.

The particular rules that may be applied to data before validation with
this profile's validator are given in the table below. These rules are
enacted by the application of a series of
SPARQL<sup>[ref](#sparql)</sup> queries to the data, all of which are
packaged up inside a SHACL<sup>[ref](#shacl)</sup> file in this
profile's repository.

<table class="bordered">
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr class="header">
<th>Rule</th>
<th>Description</th>
<th>SPARQL Query</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>hasTopConcept</td>
<td>Calculate <code>skos:hasTopConcept</code> as the inverse to
<code>skos:topConceptOf</code></td>
<td><pre><code>CONSTRUCT {
    $this skos:hasTopConcept ?c .
}
WHERE {
    ?c skos:topConceptOf $this .
}</code></pre></td>
</tr>
<tr class="even">
<td>topConceptOf</td>
<td>Calculate <code>skos:topConceptOf</code> as the inverse to
<code>skos:hasTopConcept</code></td>
<td><pre><code>CONSTRUCT {
    $this skos:topConceptOf ?cs .
}
WHERE {
    ?cs skos:hasTopConcept $this .
}</code></pre></td>
</tr>
<tr class="odd">
<td>broader</td>
<td>Calculate <code>skos:broader</code> as the inverse to
<code>skos:narrower</code></td>
<td><pre><code>CONSTRUCT {
    $this skos:broader ?n .
}
WHERE {
    ?n skos:narrower $this .
}</code></pre></td>
</tr>
<tr class="even">
<td>narrower</td>
<td>Calculate <code>skos:narrower</code> as the inverse to
<code>skos:broader</code></td>
<td><pre><code>CONSTRUCT {
    $this skos:narrower ?b .
}
WHERE {
    ?b skos:broader $this .
}</code></pre></td>
</tr>
<tr class="odd">
<td>inScheme</td>
<td>Calculate <code>skos:inScheme</code> for all Concepts, based on
their linking to a Concept Scheme via
<code>skos:broader/skos:topConceptOf</code> property path</td>
<td><pre><code>CONSTRUCT {
    $this skos:inScheme ?cs .
}
WHERE {
    $this skos:broader*/skos:topConceptOf ?cs .
}</code></pre></td>
</tr>
<tr class="even">
<td>Concept provenance</td>
<td>Infer provenance predicates for a Concept when they don't have their
own but their containing Concept Scheme does</td>
<td><pre><code>CONSTRUCT {
    $this ?p ?o3
}
WHERE {
    $this skos:inScheme ?cs .

    VALUES ?p {
        prov:wasDerivedFrom
        skos:historyNote
        sdo:citation
        dcterms:source
        dcterms:provenance
    }

    ?cs ?p ?o .

    OPTIONAL {
        $this ?p ?o2 .
    }

    BIND (COALESCE(?o2, ?o) AS ?o3)
}</code></pre></td>
</tr>
</tbody>
</table>

Application of these rules will allow a Concept supplied without any
provenance predicates to be calculated from its containing Concept
Scheme, thus satisfying Requirement 2.3.4.

The SHACL file containing all the expansion queries is available at:

-   <https://w3id.org/profile/vocpub/expander>

A Python script able to execute the expansion rule on RDF data before
validation is available at:

-   <https://w3id.org/profile/vocpub/validate>

### 1.2 Dependencies

To characterise vocabularies according to the mandatory and suggested
Requirements of this Profile, several other vocabularies will need to be
used. This profile is therefore dependent on those vocabularies. For
this reason, copies of these vocabularies are maintained within the
repository of this profile and are accessible as per the details table
below.

<table class="bordered">
<thead>
<tr class="header">
<th>Vocabulary</th>
<th>Description</th>
<th>Where used</th>
<th>Local Copy</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><a href="https://data.idnau.org/pid/vocab/idn-role-codes">IDN Role
Codes</a></td>
<td>he Indigenous Data Network's vocabulary of the types of roles Agents
- People and Organisations - play in relation to data</td>
<td>For the predicate <code>prov:hadRole</code>, applied to an
<code>Attribution</code> indicated by a
<code>prov:qualifiedAttribution</code> predicate for a Concept
Scheme</td>
<td><a
href="https://data.idnau.org/pid/vocab/idn-role-codes">https://data.idnau.org/pid/vocab/idn-role-codes</a></td>
</tr>
<tr class="even">
<td><a href="https://linked.data.gov.au/def/reg-statuses">Registry
Statuses</a></td>
<td>The registration statuses of items in a Register, as per
ISO19135</td>
<td>For the suggested vocabulary predicate <code>reg:status</code>, as
per <span style="color:darkred;">Requirement 2.1.11</span></td>
<td><a
href="https://linked.data.gov.au/def/reg-statuses">https://linked.data.gov.au/def/reg-statuses</a></td>
</tr>
<tr class="odd">
<td><a href="https://linked.data.gov.au/def/vocdermods">Vocab Derivation
Modes</a></td>
<td>The modes by which one vocabulary may derive from another</td>
<td>For the suggested vocabulary predicate
<code>prov:qualifiedDerivation</code>, as per <span
style="color:darkred;">Requirement 2.1.12</span></td>
<td><a
href="https://linked.data.gov.au/def/vocdermods">https://linked.data.gov.au/def/vocdermods</a></td>
</tr>
</tbody>
</table>

## 2. Elements & Requirements

### 2.1 Vocabulary

This profile identifies Semantic Web objects with URI-based persistent
identifiers. For this reason:

<a href="#2.1.1" id="2.1.1" class="frag">§</a> 2.1.1 Each vocabulary
*MUST* be identified by a IRI

As per the *SKOS Primer*<sup>[ref](#skos-primer)</sup>, a document
guiding the use of SKOS:

concepts usually come in carefully compiled vocabularies, such as
thesauri or classification schemes. SKOS offers the means of
representing such KOSs using the `skos:ConceptScheme` class.

For this reason, this profile requires that:

<a href="#2.1.2" id="2.1.2" class="frag">§</a> 2.1.2 Each vocabulary
*MUST* be presented as a single Concept Scheme object

For ease of data management:

<a href="#2.1.3" id="2.1.3" class="frag">§</a> 2.1.3 Each vocabulary
*MUST* be presented in a single RDF file which does not contain
information other than that which is directly part of the vocabulary

To ensure vocabularies can be catalogued effectively and governed:

<a href="#2.1.4" id="2.1.4" class="frag">§</a> 2.1.4 Each vocabulary
*MUST* have exactly one title and at least one definition indicated
using the `skos:prefLabel` and the `skos:definition` predicates
respectively that must give textual literal values. Only one definition
per language is allowed

**NOTE**: Unlike the general directions for the use of SKOS (the [SKOS
"Primer"](https://www.w3.org/TR/skos-primer/)) labels in multiple
languages should be indicated with `skos:altLabel` predicates, not all
with `skos:prefLabel`, i.e. there should only ever be one
`skos:prefLabel` value. If multiple definitions are given, the one in
the language of the label is considered primary.

<a href="#2.1.5" id="2.1.5" class="frag">§</a> 2.1.5 Each vocabulary
*MUST* have exactly one created date and exactly one modified date
indicated using the `sdo:dateCreated` and `sdo:dateModified` or
`dcterms:created` and `dcterms:modified` predicates respectively that
must be either an `xsd:date`, `xsd:dateTime` or `xsd:dateTimeStamp`
literal value

<a href="#2.1.6" id="2.1.6" class="frag">§</a> 2.1.6 Each vocabulary
*MUST* have at least one creator, indicated using `sdo:creator` or
`dcterms:creator` predicate and exactly one publisher, indicated using
`sdo:publisher` or `dcterms:publisher`, all of which MUST be IRIs
indicating instances of `sdo:Person`, or `sdo:Organization`. A
`prov:qualifiedAttribution` predicate indicating an Agent with the
`prov:hadRole` predicate indicating the value `isorole:originator` or
`isorole:publisher` may be used instead of `sdo:creator` &
`sdo:publisher`, respectively

To be able to link SKOS vocabularies to their non-vocabulary source
information:

<a href="#2.1.7" id="2.1.7" class="frag">§</a> 2.1.7 The origins of a
Concept Scheme *MUST* be indicated by at least one of the following
predicates: `skos:historyNote`, `sdo:citation`, `prov:wasDerivedFrom`.
`dcterms:source` *MAY* be used instead of `sdo:citation` and
`dcterms:provenance` *MAY* be used instead of `skos:historyNote` but the
schema.org and SKOS predicates are preferred.

If a vocabulary is based on another Semantic Web resource, such as an
ontology or another vocabulary, `prov:wasDerivedFrom` should be used to
indicate that resource's IRI. If the vocabulary is based on a resource
that is identified by a IRI but which is not a Semantic Web resource,
`sdo:citation` should be used to indicate the resource's IRI with the
`xsd:anyURI` datatype. If the vocabulary is based on something which
cannot be identified by IRI, a statement about the vocabulary's origins
should be given in a literal value indicated with the `skos:historyNote`
predicate. If the vocabulary is not based on any other resource or
source of information, i.e. this vocabulary is its only expression, this
should be communicated by use of the `skos:historyNote` indicating the
phrase "This vocabulary is expressed for the first time here".

*The use of `dcterms:source` & `dcterms:provenance` is to maintain
compatibility with previous versions of VocPub only and may eventually
be disallowed.*

To ensure that all the terms within a vocabulary are linked to the main
vocabulary object, the Concept Scheme:

<a href="#2.1.8" id="2.1.8" class="frag">§</a> 2.1.8 All Concept
instances within a Concept Scheme *MUST* be contained in a single term
hierarchy using `skos:hasTopConcept` / `skos:topConceptOf` predicates
indicating the broadest Concepts in the vocabulary and then
`skos:broader` and/or `skos:narrower` predicates for all non-broadest
Concepts in a hierarchy that contains no cycles.

To unambiguously link the term hierarchy within a vocabulary to the
vocabulary itself:

<a href="#2.1.9" id="2.1.9" class="frag">§</a> 2.1.9 Each vocabulary's
Concept Scheme *MUST* link to at least one Concept within the vocabulary
with the `skos:hasTopConcept` predicate

To communicate the *Registry Status* of the vocabulary:

<a href="#2.1.10" id="2.1.10" class="frag">§</a> 2.1.10 The status of
the vocabulary as a whole, according to the Registry Status
standard<sup>[ref](#iso19135)</sup>, *SHOULD* be given with the
predicate `reg:status` indicating a Concept from the *Registry Statuses*
vocabulary (<https://linked.data.gov.au/def/reg-statuses>).

To indicate whether and if so how this vocabulary has been derived from
another vocabulary:

<a href="#2.1.11" id="2.1.11" class="frag">§</a> 2.1.11 The derivation
status of the vocabulary *SHOULD* be given should be given with the
predicate `prov:qualifiedDerivation` indicating a Blank Node that
contains the predicated `prov:entity`, to indicate the vocabulary
derived from and `prov:hadRole` to indicate the mode of derivation which
*SHOULD* be taken from the *Vocabulary Derivation Modes* vocabulary
(<https://linked.data.gov.au/def/vocdermods>).

Example data for a vocabulary indicating that it is an extension to
another vocabulary using the mechanism defined in Requirement 2.1.2 is:

    # Vocab X is derived from Vocab Y and is an extension of it
    <http://example.com/vocab/x>
        a skos:ConceptScheme ;
        skos:prefLabel "Vocab X"@en ;
        ...
        prov:qualifiedDerivation [
            prov:entity <http://example.com/vocab/y> ;  # Vocab Y
            prov:hadRole <https://linked.data.gov.au/def/vocdermods/extension> ;
        ] ;
    .

To high-level theming of a vocabulary:

<a href="#2.1.12" id="2.1.12" class="frag">§</a> 2.1.12 High-level
theming of a vocabulary *SHOULD* be given using the `sdo:keywords`
predicate indicating Concepts from another vocabulary. Alternatively,
`dcat:theme` *MAY* be used. Text literal values for either predicate
*SHOULD NOT* be used.

To indicate license, copyright:

<a href="#2.1.13" id="2.1.13" class="frag">§</a> 2.1.13 Any licence
pertaining to the reuse of a vocabulary's content *SHOULD* be given
using the `sdo:license` predicate preferentially indicating the IRI of a
license if in RDF form or a literal URL (datatype `xsd:anyURI`) if
online but not in RDF form. If the licence is expressed in test, a
literal text field may be indicated.

<a href="#2.1.14" id="2.1.14" class="frag">§</a> 2.1.14 The copyright
holder for the vocabulary *SHOULD* be given using the
`sdo:copyrightHolder` predicate preferentially indicating the IRI of an
Agent or a Blank Node instance of an Agent containing details as per
Agent requirements. A `prov:qualifiedAttribution` predicate indicating
an Agent with the `prov:hadRole` predicate indicating the value
`isorole:rightsHolder` may be used instead of `sdo:copyrightHolder`.

### 2.2 Collection

From the SKOS Primer<sup>[ref](#skos-primer)</sup>:

SKOS makes it possible to define meaningful groupings or "collections"
of concepts. Collections may contain Concepts defined in any vocabulary,
not just the one the Collection itself is defined in.

To ensure that Collection instances are identifiable and their meaning
isn't obscure or lost:

<a href="#2.2.1" id="2.2.1" class="frag">§</a> 2.2.1 Each Collection
*MUST* have exactly one title and at least one definition indicated
using the `skos:prefLabel` and the `skos:definition` predicates
respectively that must give textual literal values. Only one definition
per language is allowed

**NOTE**: Unlike the general directions for the use of SKOS (the [SKOS
"Primer"](https://www.w3.org/TR/skos-primer/)) labels in multiple
languages should be indicated with `skos:altLabel` predicates, not all
with `skos:prefLabel`, i.e. there should only ever be one
`skos:prefLabel` value. If multiple definitions are given, the one in
the language of the label is considered primary.

If a Collection's grouping of Concepts is derived from an existing
resource that is different from the ConceptScheme it is defined within:

<a href="#2.2.2" id="2.2.2" class="frag">§</a> 2.2.2 The origins of a
Collection, if different from its containing Concept Scheme, *SHOULD* be
indicated by at least one of the following predicates:
`skos:historyNote`, `sdo:citation`, `prov:wasDerivedFrom`.
`dcterms:source` *MAY* be used instead of `sdo:citation` and
`dcterms:provenance` *MAY* be used instead of `skos:historyNote` but the
schema.org and SKOS predicates are preferred.

*For compatibility with previous versions of this Specification,
`dcterms:provenance` MAY be used instead of `skos:historyNote` but the
latter is the preferred predicate.*

To help list Collections within vocabularies:

<a href="#2.2.3" id="2.2.3" class="frag">§</a> 2.2.3 A Collection exists
within a vocabulary *SHOULD* indicate that it is within the vocabulary
by use of the `skos:inScheme` predicate. If it is defined for the first
time in the vocabulary, it should also indicate this with the
`rdfs:isDefinedBy` predicate

To ensure that a Collection isn't empty:

<a href="#2.2.4" id="2.2.4" class="frag">§</a> 2.2.4 A Collection *MUST*
indicate at least one Concept instance that is within the collection
with use of the `skos:member` predicate. The Concept need not be defined
by the Concept Scheme that defines the Collection

### 2.3 Concept

From the SKOS Primer<sup>[ref](#skos-primer)</sup>:

The fundamental element of the SKOS vocabulary is the concept. Concepts
are the units of thought — ideas, meanings, or (categories of) objects
and events—which underlie many knowledge organization systems

Vocabularies conforming to this profile must present at least one
Concept within the vocabulary file and, as per requirements in Section
2.1, at least once Concept must be indicated as the top concept of the
vocabulary.

To ensure that Concept instances are identifiable and their meaning
isn't obscure or lost:

<a href="#2.3.1" id="2.3.1" class="frag">§</a> 2.3.1 Each Concept *MUST*
have exactly one title and at least one definition indicated using the
`skos:prefLabel` and the `skos:definition` predicates respectively that
must give textual literal values. Only one definition per language is
allowed

**NOTE**: Unlike the general directions for the use of SKOS (the [SKOS
"Primer"](https://www.w3.org/TR/skos-primer/)) labels in multiple
languages should be indicated with `skos:altLabel` predicates, not all
with `skos:prefLabel`, i.e. there should only ever be one
`skos:prefLabel` value. If multiple definitions are given, the one in
the language of the label is considered primary.

To ensure that every Concept is linked to the vocabulary that defines
it:

<a href="#2.3.2" id="2.3.2" class="frag">§</a> 2.3.2 Each Concept in a
vocabulary *MAY* indicate the vocabulary that defines it by use of the
`rdfs:isDefinedBy` predicate indicating a Concept Scheme instance. If no
such predicate is given, the Concept Scheme in the file that a Concept
is provided in is understood to be the defining Concept Scheme

Note that the vocabulary that defines a Concept does not have to be the
vocabulary in the file being validated. This is to allow for Concept
instance reuse across multiple vocabularies.

Since a Concept may be used in more than one vocabulary:

<a href="#2.3.3" id="2.3.3" class="frag">§</a> 2.3.3 Each Concept in a
vocabulary *MUST* indicate that it appears within that vocabulary's
hierarchy of Concepts either directly by use of the `skos:topConceptOf`
predicate indicating the vocabulary or indirectly by use of one or more
`skos:broader` / `skos:narrower` predicates placing the Concept within a
chain of other Concepts, the top concept of which uses the
`skos:topConceptOf` predicate to indicate the vocabulary.

If a Concept is derived from an existing resource and that derivation is
not already covered by source information for the vocabulary that it is
within:

<a href="#2.3.4" id="2.3.4" class="frag">§</a> 2.3.4 The origins of a
Concept, if different from its containing Concept Scheme, *SHOULD* be
indicated by at least one of the following predicates:
`skos:historyNote`, `sdo:citation`, `dcterms:source` or
`prov:wasDerivedFrom` or `dcterms:provenance`.

If a Concept is based on another Semantic Web resource, such as another
Concept or other defined object, `prov:wasDerivedFrom` should be used to
indicate that resource's IRI. If the Concept is based on a resource that
is identified by a IRI but which is not a Semantic Web resource,
`dcterms:source` should be used to indicate the resource's IRI. If the
vocabulary is based on something which cannot be identified by IRI, a
statement about the vocabulary's origins should be given in a literal
value indicated with the `skos:historyNote` predicate. If the vocabulary
is not based on any other resource or source of information, i.e. this
vocabulary is its only expression, this should be communicated by use of
the `skos:historyNote` indicating the phrase "This vocabulary is
expressed for the first time here".

### 2.4 Agent

To be consistent with other Semantic Web representations of Agents,
vocabularies' associated Agents, creator & publisher must be certain
typed RDF values:

<a href="#2.4.1" id="2.4.1" class="frag">§</a> 2.4.1 Each Agent
associated with a vocabulary *MUST* be typed as an `sdo:Person` or
`sdo:Organization`

To ensure human readability and association of Agents with their
non-Semantic Web (real world) form:

<a href="#2.4.2" id="2.4.2" class="frag">§</a> 2.4.2 Each Agent *MUST*
give exactly one name with the `sdo:name` predicate indicating a literal
text value

To ensure that Agents are linked to non-Semantic Web forms of
identification:

<a href="#2.4.3" id="2.4.3" class="frag">§</a> 2.4.3 Each Agent *MUST*
indicate either a `sdo:url` (for organizations) or a `sdo:email` (for
people) predicate with a URL or email value

To link to Agent registers using non-Semantic Web identifiers for
Agents:

<a href="#2.4.4" id="2.4.4" class="frag">§</a> 2.4.4 Each Agent *SHOULD*
indicate any non-Semantic Web identifiers for Agents with the
`sdo:identifier` predicate with literal identifier values,
preferentially with custom data types that define the form of the
identifier.

**NOTE**: This method of providing identifiers with specialised
datatypes is the same as that specified for `skos:notation` values in
the [SKOS Primer](https://www.w3.org/TR/skos-primer/#secnotations).

## 3. References

<span id="prof"></span>PROF
Rob Atkinson; Nicholas J. Car (eds.). *The Profiles Vocabulary*. 18
December 2019. W3C Working Group Note. URL:
<https://www.w3.org/TR/dx-prof/>

<span id="iso19135"></span>ISO 19135-1:2015
International Organization for Standardization *ISO 19135-1:2015 -
Geographic information - Procedures for item registration - Part 1:
Fundamentals*. 2015. ISO Standard. URL:
<https://www.iso.org/standard/54721.html>

<span id="owl"></span>OWL
W3C OWL Working Group (eds.). *OWL 2 Web Ontology Language Document
Overview (Second Edition)*. 11 December 2012. W3C Recommendation. URL:
<https://www.w3.org/TR/owl2-overview/>

<span id="shacl"></span>SHACL
World Wide Web Consortium. *Shapes Constraint Language (SHACL)* 20
July 2017. W3C Recommendation. URL: <https://www.w3.org/TR/shacl/>

<span id="skos"></span>SKOS
Alistair Miles; Sean Bechhofer (eds.). *SKOS Simple Knowledge
Organization System Reference*. 18 August 2009. W3C Recommendation. URL:
<https://www.w3.org/TR/skos-reference/>

<span id="skos-primer"></span>SKOS Primer
Antoine Isaac; Ed Summers (eds.). *SKOS Simple Knowledge Organization
System Primer*. 18 August 2009. W3C Note. URL:
<https://www.w3.org/TR/skos-primer/>

<span id="semantic-web"></span>Semantic Web
World Wide Web Consortium. *Semantic Web* 2015. Web Page. URL:
<https://www.w3.org/standards/semanticweb/>, accessed 2020-06-14

<span id="sparql"></span>SPARQL
World Wide Web Consortium. *SPARQL 1.2 Query Language* 29
September 2023. W3C Working Draft. URL:
<https://www.w3.org/TR/sparql12-query/>
