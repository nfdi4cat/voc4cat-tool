# Task for version 1.0.0

https://github.com/nfdi4cat/voc4cat-tool/issues/124

Ideas are marked as done here if they have been implemented in dev-1.0.0 branch (and therefore become part of v1.0.0).

### Template

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
