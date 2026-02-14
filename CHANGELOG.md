# Change log

## Release 1.0.3 (2026-02-14)

Fixes:

- Reject IDs with wrong digit count during `voc4cat convert`. Previously, IDs with more digits than configured (e.g. 8 digits with `id_length: 7`) were silently accepted because the regex matched only the trailing digits. [#341](https://github.com/nfdi4cat/voc4cat-tool/issues/341)

## Release 1.0.2 (2026-02-09)

Fixes:

- Allow untracked .ttl files in `--prov-from-git`. Skip them with an info log instead of raising an error. [#339](https://github.com/nfdi4cat/voc4cat-tool/issues/339)

## Release 1.0.1 (2026-01-06)

Fixes:

- Fix git blame URLs to include partition subdirectory (e.g., `IDs0000xxx/`) matching the new partitioned storage structure. [#335](https://github.com/nfdi4cat/voc4cat-tool/pull/335)

## Release 1.0.0 (2025-12-31)

Features:

- **Partitioned storage:** The `--split` option now organizes concept files into subdirectories by ID range (1000 IDs per directory, e.g., `IDs0001xxx/`). This avoids GitHub UI limitations with large directories. The `--join` option supports both the new partitioned structure and the previous flat structure. [#328](https://github.com/nfdi4cat/voc4cat-tool/pull/328)
- **Namespace prefixes in RDF:** The `transform` command now uses namespace bindings/prefixes in output (as convert already did). [#327](https://github.com/nfdi4cat/voc4cat-tool/pull/327)
- **Longturtle format:** Turtle files are now written in longturtle format everywhere (this was not the case in rc1/2). [#327](https://github.com/nfdi4cat/voc4cat-tool/pull/327)
- **Improved `--prov-from-git`:** Git history evaluation now follows file moves/renames. [#329](https://github.com/nfdi4cat/voc4cat-tool/pull/329)

Changes:

- Improved migration guide and template update guide.

- Fix BASE declaration in vp4cat profile; allow `dct:provenance` with IRI value (Req. 2.2.2). [#325](https://github.com/nfdi4cat/voc4cat-tool/pull/325), [#326](https://github.com/nfdi4cat/voc4cat-tool/issues/326)
- Fix reporting for `check --detect-hierarchy-redundancy`. [#323](https://github.com/nfdi4cat/voc4cat-tool/pull/323)
- Fix openpyxl warning about worksheet selection.
- Fix xlsx generation to mark only one sheet as selected.


## Release 1.0.0 (RC2) (2025-12-27)

The following changes were made to RC1 based on testing it with the voc4cat vocabulary and Skosmos 3.0.

Features:

- **New transform option `--prov-from-git`:** Adds `dct:created` and `dct:modified` dates to split turtle files based on git history. Created date is only added if missing; modified date is updated when different.
- **New check option `--detect-hierarchy-redundancy`:** Detects redundant hierarchical relationships where a concept has `skos:broader` to both a parent and an ancestor of that parent.
- **Added `dct:isReplacedBy` columns** to Concepts and Collections sheets for specifying replacement IRIs when deprecating concepts.

Changes:

- **Changed `dct:identifier` format:** Now uses just the local numeric ID (e.g., `0000123` instead of `voc4cat_0000123`).
- **`skos:historyNote` solely for obsoletion:** History notes are no longer generated from provenance data; they are now exclusively used for documenting concept obsoletion.

## Release 1.0.0 (RC1) (2025-12-22)

:::{important}
This is a major release with breaking changes.
Vocabularies and xlsx-templates must be upgraded from xlsx template v0.43 to v1.0, see [migration-to-v1.0](https://nfdi4cat.github.io/voc4cat-tool/migration-to-v1.0.html).
:::

Features:

- **New xlsx template v1.0** with pydantic-backed model for improved consistency and validation. Template generator creates files dynamically from the data model. It is no longer required to provide an xlsx-template (but still an option).
- **ConceptScheme metadata** is now read from `idranges.toml` config.
- **New validation profile vp4cat-5.2** based on vocpub-5.2, now the default profile.
- **Custom profile support:** Accept custom SHACL profile files for validation via CLI path or config.
- **Improved provenance support**
  - **Improved citation** of the concept's origin by properties `prov:wasInfluencedBy`, `prov:hadPrimarySource` and to reference its `dct:license` and the `dct:rightsHolder`. This allows to reference the source.
  - **Git blame links:** Provenance information links to git blame URLs for traceability.
  - **Dynamic `skos:historyNote`:** Auto-generated from `PROV.wasInfluencedBy` and source vocab references.
- **Deprecation handling:** Support for `owl:deprecated`, replaced-by IRIs, and obsolete markers.
- **ID ranges sheet:** New output sheet displaying ID range configuration.
- **Python 3.14 support** added to test matrix.
- **Sphinx documentation** including action to build and publish the docs to GitHub Pages.
- **Improved Skosmos support** by aligning with its [data model](https://github.com/NatLibFi/Skosmos/wiki/Data-Model) when possible.

Breaking changes:

- **New xlsx template format v1.0** replaces template v0.43. Migration required for existing vocabularies.
- **Removed CLI option `voc4cat transform --make-ids`**.
- **Profile changes:** Removed vocpub pre-3.0 profile; vp4cat-5.2 is now default.

Other Changes:

- Code refactoring: eliminated duplication, split large modules, improved test coverage.
- Removed all binary xlsx-files from the repository
- Switch from codespell to typos spell checker.

## Release 0.10.1 (2025-12-15)

**This is the last release of the 0.x series.**

Changes:

- Removed extra code related to 1.0-series which was not used at all.

## Release 0.10.0 (2025-11-29)

:::{important}
Due to the change of hierarchy notation, it is not possible to use XLSX templates made for earlier versions.
:::

Features:

- **BREAKING** Hierarchy definition changed from ChildrenIRI to ParentIRI approach.
  Each concept specifies its parent concepts rather than its children concepts.  (part of [#300](https://github.com/nfdi4cat/voc4cat-tool/issues/300))
- **BREAKING** Removed functionality to express concept-hierarchies by indentation in xlsx table cells.  (part of [#300](https://github.com/nfdi4cat/voc4cat-tool/issues/300))

Changes:

- **BREAKING** Read template version number from Concept Scheme Sheet (cell B13) instead of Introduction sheet (part of [#300](https://github.com/nfdi4cat/voc4cat-tool/issues/300) by @dalito)
- Migrate codebase to pydantic2 by @dalito in [#283](https://github.com/nfdi4cat/voc4cat-tool/pull/283)

## Release 0.9.2 (2025-04-24)

Feature:

- Add a command/tool to help with reviewing (e.g. by performing sentence-transformer based similarity analysis) [#279](https://github.com/nfdi4cat/voc4cat-tool/issues/279), [#280](https://github.com/nfdi4cat/voc4cat-tool/pull/280)

Bug fix:

- Tailing comma in ChildrenIRI raises error [#277](https://github.com/nfdi4cat/voc4cat-tool/issues/277), [#278](https://github.com/nfdi4cat/voc4cat-tool/pull/278)

Change:

- Remove tailing and starting spaces from prefLabel and other xlsx table cells [#281](https://github.com/nfdi4cat/voc4cat-tool/issues/281), [#282](https://github.com/nfdi4cat/voc4cat-tool/pull/282)

## Release 0.9.1 (2025-03-19)

Bug fixes:

- Fix writing to sheet "Additional Concept Features" (mappings could be lost) [#270](https://github.com/nfdi4cat/voc4cat-tool/issues/270), [#272](https://github.com/nfdi4cat/voc4cat-tool/pull/272)
- Stop filling source vocab URI column with concept URI hyperlink (bug introduced in Release 0.9.0) [#269](https://github.com/nfdi4cat/voc4cat-tool/issues/269), [#271](https://github.com/nfdi4cat/voc4cat-tool/pull/271)

## Release 0.9.0 (2025-02-04)

Features:

- In xlsx-files IRIs will now be shown as `https://example.org/001 (example 001)` or (if a matching prefix exists) as `ex:001 (example 001)`. The preferred label is used as qualifier of the IRI (in round brackets). [#253](https://github.com/nfdi4cat/voc4cat-tool/issues/253), [#258](https://github.com/nfdi4cat/voc4cat-tool/pull/258)
- Improve styling of generated xlsx. The style is now copied from the first data row to all following rows. The row height is auto-adjusted. [#260](https://github.com/nfdi4cat/voc4cat-tool/issues/260), [#264](https://github.com/nfdi4cat/voc4cat-tool/pull/264), [#265](https://github.com/nfdi4cat/voc4cat-tool/pull/265)

Breaking changes:

- The sheet "Prefixes" is now read-only. Prefixes can now only be defined in `idranges.config`. [#257](https://github.com/nfdi4cat/voc4cat-tool/issues/257), [#263](https://github.com/nfdi4cat/voc4cat-tool/pull/263)
- Removed executable script `merge_vocab` [#244](https://github.com/nfdi4cat/voc4cat-tool/issues/244), [#259](https://github.com/nfdi4cat/voc4cat-tool/pull/259)

Changes:

- New, better styled default template `src/voc4cat/blank_043.xlsx` [#265](https://github.com/nfdi4cat/voc4cat-tool/pull/265)

Bug fixes:

- Handling of prefixes for multiple vocabularies. [#257](https://github.com/nfdi4cat/voc4cat-tool/issues/257), [#263](https://github.com/nfdi4cat/voc4cat-tool/pull/263)
- Prefixes given in `idranges.toml` were ignored. [#205](https://github.com/nfdi4cat/voc4cat-tool/issues/205) [#257](https://github.com/nfdi4cat/voc4cat-tool/issues/257), [#263](https://github.com/nfdi4cat/voc4cat-tool/pull/263)

## Release 0.8.8 (2025-01-27)

0.8.8 only contains a fix for a bug introduced in 0.8.6.

Bug fixes:

- Fix jumping over every second row when writing concepts to xlsx ([#254](https://github.com/nfdi4cat/voc4cat-tool/issues/254) fixed in [#255](https://github.com/nfdi4cat/voc4cat-tool/pull/255))

## Release 0.8.6 / 0.8.7 (2025-01-26)

0.8.7 only adds a missed commit with the CHANGENOTES and README updates.

Bug fixes:

- Fix handling of mappings to external vocabularies/ontologies [#242](https://github.com/nfdi4cat/voc4cat-tool/pull/242)

New features:

- Support Python 3.13 [#234](https://github.com/nfdi4cat/voc4cat-tool/pull/234)

Changes:

- Write only concepts with mapping to "Additional Concept Features" sheet [#246](https://github.com/nfdi4cat/voc4cat-tool/pull/246)
- Add alternate name `voc4cat-merge` for executable script `merge_vocab` by [#243](https://github.com/nfdi4cat/voc4cat-tool/pull/243)
- Make pyLODE optional (remove from dependencies) [#250](https://github.com/nfdi4cat/voc4cat-tool/pull/250)

## Release 0.8.5 (2024-03-09)

Bug fixes:

- Fix creation of two ttl-files for sub-command "join" with "--outbox" option. [#215](https://github.com/nfdi4cat/voc4cat-tool/issues/215), [#216](https://github.com/nfdi4cat/voc4cat-tool/pull/216)

## Release 0.8.4 (2024-03-04)

Bug fixes:

- Fix transform join subcommand to produce vocpub-4.7-conform turtle file. [#213](https://github.com/nfdi4cat/voc4cat-tool/pull/213)

## Release 0.8.3 (2024-02-28)

Bug fixes:

- Fix writing to wrong file location for sub-command "join" with "--outbox" option. [#211](https://github.com/nfdi4cat/voc4cat-tool/issues/211), [#212](https://github.com/nfdi4cat/voc4cat-tool/pull/212)
- Fix clearing of cells with hyperlinks in xlsx by openpyxl. [#209](https://github.com/nfdi4cat/voc4cat-tool/issues/209), [#210](https://github.com/nfdi4cat/voc4cat-tool/pull/210)

## Release 0.8.2 (2024-02-21)

Bug fixes:

- Fix agent name type in turtle as required by vocpub profile 4.7. [#206](https://github.com/nfdi4cat/voc4cat-tool/issues/206), [#207](https://github.com/nfdi4cat/voc4cat-tool/pull/207)

## Release 0.8.1 (2024-02-20)

Bug fixes:

- Add colorama as a main dependency. [#204](https://github.com/nfdi4cat/voc4cat-tool/pull/204)

## Release 0.8.0 (2024-02-19)

New features:

- Support for Python 3.12. [#202](https://github.com/nfdi4cat/voc4cat-tool/pull/202)

Changes:

- Support current vocpub profile 4.7. [#198](https://github.com/nfdi4cat/voc4cat-tool/issues/198), [#199](https://github.com/nfdi4cat/voc4cat-tool/pull/199)

Breaking changes:

- Remove alternative documentation generation with ontospy. [#200](https://github.com/nfdi4cat/voc4cat-tool/issues/200), [#202](https://github.com/nfdi4cat/voc4cat-tool/pull/202)

## Release 0.7.10 (2024-02-11)

New features:

- Add coverage summary as job output. [#197](https://github.com/nfdi4cat/voc4cat-tool/pull/197)

Changes:

- Document which vocpub profile is used in 0.7.x series and move profiles to separate directory. [#195](https://github.com/nfdi4cat/voc4cat-tool/issues/195), [#196](https://github.com/nfdi4cat/voc4cat-tool/pull/196)

## Release 0.7.9 (2024-02-01)

Bug fixes:

- Adjust validation of GitHub user names to allow uppercase. [#193](https://github.com/nfdi4cat/voc4cat-tool/issues/193), [#194](https://github.com/nfdi4cat/voc4cat-tool/pull/194)

## Release 0.7.8 (2023-10-30)

Bug fixes:

- In CI, read modified date of concept scheme CS from env.var (& fix its type). [#177](https://github.com/nfdi4cat/voc4cat-tool/issues/177), [#178](https://github.com/nfdi4cat/voc4cat-tool/pull/178)

## Release 0.7.7 (2023-10-30)

Changes:

- Upgrade curies package (to >= 0.6.6) and use new passthrough option. [#173](https://github.com/nfdi4cat/voc4cat-tool/issues/173), [#176](https://github.com/nfdi4cat/voc4cat-tool/pull/176)

Bug fixes:

- Consistent validation with pydantic and SHACL/vocpub (disallow None). [#174](https://github.com/nfdi4cat/voc4cat-tool/issues/174), [#175](https://github.com/nfdi4cat/voc4cat-tool/pull/175)

## Release 0.7.5 / 0.7.6 (2023-09-03)

In 0.7.6 we fixed the license specifier for Zenodo and the link to the changelog for PyPI.

New features:

- Add creation of an index-page for the root of gh-pages. [#160](https://github.com/nfdi4cat/voc4cat-tool/issues/160), [#165](https://github.com/nfdi4cat/voc4cat-tool/pull/165)

Changes:

- Replaced CITATION.cff by CITATION.bib to avoid side effects on data in Zenodo. [#166](https://github.com/nfdi4cat/voc4cat-tool/issues/166), [#167](https://github.com/nfdi4cat/voc4cat-tool/pull/167), [#168](https://github.com/nfdi4cat/voc4cat-tool/pull/168)
- Provide metadata for Zenodo completely via `.zenodo.json`. The metadata have also been enriched significantly. [#167](https://github.com/nfdi4cat/voc4cat-tool/pull/167), [#168](https://github.com/nfdi4cat/voc4cat-tool/pull/168)

## Release 0.7.4 (2023-08-31)

New features:

- Expand tables to include full content. This happens every time when an xlsx-file is written. [#155](https://github.com/nfdi4cat/voc4cat-tool/issues/155), [#159](https://github.com/nfdi4cat/voc4cat-tool/pull/159)

Changes:

- Change HTML documentation to use IRI as id (anchor) in html. [#156](https://github.com/nfdi4cat/voc4cat-tool/pull/156)
- List members in collections in alphabetical order (in HTML documentation). [#162](https://github.com/nfdi4cat/voc4cat-tool/pull/162)

Bug fixes:

- Creator and publisher missing in generated HTML documentation. [#154](https://github.com/nfdi4cat/voc4cat-tool/pull/154)

## Release 0.7.2 / 0.7.3 (2023-08-23)

First release after setting up Zenodo integration (0.7.2) and fix of Zenodo community (0.7.3).

There were no functional changes since 0.7.1.

## Release 0.7.1 (2023-08-22)

First release to upload to PyPI.

There were no functional changes since 0.7.0.

## Release 0.7.0 (2023-08-16)

New features:

- In concept scheme sheet creator can now be ORCID, ROR ID or a predefined string; publisher can be ROR ID or a predefined string (for example `NFDI4Cat`) [#120](https://github.com/nfdi4cat/voc4cat-tool/issues/120), [#151](https://github.com/nfdi4cat/voc4cat-tool/pull/151)
- Support for two environment variables was added. If present they will be used with highest preference. [#148](https://github.com/nfdi4cat/voc4cat-tool/pull/148)
  - `VOC4CAT_MODIFIED` - Can be used to supply a modified date.
  - `VOC4CAT_VERSION` - version string; it must start with "v".
- voc4cat detects if it runs in gh-actions. In gh-actions it clears the modified date to avoid tracking its changes with git. [#148](https://github.com/nfdi4cat/voc4cat-tool/pull/148)

Changes:

- In concept scheme sheet, modified date and version are now optional. [#148](https://github.com/nfdi4cat/voc4cat-tool/pull/148)
- Update notes xlsx-template and example files. [#152](https://github.com/nfdi4cat/voc4cat-tool/pull/152)
- Use rotating logfiles instead of single file by default. [#149](https://github.com/nfdi4cat/voc4cat-tool/issues/149), [#150](https://github.com/nfdi4cat/voc4cat-tool/pull/150)

Bug fixes:

- Modified date of concept scheme was not transferred from xlsx to rdf. [#147](https://github.com/nfdi4cat/voc4cat-tool/issues/147), [#148](https://github.com/nfdi4cat/voc4cat-tool/pull/148)

## Release 0.6.2 (2023-08-10)

New features:

- Option `--ci-post` of sub-command `voc4cat check` was improved to detect and work with split vocabularies. [#146](https://github.com/nfdi4cat/voc4cat-tool/pull/146)

## Release 0.6.1 (2023-08-10)

New features:

- The `merge_vocab` script gained support for directories containing vocabularies created with `voc4cat transform --split`. This feature is used in gh-actions of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)-based vocabularies. [#144](https://github.com/nfdi4cat/voc4cat-tool/pull/144)

Changes:

- The use of logging levels was made more consistent: Success of an operation is now logged for all operation on INFO level. [#145](https://github.com/nfdi4cat/voc4cat-tool/pull/145)
- The log file will now always be written to the given directory. Previously the log file directory depended on the presence of the `--outdir` option. [#144](https://github.com/nfdi4cat/voc4cat-tool/pull/144)

Bug fixes:

- Sub-command `voc4cat docs` failed if `--outdir` was not given. [#143](https://github.com/nfdi4cat/voc4cat-tool/issues/143) [#144](https://github.com/nfdi4cat/voc4cat-tool/pull/144)

## Release 0.6.0 (2023-08-09)

New features:

- New command line interface `voc4cat` that uses subcommands `transform`, `convert`, `check` and `docs`.
  This was added as preview in Release 0.5.1 and is now the default.
  With the new CLI conversion and validation are no longer coupled but can be run separately. [#140](https://github.com/nfdi4cat/voc4cat-tool/issues/140), [#141](https://github.com/nfdi4cat/voc4cat-tool/pull/141)
- New options for subcommand `transform`: `--split` to split a large SKOS/rdf file to a directory of files with one file per concept/collection. `--join` for the reverse operation of  transforming the directory of files back to a single turtle vocabulary. [#139](https://github.com/nfdi4cat/voc4cat-tool/pull/139)

Changes:

- As part of the CLI work, the vocexcel CLI was removed. [#141](https://github.com/nfdi4cat/voc4cat-tool/pull/141)
- Consistent use and handling of exceptions. [#136](https://github.com/nfdi4cat/voc4cat-tool/pull/136)

## Release 0.5.1 (2023-08-03)

New features:

- New (experimental) command line interface `voc4cat-ng` that will replace the current one in 0.6.0. [#128](https://github.com/nfdi4cat/voc4cat-tool/issues/128), [#135](https://github.com/nfdi4cat/voc4cat-tool/pull/135)
- When adding IDs via --make-IDs, the new CLI offers to pass a base-IRI (see help `voc4cat-ng transform --help`).

Changes:

- Various small changes to improve test coverage (now 96 %) and reduce the number of linter complaints (from 38 to 25).

## Release 0.5.0 (2023-07-27)

New features:

- Support for a vocabulary configuration file `idranges.toml`.
  Via this configuration file ranges of IDs can be assigned/reserved for individual contributors. [#131](https://github.com/nfdi4cat/voc4cat-tool/issues/131), [#134](https://github.com/nfdi4cat/voc4cat-tool/pull/134)
- Extended validation/checks especially useful for the CI-vocabulary pipeline of [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template).
  The new config provides the basis for more thorough validation. [#126](https://github.com/nfdi4cat/voc4cat-tool/issues/126) [#134](https://github.com/nfdi4cat/voc4cat-tool/pull/134)
- Support for pylode2 as new documentation generator which is also the new default. [#115](https://github.com/nfdi4cat/voc4cat-tool/pull/115)
- Added a central logging config. Updated code to use logging instead of print() almost everywhere.

Changes:

- Merged some parts from vocexcel to remove vocexcel as a dependency. [#119](https://github.com/nfdi4cat/voc4cat-tool/pull/119)
- Various code improvements. [#126](https://github.com/nfdi4cat/voc4cat-tool/issues/126), [#127](https://github.com/nfdi4cat/voc4cat-tool/pull/127), [#129](https://github.com/nfdi4cat/voc4cat-tool/pull/129)
- Adapted and revised example files. [#137](https://github.com/nfdi4cat/voc4cat-tool/pull/137)
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
