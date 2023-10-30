# Change log

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
