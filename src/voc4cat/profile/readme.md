# SHACL profile for voc4cat vocabularies

Note, that the content in this directory has a different license than voc4cat-tool.
It is [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) licensed.

The vocabulary profile 'vp4Cat' is derived from the vocpub profile developed by the
Australian Government Linked Data Working Group, see [AGLDWG/vocpub-profile](https://github.com/AGLDWG/vocpub-profile).

From vp4cat-5.3 on, vp4cat carries its own version number. Up to vp4cat-5.2 the number
matched the vocpub release the profile was based on, which no longer works now that
vp4cat has changes of its own.

## Current: vp4cat-5.3

[SHACL profile](./vp4cat-5.3.ttl), based on vocpub 5.2. `vp4cat` is a version-neutral
copy of the current profile, so `--profile vp4cat` follows this file.

The differences in vp4cat are:

- vocabulary-profile IRI under NFDI4Cat namespace `https://w3id.org/nfdi4cat/vp4cat`
- Modified Requirement-2.4.3b to allow schema:url as alternative to schema:email for Persons
- Modified Requirement-2.3.4 to also accept prov:hadPrimarySource as alternative
- Modified Requirement-2.2.2 to also accept `<IRI>` for dcterms:provenance
- Removed `sh:maxCount` on `skos:prefLabel`, so a concept can be labelled in several
  languages. `sh:uniqueLang` still permits only one label per language, which is the
  rule SKOS states. vocpub keeps `sh:maxCount` in its default validator and offers
  `validators/validator.multilang.ttl` for the multilingual case instead.
- Removed the VocEdit SHACL UI shapes (`Shui-*`, the property groups and the `dash:`
  annotations). They made pySHACL report every prefLabel and definition result twice.
  vocpub keeps them in a separate `validators/shui.ttl`.

## 1.0.x series of voc4cat-tool

These releases use [vp4cat-5.2](./vp4cat-5.2.ttl), which requires exactly one
`skos:prefLabel` per concept. It is still bundled, so vocabularies can pin it.

We include the original vocpub profiles here as reference:

- vocpub-5.2 [specification](./specification-vocpub-5.2.md)
- vocpub-5.2 [SHACL profile](./vocpub-5.2.ttl)

The differences between v5.2 and the previously used v4.7 are small: The IRI changed to linked.data.gov.au, warnings moved from PropertyShapes to NodeShape, and `schema` is used as prefix instead of `sdo`.

## 0.8.x/0.9.x/0.10.x series of voc4cat-tool

These releases of voc4cat-tool used vocpub-4.7, see its [specification](./specification-vocpub-4.7.md) and its [SHACL profile](./vocpub-4.7.ttl)
