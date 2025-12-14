# Tasks tbd for version 1.0.0

https://github.com/nfdi4cat/voc4cat-tool/issues/124

Ideas are marked as done here if they have been implemented in dev-1.0.0 branch (and therefore become part of v1.0.0).

## Implementation plan

- [done] Step 1: Create python code that generates the structure of `src/voc4cat/templates/vocab/blank_1.0_min.xlsx` (but not the enum sheet)
- [done] Step 2a: Adapt converter to output v043 rdf data of current rdf-schema into the new template reusing `src/voc4cat/models.py`
- [done] Step 2b: Adapt converter for roundtripping with v043 rdf and xlsx v1.0
- [done] Step 3: Add support for new columns in template v1.0 to read their data and output as RDF. The two way conversion RDF <-> XLXS must be lossless. In order to convert existing RDF data created with template 043 we need to be able to read in these RDF data and convert them into V1.0 RDF. We only need a one-way conversion 043-to-v1.0.
- [done] Step 4: Improve deprecation handling
  - Enum (string) in skos:historyNote - if present and filled with reason from enum, add "OBSOLETE " at the start of the  prefLabel of the concept (only for default language "en") if the prefLabel does not yet start likewise.
  - Add dct:replacedBy if the concept was replaced by another one to RDF. - How to enter info in xlsx? Reuse changeNote column and special notation `replaced_by <IRI>`.
- [done] Step 5: Improved and more precise provenance info modelling
  - Use prov:has_provenance for linking version-specific git blame page on github; for this add another column "Provenance" in concepts sheet before "Change Note" (read only)
  - Output the link also as rdfs:seeAlso (for Skosmos)
- [done] Step 6: Make concept scheme table read only. Instead integrate the metadata into IDranges file and read from it. The idranges file probably should also have a version for its structure.
- [done] Step 7 (minor & optional): Output IDrange contributor info to a "ID ranges" sheet in xlsx (read-only). Make a table with 3 columns gh-name, id-ranges, unused IDs in range. Give ID ranges as string like "0001040 - 0001050", in unused IDs give the number of unused ID and the first unused, e.g. "next unused: 0001040, unused: 10"
- [done] Step 8: The concepScheme metadata are almost all optional after step 7. But we need to distinguish: First, we want to import as much as possible from 043. Second, we need a specification which metadata are optional in v1.0 to apply in code and document in IDranges.toml template:
  - vocabulary_iri - present in 0.43 - mandatory
  - prefix - new in v1.0 - optional
  - title - present in 0.43 - mandatory
  - description - present in 0.43 - mandatory
  - created_date - present in 0.43 - mandatory
  - creator - present in 0.43 - mandatory
  - publisher - present in 0.43 - optional
  - custodian - present in 0.43 - optional
  - catalogue_pid - present in 0.43 - optional
  - documentation - new in v1.0 - optional
  - issue_Tracker - new in v1.0 - optional
  - helpdesk - new in v1.0 - optional
  - repository - new in v1.0 - mandatory
  - homepage - new in v1.0 - optional
  - conform_to - new in v1.0 - optional

- Extra step I:
  - (a) Add name to idranges (it should be manually taken from the given ORCID profile).
    Having the name allows to create a proper list of all contributors and add that to the concept scheme in RDF & xlsx.
    The name in idranges should be optional.
    So a contributor may just show up with only the gh-name if ORCID or name is not given.
  - (b) Derive who contributed from the ID ranges used (we compute this for idranges sheet).
    Everyone who used any ID from their reserved range is a contributor.


- Deferred idea (not important to expose to user): Add support to optionally declare skos:broaderTransitive (and its inverse skos:narrowTransitive). Specify transitivity in xlsx like this: "voc4cat:0000184 T (actions)". The idea is to use the ParentIRI column for transitive and non-tranisitve (normal) relations. Note that 043 did not have transitivity at all.

Each step should be done in a separate PR and each step should be well tested.
