# Task for version 1.0.0

https://github.com/nfdi4cat/voc4cat-tool/issues/124

Ideas are marked as done here if they have been implemented in dev-1.0.0 branch (and therefore become part of v1.0.0).

## Implementation plan

- [done] Step 1: Create python code that generates the structure of `src/voc4cat/templates/vocab/blank_1.0_min.xlsx` (but not the enum sheet)
- [done] Step 2a: Adapt converter to output v043 rdf data of current rdf-schema into the new template reusing `src/voc4cat/models.py`
- [done] Step 2b: Adapt converter for roundtripping with v043 rdf and xlsx v1.0
- [done] Step 3: Add support for new columns in template v1.0 to read their data and output as RDF. The two way conversion RDF <-> XLXS must be lossless. In order to convert existing RDF data created with template 043 we need to be able to read in these RDF data and convert them into V1.0 RDF. We only need a one-way conversion 043-to-v1.0.
- [done] Step 4: Improve deprecation handling
  - Enum (string) in skos:historyNote - if present and filled with reason from enum, add "OBSOLETE " at the start of the  prefLabel of the concept (only for default language "en") if the prefLabel does not yet start likewise.
  - Add dct:replacedBy if the concept was replaced by another one to RDF. - How to enter info in xlsx? Re-use changeNote column and special notation `replaced_by <IRI>`.
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

## Template

This is a list of structural changes for 1.0.0.
The most current template draft is `src/voc4cat/templates/vocab/blank_1.0_min.xlsx`

- Support for skos:altLabel in multiple languages. Currently it is assumed that all (comma-separated) altLabels are always given in the default language "en".
  - [x] Included in template draft
  - [ ] Implemented in code
- Support different languages for collection prefLabel.
  - [x] Included in template draft
  - [ ] Implemented in code
- Make multi-language data entry easier by specifying just one language per line in the concept sheet.
  - [x] Included in template draft
  - [ ] Implemented in code
- Add a notes/feedback column (skos:editorialNote) for editorial purposes. It could be used by tools (or humans) to add notes which are relevant for  editing the concept/collection. This column may also be used by checking tools.
  - [x] Included in template draft
  - [ ] Implemented in code
- [ ] Change provenance column to skos:changeNote column to store a link to git blame output on github (maybe redirected via w3id.org). The link must be version dependent and is autocreated (read-only).
  - [x] Included in template draft
  - [ ] Implemented in code
- Support two ways of giving credit to used sources:
  - (i) vebratim copies; the source should be entered in columns "Source Vocab" (dct:source), "Source Vocab license", "Source Vocab Rights holder"
  - (ii) definitions influenced by other sources; these should be entered in "Influenced by IRIs" column.
  - [x] Included in template draft
  - [ ] Implemented in code
- ~~Add a status column with states proposed/accepted/obsolete~~ Auto generate skos:historyNote with date & state upon change. Suggested states to track: created, obsoleted because ... (see next point). This information will not be present in Excel but only in turtle.
  - [x] Included in template draft
  - [ ] Implemented in code
- [ ] Add column for reason of obsoletion and provide pre-defined reasons for obsoletion (inspired by https://wiki.geneontology.org/index.php/Obsoleting_an_Existing_Ontology_Term); see also [deprecation in Skosmos](https://github.com/NatLibFi/Skosmos/wiki/Data-Model#deprecated-concepts)
  - Choices
    - The term is not clearly defined and usage has been inconsistent.
    - This term was added in error.
    - More specific terms were created.
    - This term was converted to a collection.
    - The meaning of the term is ambiguous.
    - There is no evidence that this function/process/component exists.
  - [x] Included in template draft
  - [ ] Implemented in code
- [ ] (maybe) Use [tables](https://openpyxl.readthedocs.io/en/latest/worksheet_tables.html) instead of hard-coded cell-positions and sheet names. Tables can be found independently of their cell position and "home" sheet. This would give users more flexibility to adjust the layout. (previously suggested [here](https://github.com/surroundaustralia/VocExcel/issues/31#issue-1227553740))
  - [x] Included in template draft
  - [ ] Implemented in code

- Add column to support skos:orderedCollection
  - [x] Included in template draft
  - [ ] Implemented in code
- (optionally) display a notation column
  - [ ] Implemented in code

Collection membership:

- [ ] Use a new column skos:member (meaning "is member of") in concepts sheet to express membership of a concept in 0...N ollections.
  - [x] Included in template draft
  - [ ] Implemented in code
- [ ] Change the column in collection sheet to express "is member of" for collections in collections.
  - [x] Included in template draft
  - [ ] Implemented in code

### Converter

- [ ] Use a different separator than comma in xlsx cells. Users often use a comma as part of the text and/or use a semicolon as separator because they are used to semicolons from Excel formulas. It is suggested to separate urls from other urls or text by space (and/or) newline. For pure text fields (alternate label), we should consider to use a vertical bar | as separator.
- Add skos:notation (ID of concept) in RDF output
- [ ] The user should never change anything in the concept scheme sheet of the template. So the sheet should just be created as info-page but never read. To realize this we need to extend the vocabulary configuration file. Some additional fields should be added (e.g. homepage-URL or issue-tracker-URL).
- [ ] (maybe) Output [SKOS-XL](https://www.w3.org/TR/skos-reference/#xl). Then a unique ID for each translation allows to make statements on the translated concept, e.g. about provenance of the translation. Skosmos supports SKOS-XL labels.
- [ ] (maybe) Support [skos:orderedCollection](https://www.w3.org/TR/skos-reference/#collections). Skosmos does not support skos:orderedCollection, https://github.com/NatLibFi/Skosmos/issues/1268 but may use skos:notation to sort concepts.
- [ ] (maybe) Support not-yet supported SKOS relations like [skos:broaderTransitive](https://www.w3.org/TR/skos-reference/#broaderTransitive), [skos:narrowerTransitive](https://www.w3.org/TR/skos-reference/#narrowerTransitive)

### Profile

- [ ] Allow prefLabel in multiple languages (see [vocexcel#1](https://github.com/RDFLib/VocExcel/issues/1)). We probably need our own SHACL vocabulary profile.
- [ ] Several changes suggested above e.g. the use of skos:notes require profile changes.
