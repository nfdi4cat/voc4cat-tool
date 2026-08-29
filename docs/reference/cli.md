# CLI Reference

Complete reference for the voc4cat command-line interface.

## Global options

```bash
voc4cat [-h] [-V] {transform,convert,check,docs,template} ...
```

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message |
| `-V, --version` | Show voc4cat version |

:::

## Common options

These options are available on all subcommands:

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `-v, --verbose` | More verbose output (repeat for more: `-vv`, `-vvv`) |
| `-q, --quiet` | Less verbose output (repeat for less: `-qq`, `-qqq`) |
| `--config CONFIG` | Path to config file (typically `idranges.toml`) |
| `-O, --outdir DIR` | Output directory (created if needed) |
| `-l, --logfile FILE` | Log to file at given path |

:::

## convert

Convert between xlsx and RDF formats.

```bash
voc4cat convert [options] VOCAB
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | File or directory to process |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--outputformat {turtle,xml,json-ld}` | RDF output format (default: turtle) |
| `--from {043,auto}` | Source format version for RDF-to-RDF conversion |
| `-t, --template FILE` | xlsx template for SKOS to xlsx conversion |

:::

### Examples

```bash
# xlsx to turtle
voc4cat convert --config idranges.toml myvocab.xlsx

# turtle to xlsx
voc4cat convert --config idranges.toml --outdir . myvocab.ttl

# Convert all files in directory
voc4cat convert --config idranges.toml vocabularies/

# Output as JSON-LD
voc4cat convert --config idranges.toml --outputformat json-ld myvocab.xlsx

# Convert from old 0.4.3 format
voc4cat convert --config idranges.toml --from 043 old_vocab.ttl
```

## transform

Transform vocabularies (same input/output format). Used for splitting and joining turtle files.

```bash
voc4cat transform [options] VOCAB
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | File or directory to process |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--split` | Split single turtle file into one file per concept |
| `--join` | Join split turtle files into single file |
| `--prov-from-git` | Add `dct:created` and `dct:modified` dates from git history |
| `--diff-base REF` | Git ref to compare against with `--prov-from-git` |
| `--modified-date DATE` | Date to write as `dct:modified` instead of the date from git |
| `--inplace` | Modify files in place (removes source) |

:::

### Split/Join workflow

Large turtle files produce difficult-to-review git diffs. The split format stores each concept in a separate file, making changes easier to review.

Concepts are partitioned into subdirectories by ID range (1000 IDs per directory) to avoid GitHub UI limitations with large directories:

```
vocabularies/myvocab/
├── concept_scheme.ttl
└── IDs0001xxx/
    ├── 0001001.ttl
    └── 0001002.ttl
```

The directory name padding matches the vocabulary's `id_length` setting (e.g., `IDs0001xxx` for 7-digit IDs, `IDs001xxx` for 6-digit IDs).

The voc4cat-template workflows use split format for storage and join files when needed for documentation or export.

### Examples

```bash
# Split into directory (creates myvocab/ folder)
voc4cat transform --split myvocab.ttl

# Split and remove original file
voc4cat transform --split --inplace myvocab.ttl

# Join split files back into single file
voc4cat transform --join myvocab/

# Join and remove source directory
voc4cat transform --join --inplace myvocab/

# Add provenance dates from git history to split files
voc4cat transform --prov-from-git --inplace myvocab/

# Same, but date only the concepts that changed since origin/main
voc4cat transform --prov-from-git --diff-base origin/main --inplace myvocab/

# Same, but write to output directory
voc4cat transform --prov-from-git --outdir output/ myvocab/

# Date the changed concepts with a date supplied by the caller
voc4cat transform --prov-from-git --diff-base origin/main --modified-date 2026-08-30 --inplace myvocab/
```

### Git provenance workflow

The `--prov-from-git` option adds Dublin Core provenance dates to split turtle files based on git history:

