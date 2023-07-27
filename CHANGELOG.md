# Change log

## Release 0.5.0 (2023-07-27)

New features:

- Support for a vocabulary configuration file `idranges.toml`. Via this configuration file ranges of IDs can be assigned/reserved for individual contributors. #131, #134
- Extended validation/checks especially useful for the CI-vocabulary pipeline of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template). The new config provides the basis for more thorough validation. #126 #134
- Support for pylode as new documentation generator which is also the new default. #115
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
