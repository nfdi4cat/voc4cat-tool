# Change log

## Release 0.6.x (2023-08-dd)

New features:

- The `merge_vocab` script gained support for directories containing vocabularies created with `voc4cat transform --split`. This feature is used in gh-actions of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)-based vocabularies.

Changes:

- The log file will now always be written to the given directory. Previously the log file directory depended on the presence of the `--outdir` option.

Bug fixes:

- Sub-command `voc4cat docs` failed if `--outdir` was not given.

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