- **`dct:created`**: Added only if missing, set to the date of the first commit
- **`dct:modified`**: Updated when different from the most recent commit date

With `--diff-base REF` only concepts whose content changed compared to REF get updated dates;
unchanged concepts keep the dates they have in REF.

#### Supplying the modification date

`--modified-date DATE` writes DATE as `dct:modified` for the concepts that differ from REF, instead of the date taken from git.
The concept scheme gets DATE whenever any file of the vocabulary differs from REF, because editing a concept usually leaves `concept_scheme.ttl` untouched and its date would otherwise never advance.
Concepts that are unchanged compared to REF keep the dates they have in REF, as without the option.

A concept file that no commit has touched yet gets DATE as both `dct:created` and `dct:modified`.
Such a file is skipped without the option, because git offers no dates for it, and it would reach the repository with no provenance at all.

Use it where the turtle files are generated and committed *after* this command runs, as in the pull-request workflow of the voc4cat-template.
There the change being stamped is not yet in any commit, so git reports the previous edit and the date written is one cycle behind.

`--modified-date` requires `--diff-base`: without a base there is no set of changed concepts, so the date would be forced on the whole vocabulary.

Requirements:
- Untracked `.ttl` files are skipped with an info message unless `--modified-date` supplies their dates
- Requires either `--inplace` or `--outdir`
- The repository must not use squash merging (see below)

#### Merge strategy

Dates are read from the **author** date of each commit that touched a concept file, so the repository's merge strategy decides whether they survive.

:::{important}
Disable squash merging in repositories that use `--prov-from-git`.
:::

| Merge strategy | Author dates | Result |
|----------------|--------------|--------|
| Merge commit | Preserved from the pull request branch | Safe |
| Rebase merging | Replayed, author dates preserved | Safe |
| Squash merging | Replaced by one commit dated at merge time | **Dates are lost** |

Squashing discards the commits of the pull request branch. A concept created on one day and merged on another therefore keeps a `dct:created` value that no commit corroborates. Because a spreadsheet carries no date columns, the next xlsx submission strips all dates and re-derives them from what git can still see - the squash commit - silently rewriting the original creation date in a pull request that has nothing to do with that concept.

## check

Validate vocabularies and check CI pipeline state.

```bash
voc4cat check [options] [VOCAB]
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | File or directory to validate (optional for CI checks) |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--inplace` | Annotate xlsx files in place with validation results |
| `-p, --profile PROFILE` | SHACL profile token or path to a SHACL file (default: `vp4cat-5.3`) |
| `--fail-at-level {1,2,3}` | Minimum severity to fail: 1=info, 2=warning, 3=violation |
| `--listprofiles` | List available SHACL profiles |
| `--redundant-hierarchies` | Detect redundant hierarchical relationships |
| `--ci-pre INBOX` | Pre-merge CI check comparing INBOX to VOCAB |
| `--ci-post EXISTING` | Post-merge CI check comparing EXISTING to VOCAB |

:::

### Examples

```bash
# Basic validation
voc4cat check --config idranges.toml myvocab.ttl

# List available profiles
voc4cat check --listprofiles

# Validate with a bundled profile token
voc4cat check --config idranges.toml --profile vocpub-4.7 myvocab.ttl

# Validate with a custom SHACL file
voc4cat check --config idranges.toml --profile ./my-profile.ttl myvocab.ttl

# Only fail on violations (ignore warnings)
voc4cat check --config idranges.toml --fail-at-level 3 myvocab.ttl

# CI pre-merge check
voc4cat check --config idranges.toml --ci-pre inbox/ vocabularies/

# CI post-merge check
voc4cat check --config idranges.toml --ci-post existing/ vocabularies/

# Check for redundant broader relationships
voc4cat check --config idranges.toml --redundant-hierarchies myvocab.ttl
```

### ID range check

