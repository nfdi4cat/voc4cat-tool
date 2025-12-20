# SHACL profile for voc4cat vocabularies

Note, that the content in this directory has a different license than voc4cat-tool.
It is [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) licensed.

## 1.0.x series of voc4cat-tool

These releases use the vocabulary profile 'vp4Cat' [SHACL profile](./vp4cat-5.2.ttl) which is almost identical to the vocpub profiles of the same version, which is developed by the Australian Government Linked Data Working Group, see [AGLDWG/vocpub-profile](https://github.com/AGLDWG/vocpub-profile).

The differences in vp4cat are:

- vocabulary-profile IRI under NFDI4Cat namespace `https://w3id.org/nfdi4cat/voc4cat/profile`
- Modified Requirement-2.4.3b to allow schema:url as alternative to schema:email for Persons
- Modified Requirement-2.3.4 to also accept prov:hadPrimarySource as alternative

We include the original vocpub profiles here as reference:

- vocpub-5.2 [specification](./specification-vocpub-5.2.md)
- vocpub-5.2 [SHACL profile](./vocpub-5.2.ttl)

The differences between v5.2 and the previously used v4.7 are small: The IRI changed to linked.data.gov.au, warnings moved from PropertyShapes to NodeShape, and `schema` is used as prefix instead of `sdo`.

## 0.8.x/0.9.x/0.10.x series of voc4cat-tool

These releases of voc4cat-tool used vocpub-4.7, see its [specification](./specification-vocpub-4.7.md) and its [SHACL profile](./vocpub-4.7.ttl)
