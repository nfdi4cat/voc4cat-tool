# Change log

## Release 0.9.2 (2025-04-24)

Feature:

- Add a command/tool to help with reviewing (e.g. by performing sentence-transformer based similarity analysis) #279, #280

Bug fix:

- Tailing comma in ChildrenIRI raises error #277, #278

Change:

- Remove tailing and starting spaces from prefLabel and other Excel cells #281, #282

## Release 0.9.1 (2025-03-19)

Bug fixes:

- Fix writing to sheet "Additional Concept Features" (mappings could be lost) #270, #272
- Stop filling source vocab URI column with concept URI hyperlink (bug introduced in Release 0.9.0) #269, #271

## Release 0.9.0 (2025-02-04)

Features:

- In xlsx-files IRIs will now be shown as `https://example.org/001 (example 001)` or (if a matching prefix exists) as `ex:001 (example 001)`. The preferred label is used as qualifier of the IRI (in round brackets). #253, #258
- Improve styling of generated xlsx. The style is now copied from the first data row to all following rows. The row height is auto-adjusted. #260, #264, #265

Breaking changes:

- The sheet "Prefixes" is now read-only. Prefixes can now only be defined in `idranges.config`. #257, #263
- Removed executable script `merge_vocab` #244, #259

Changes:

- New, better styled default template `src/voc4cat/blank_043.xlsx` #265

Bug fixes:

- Handling of prefixes for multiple vocabularies. #257, #263
- Prefixes given in `idranges.toml` were ignored. #205 #257, #263

## Release 0.8.8 (2025-01-27)

0.8.8 only contains a fix for a bug introduced in 0.8.6.

Bug fixes:

- Fix jumping over every second row when writing concepts to xlsx (#254 fixed in #255)

## Release 0.8.6 / 0.8.7 (2025-01-26)

0.8.7 only adds a missed commit with the CHANGENOTES and README updates.

Bug fixes:

- Fix handling of mappings to external vocabularies/ontologies #242

New features:

- Support Python 3.13 #234

Changes:

- Write only concepts with mapping to "Additional Concept Features" sheet #246
- Add alternate name `voc4cat-merge` for executable script `merge_vocab` by #243
- Make pyLODE optional (remove from dependencies) #250

## Release 0.8.5 (2024-03-09)

Bug fixes:

- Fix creation of two ttl-files for sub-command "join" with "--outbox" option. #215, #216

## Release 0.8.4 (2024-03-04)

Bug fixes:

- Fix transform join subcommand to produce vocpub-4.7-conform turtle file. #213

## Release 0.8.3 (2024-02-28)

Bug fixes:

- Fix writing to wrong file location for sub-command "join" with "--outbox" option. #211, #212
- Fix clearing of cells with hyperlinks in xlsx by openpyxl. #209, #210

## Release 0.8.2 (2024-02-21)

Bug fixes:

- Fix agent name type in turtle as required by vocpub profile 4.7. #206, #207

## Release 0.8.1 (2024-02-20)

Bug fixes:

- Add colorama as a main dependency. #204

## Release 0.8.0 (2024-02-19)

New features:

- Support for Python 3.12. #202

Changes:

- Support current vocpub profile 4.7. #198, #199

Breaking changes:

- Remove alternative documentation generation with ontospy. #200, #202

## Release 0.7.10 (2024-02-11)

New features:

- Add coverage summary as job output. #197

Changes:

- Document which vocpub profile is used in 0.7.x series and move profiles to separate directory. #195, #196

## Release 0.7.9 (2024-02-01)

Bug fixes:

- Adjust validation of GitHub user names to allow uppercase. #193, #194

## Release 0.7.8 (2023-10-30)

Bug fixes:

- In CI, read modified date of concept scheme CS from env.var (& fix its type). #177, #178

## Release 0.7.7 (2023-10-30)

Changes:

- Upgrade curies package (to >= 0.6.6) and use new passthrough option. #173, #176

Bug fixes:

- Consistent validation with pydantic and SHACL/vocpub (disallow None). #174, #175

## Release 0.7.5 / 0.7.6 (2023-09-03)

In 0.7.6 we fixed the license specifier for Zenodo and the link to the changelog for PyPI.

New features:

- Add creation of an index-page for the root of gh-pages. #160, #165

Changes:

- Replaced CITATION.cff by CITATION.bib to avoid side effects on data in Zenodo. #166, #167, #168
- Provide metadata for Zenodo completely via `.zenodo.json`. The metadata have also been enriched significantly. #167, #168

## Release 0.7.4 (2023-08-31)

New features:

- Expand tables to include full content. This happens every time when an xlsx-file is written. #155, #159

Changes:

- Change HTML documentation to use IRI as id (anchor) in html. #156
- List members in collections in alphabetical order (in HTML documentation). #162

Bug fixes:

- Creator and publisher missing in generated HTML documentation. #154

## Release 0.7.2 / 0.7.3 (2023-08-23)

First release after setting up Zenodo integration (0.7.2) and fix of Zenodo community (0.7.3).

There were no functional changes since 0.7.1.

## Release 0.7.1 (2023-08-22)

First release to upload to PyPI.

There were no functional changes since 0.7.0.

## Release 0.7.0 (2023-08-16)

New features:

- In concept scheme sheet creator can now be ORCID, ROR ID or a predefined string; publisher can be ROR ID or a predefined string (for example `NFDI4Cat`) #120, #151
- Support for two environment variables was added. If present they will be used with highest preference. #148
  - `VOC4CAT_MODIFIED` - Can be used to supply a modified date.
  - `VOC4CAT_VERSION` - version string; it must start with "v".
- voc4cat detects if it runs in gh-actions. In gh-actions it clears the modified date to avoid tracking its changes with git. #148

Changes:

- In concept scheme sheet, modified date and version are now optional. #148
- Update notes xlsx-template and example files. #152
- Use rotating logfiles instead of single file by default. #149, #150

Bug fixes:

- Modified date of concept scheme was not transferred from xlsx to rdf. #147, #148

## Release 0.6.2 (2023-08-10)

New features:

- Option `--ci-post` of sub-command `voc4cat check` was improved to detect and work with split vocabularies. #146

## Release 0.6.1 (2023-08-10)

New features:

- The `merge_vocab` script gained support for directories containing vocabularies created with `voc4cat transform --split`. This feature is used in gh-actions of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)-based vocabularies. #144

