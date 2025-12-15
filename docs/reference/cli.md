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
| `--inplace` | Modify files in place (removes source) |

:::

### Split/Join workflow

Large turtle files produce difficult-to-review git diffs. The split format stores each concept in a separate file, making changes easier to review:

```
vocabularies/myvocab/
├── concept_scheme.ttl
├── 0001001.ttl
└── 0001002.ttl
```

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
```

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
| `-p, --profile PROFILE` | SHACL profile to check against (default: `vocpub`) |
| `--fail-at-level {1,2,3}` | Minimum severity to fail: 1=info, 2=warning, 3=violation |
| `--listprofiles` | List available SHACL profiles |
| `--ci-pre INBOX` | Pre-merge CI check comparing INBOX to VOCAB |
| `--ci-post EXISTING` | Post-merge CI check comparing EXISTING to VOCAB |

:::

### Examples

```bash
# Basic validation
voc4cat check --config idranges.toml myvocab.ttl

# List available profiles
voc4cat check --listprofiles

# Validate with specific profile
voc4cat check --config idranges.toml --profile vocpub myvocab.ttl

# Only fail on violations (ignore warnings)
voc4cat check --config idranges.toml --fail-at-level 3 myvocab.ttl

# CI pre-merge check
voc4cat check --config idranges.toml --ci-pre inbox/ vocabularies/

# CI post-merge check
voc4cat check --config idranges.toml --ci-post existing/ vocabularies/
```

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

Generate blank Excel templates.

```bash
voc4cat template [options] [VOCAB]
```

### Arguments & Options

:::{table}
:align: left

| Argument | Description |
|----------|-------------|
| `VOCAB` | Used as filename (VOCAB.xlsx) |

:::

:::{table}
:align: left

| Option | Description |
|--------|-------------|
| `--version {v1.0}` | Template version (default: v1.0) |

:::

### Examples

```bash
# Generate template from config
voc4cat template --config idranges.toml --outdir .

# Explicit version
voc4cat template --config idranges.toml --version v1.0 --outdir .
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
| `VOC4CAT_VERSION` | Version string to embed in converted vocabularies |
| `NO_COLOR` | Disable colored output when set |

:::

## Exit codes

:::{table}
:align: left

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, file not found, etc.) |

:::