`--ci-post` verifies that IRIs added since the previous version use IDs from a range granted to the contributor who triggered the run. The contributor is read from the `GITHUB_ACTOR` environment variable and matched against `gh_name` in the `[[vocabs.VOCAB_NAME.id_range]]` sections of the vocabulary being checked. Ranges granted for a different vocabulary do not apply, and a contributor holding several ranges may use IDs from any of them.

IRIs that already existed in the previous version are not checked, so editing concepts created by others is unaffected. A vocabulary without a previous version is new, so all of its IRIs are checked.

If `GITHUB_ACTOR` is not set the check is skipped with a warning. On GitHub Actions, where `GITHUB_ACTIONS` is always set, the missing variable is an error instead, so a misconfigured workflow cannot silently skip the check.

### Inbox contents check

`--ci-pre` verifies that the inbox holds only vocabulary spreadsheets (`*.xlsx`) and markdown documentation (`*.md`). Anything else - data files, legacy `*.xls` spreadsheets, or subdirectories - is reported by name. Outside CI this is a warning; on GitHub Actions it is an error. Files whose name begins with a dot, such as `.gitkeep`, are ignored.

### Hierarchy redundancy check

The `--redundant-hierarchies` option detects redundant hierarchical relationships where a concept has `skos:broader` links to both a parent and an ancestor of that parent. For example, if concept C has broader B, and B has broader A, then C should not also have broader A directly. While such redundancies are OK in SKOS they cause problems for [Skosmos](https://skosmos.org/). So we suggest to remove them if you plan to host your vocabulary with Skosmos.

## docs

Generate HTML documentation from vocabularies.

```bash
voc4cat docs [options] VOCAB
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | File or directory to document |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--style {pylode}` | Documentation style (default: pylode) |
| `--force` | Overwrite existing output files |

:::

### Examples

```bash
# Generate documentation
voc4cat docs myvocab.ttl

# Output to specific directory
voc4cat docs --outdir docs/ myvocab.ttl

# Document all vocabularies
voc4cat docs --outdir docs/ vocabularies/

# Force overwrite
voc4cat docs --force --outdir docs/ myvocab.ttl
```

## template

Generate blank xlsx vocabulary templates.

```bash
voc4cat template [options] VOCAB
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | Vocabulary name, used as filename (VOCAB.xlsx) |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--version {v1.0}` | Template version (default: v1.0) |
| `-t, --template FILE` | xlsx file to use as base for the generated sheets |

:::

### Examples

```bash
# Generate template from config
voc4cat template --config idranges.toml --outdir . myvocab

# Explicit version
voc4cat template --config idranges.toml --version v1.0 --outdir . myvocab
```

## Additional tools

### voc-assistant

Detects quality issues using semantic similarity - finds potential duplicates, similar definitions, and typos. Useful for reviewing large vocabularies or comparing versions.

**Installation** (optional dependency):
```bash
pip install voc4cat[assistant]
```

**Usage:**
```bash
# Check single vocabulary for internal duplicates
voc-assistant check myvocab.ttl

# Compare two vocabularies (e.g., before/after changes)
voc-assistant compare existing.ttl new.ttl
```

### voc4cat-merge

Custom git merge driver for vocabulary files used in the GitHub action workflows. It is hardly useful locally.

## Environment variables

:::{table}
:align: left

| Variable | Description |
|----------|-------------|
| `LOGLEVEL` | Log level for console and logfile (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `VOC4CAT_VERSION` | Version string to embed in converted vocabularies (must start with `v`) |
| `VOC4CAT_MODIFIED` | Modified date to embed instead of today's date |
| `GITHUB_ACTOR` | Contributor whose ID ranges `check --ci-post` enforces |
| `GITHUB_REPOSITORY` | `owner/repo` used to build git blame links |
| `GITHUB_ACTIONS` | Set by GitHub Actions; turns the advisory checks of `check --ci-pre` and `--ci-post` into errors |
| `CI` | Also build the multi-release index page in `docs` |

:::

## Exit codes

:::{table}
:align: left

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, file not found, etc.) |

:::