Changes:

- The use of logging levels was made more consistent: Success of an operation is now logged for all operation on INFO level. #145
- The log file will now always be written to the given directory. Previously the log file directory depended on the presence of the `--outdir` option. #144

Bug fixes:

- Sub-command `voc4cat docs` failed if `--outdir` was not given. #143 #144

## Release 0.6.0 (2023-08-09)

New features:

- New command line interface `voc4cat` that uses subcommands `transform`, `convert`, `check` and `docs`.
  This was added as preview in Release 0.5.1 and is now the default.
  With the new CLI conversion and validation are no longer coupled but can be run separately. #140, #141
- New options for subcommand `transform`: `--split` to split a large SKOS/rdf file to a directory of files with one file per concept/collection. `--join` for the reverse operation of  transforming the directory of files back to a single turtle vocabulary. #139

Changes:

- As part of the CLI work, the vocexcel CLI was removed. #141
- Consistent use and handling of exceptions. #136

## Release 0.5.1 (2023-08-03)

New features:

- New (experimental) command line interface `voc4cat-ng` that will replace the current one in 0.6.0. #128, #135
- When adding IDs via --make-IDs, the new CLI offers to pass a base-IRI (see help `voc4cat-ng transform --help`).

Changes:

- Various small changes to improve test coverage (now 96 %) and reduce the number of linter complaints (from 38 to 25).

## Release 0.5.0 (2023-07-27)

New features:

- Support for a vocabulary configuration file `idranges.toml`.
  Via this configuration file ranges of IDs can be assigned/reserved for individual contributors. #131, #134
- Extended validation/checks especially useful for the CI-vocabulary pipeline of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template).
  The new config provides the basis for more thorough validation. #126 #134
- Support for pylode2 as new documentation generator which is also the new default. #115
- Added a central logging config. Updated code to use logging instead of print() almost everywhere.

Changes:

- Merged some parts from vocexcel to remove vocexcel as a dependency. #119
- Various code improvements. #126, #127, #129
- Adapted and revised example files. #137
- Switched to [ruff](https://github.com/astral-sh/ruff) as code linter.

Bug fixes:

- None.

## Release 0.4.0 (2023-03-15)

First public release of voc4cat on github.

## Earlier releases

Before 0.4.0 the code was in alpha state and kept private.
See git commit log and the issues & milestones in this repository for the early history.

Just before 0.4.0 the code was migrated from a private gitlab instance to github.
The transfer went OK but not perfect (gitlab-MRs were not well converted to github-PRs).
