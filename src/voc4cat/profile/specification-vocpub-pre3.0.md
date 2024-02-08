# VocPub Profile - Specification vocpub-pre30

URI
`https://w3id.org/profile/vocpub/spec` - Note, a version-specific URI does not exist.

Title
VocPub Profile - Specification Document

Definition
This document specifies the VocPub Profile. It is to be used to inform
people about the requirements that need to be met by data claiming to
conform to the profile.

Created
2020-06-14

Modified
2021-08-31

Creator
[Nicholas J. Car](https://orcid.org/0000-0002-8742-7730)

Contributor
[Simon J D Cox](https://orcid.org/0000-0002-3884-3420)

Publisher
[SURROUND Australia Pty Ltd](https://linked.data.gov.au/org/surround)

Further metadata
This specification is part of the *VocPub Profile*. See that profile's
main document for License & Rights information and other metadata not
given here.

Profile URI
`https://w3id.org/profile/vocpub` - Note, a version-specific URI does not exist.

License
[CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Abstract

This is the specification document of [SURROUND Australia Pty
Ltd](https://www.ga.gov.au)'s
[profile](https://www.w3.org/TR/dx-prof/#definitions) of
[SKOS](https://www.w3.org/TR/skos-reference/). It defines the
requirements that data must satisfy to be considered conformant with
this profile.

This specification is not to be used for testing conformance of RDF
resources to this profile. That role belongs to the *validation*
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

prof
`http://www.w3.org/ns/dx/prof/`

prov
`http://www.w3.org/ns/prov#`

sdo
`https://schema.org/`

skos
`http://www.w3.org/2004/02/skos/core#`

rdfs
`http://www.w3.org/2000/01/rdf-schema#`

## 1. Introduction

[SURROUND Australia Pty Ltd (SURROUND)](https://www.ga.gov.au) defines a
*vocabulary* as a controlled collection of defined terms that may or may
not contain relationships between terms and relationships to terms in
other vocabularies.

SURROUND uses the Simple Knowledge Organization System Reference
(SKOS)<sup>[ref](#skos)</sup> to represent vocabularies in a form that
can be read by humans and consumed by machines; that is, in *Semantic
Web* form<sup>[ref](#semantic-web)</sup>.

This document specifies a *profile* of SKOS and by profile, the
definition of from the *Profiles Vocabulary*<sup>[ref](#prof)</sup> is
used. A *profile* is:

A specification that constrains, extends, combines, or provides guidance
or explanation about the usage of other specifications.

Here, the *other specification* being profiled is SKOS.

In the next section, this document describes how SKOS's elements must be
presented to make a vocabulary that conforms to this profile.

This specification's rules/requirements - are numbered and <span
style="color:darkred;">indicated in red text</span>.

## 2. Elements & Requirements

### 2.1 Vocabulary

SURROUND identifies Semantic Web objects with URI-based persistent
identifiers. For this reason:

2.1.1 Each vocabulary *MUST* be identified by a URI

As per the *SKOS Primer*<sup>[ref](#skos-primer)</sup>, a document
guiding the use of SKOS:

concepts usually come in carefully compiled vocabularies, such as
thesauri or classification schemes. SKOS offers the means of
representing such KOSs using the `skos:ConceptScheme` class.

For this reason, this profile requires that:

2.1.2 Each vocabulary *MUST* be presented as a single
`skos:ConceptScheme` object

For ease of data management:

2.1.3 Each vocabulary *MUST* be presented in a single file which does
not contain information other than that which is directly part of the
vocabulary and the file is considered the point-of-truth

To ensure vocabularies can be catalogued effectively and governed:

2.1.4a Each vocabulary *MUST* have one and only one title indicated
using the `skos:prefLabel` property that must be a text literal value

2.1.4b Each vocabulary *MUST* have one and only one definition value
indicated using the `skos:definition` property that must be a text
literal values

2.1.5 Each vocabulary *MUST* have one and only one created date and one
and only one modified date indicated using the `dcterms:created` and
`dcterms:modified` properties respectively that must be either an
xsd:date, xsd:dateTime or xsd:dateTimeStamp literal value

2.1.6a Each vocabulary *MUST* have at least one creator, indicated using
`dcterms:creator` property that must be a URI value indicating an
instances of `sdo:Person`, `sdo:Organization` or
`sdo:GovernmentOrganization`

2.1.6b Each vocabulary *MUST* have at least one publisher, indicated
using `dcterms:publisher` property that must be a URI value indicating
an instance of `sdo:Person`, `sdo:Organization` or
`sdo:GovernmentOrganization`

To be able to link SKOS vocabularies to their non-vocabulary source
information:

2.1.7 Provenance for a `skos:ConceptScheme` *MUST* be indicated by at
least one of the following properties: `dcterms:provenance`,
`dcterms:source` or `prov:wasDerivedFrom`.

If a vocabulary is based on another Semantic Web resource, such as an
ontology or another vocabulary, `prov:wasDerivedFrom` should be used to
indicate that resource's URI. If the vocabulary is based on a resource
that is identified by a URI but which is not a Semantic Web resource,
`dcterms:source` should be used to indicate the resource's URI. If the
vocabulary is based on something which cannot be identified by URI, a
statement about the thing should be given in a literal value indicated
with the `dcterms:provenance` property. If the vocabulary is not based
on any other resource or source of information, i.e. this vocabulary is
its only expression, this should be communicated by use of the
`dcterms:provenance` indicating the phrase "This vocabulary is expressed
for the first time here".

To ensure that all the terms within a vocabulary are linked to the main
vocabulary object, the `skos:ConceptScheme`:

2.1.8 All `skos:Concept` instances within a `skos:ConceptScheme` *MUST*
link be ordered in a single, term hierarchy using `skos:broader` and/or
`skos:narrower` properties and which contains no cycles.

To unambiguously link the term hierarchy within a vocabulary to the
vocabulary itself:

2.1.9 Each vocabulary's `skos:ConceptScheme` *MUST* link to at least one
`skos:Concept` within the vocabulary as with the property
`skos:hasTopConcept`

### 2.2 Collection

From the SKOS Primer<sup>[ref](#skos-primer)</sup>:

SKOS makes it possible to define meaningful groupings or "collections"
of concepts

To ensure that `skos:Collection` instances are identifiable and their
meaning isn't obscure or lost:

2.2.1a Each `skos:Collection` instance *MUST* have one and only one
title indicated using the `skos:prefLabel` property that must be a text
literal value

2.2.1b Each `skos:Collection` instance *MUST* have one and only one
definition indicated using the `skos:definition` property that must be a
text literal value

If a `skos:Collection` is derived from an existing resource:

2.2.2 Provenance for a `skos:Collection` *SHOULD* be indicated by at
least one of the following properties: `dcterms:provenance`,
`dcterms:source` or `prov:wasDerivedFrom`.

### 2.3 Concept

From the SKOS Primer<sup>[ref](#skos-primer)</sup>:

The fundamental element of the SKOS vocabulary is the concept. Concepts
are the units of thought — ideas, meanings, or (categories of) objects
and events—which underlie many knowledge organization systems

Vocabularies conforming to this profile must present at least one
`sckos:Concept` within the vocabulary file and, as per requirements in
Section 2.1, at least once `skos:Concept` must be indicated as the top
concept of the vocabulary.

To ensure that `skos:Concept` instances are identifiable and their
meaning isn't obscure or lost:

2.3.1a Each `skos:Concept` instance *MUST* have one and only one title
indicated using the `skos:prefLabel` property that must be a text
literal value

2.3.1b Each `skos:Concept` instance *MUST* have one and only one
definition indicated using the `skos:definition` property that must be a
text literal value

To ensure that every `skos:Concept` is linked to the vocabulary that
defines it:

2.3.2 Each `skos:Concept` in a vocabulary *MAY* indicate the vocabulary
that defines it by use of the `rdfs:isDefinedBy` property indicating a
`skos:ConceptScheme` instance

Note that the vocabulary that defines a `skos:Concept` does not have to
be the vocabulary in the file being validated. This is to allow for
`skos:Concept` instance reuse across multiple vocabularies.

Since a `skos:Concept` may be used in more than one vocabulary:

2.3.3 Each `skos:Concept` in a vocabulary *MUST* indicate that it
appears within that vocabulary's hierarchy of terms by use of either or
both `skos:inScheme` and `skos:topConceptOf` properties

If a `skos:Concept` is derived from an existing resource and that
derivation is not already covered by source information for the
vocabulary that it is within:

2.3.4 Provenance for a `skos:Concept`, if different from that of its
containing `skos:ConceptScheme`, *SHOULD* be indicated by at least one
of the following properties: `dcterms:provenance`, `dcterms:source` or
`prov:wasDerivedFrom`.

2.3.5 Each `skos:Concept` in a vocabulary *SHOULD* indicate its
permanent identifier as the value of a `dcterms:identifier` property. If
the permanent identifier is a URI, the value may have the datatype
`^^xsd:anyURI`

### 2.4 Agent

To be consistent with other Semantic Web representations of agents,
vocabularies' associated agents, creator & publisher must be certain
typed RDF values:

2.4.1 Each agent associated with a vocabulary *MUST* be typed as an
`sdo:Person`, `sdo:Organization` or `sdo:GovernmentOrganization`

To ensure human readability and association of agents with their
non-Semantic Web (real world) form:

2.4.2 Each agent *MUST* indicate at least one name property with the
`sdo:name` property that must be a text literal value

To ensure that agents are linked to non-Semantic Web forms of
identification:

2.4.3a Each agent *MUST* indicate either a `sdo:url` (for organizations)
or a `sdo:email` (for people) property with a URL or email value

2.4.3b Each agent *MUST* indicate either a `sdo:url` (for organizations)
or a `sdo:email` (for people) property with a URL or email value

## 3. References

<span id="prof"></span>PROV
Rob Atkinson; Nicholas J. Car (eds.). *The Profiles Vocabulary*. 18
December 2019. W3C Working Group Note. URL:
<https://www.w3.org/TR/dx-prof/>

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
