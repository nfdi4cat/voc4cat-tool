# Running Workflows Locally

The voc4cat-template includes a `justfile` with the same commands as used in GitHub Actions.
This enables running the actions workflows locally on your machine exactly as they are run in GitHub actions,
which is very useful to

- debug workflow issues
- test and develop voc4cat-tool code
- test migrating to a new version

## Prerequisites

- **[just](https://github.com/casey/just)** - A command runner (like make, but simpler)
- **[uv](https://docs.astral.sh/uv/)** - A fast Python package manager

### Installing uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installing just

`just` is available via [PyPI](https://pypi.org/project/rust-just/). So we can use UV (or pipx) to install

```bash
uv tool rust-just
```

Alternatively, you can download from just's GitHub [releases](https://github.com/casey/just/releases) page.

## Available commands

From the root of a voc4cat-template based repository, run `just` to see available commands:

```bash
$ just
Available recipes:
    all     # Run all steps as in gh-actions: check xlsx, convert to SKOS, build docs, re-build xlsx
    check   # Check the xlsx file in inbox/ for errors
    clean   # Remove all generated files/directories
    convert # Convert the xlsx file in inbox/ to turtle
    docs    # Run voc4cat (build HTML documentation from ttl files)
    setup   # Run initial setup (run this first)
    update  # Updates voc4cat-tool installation
    xlsx    # Rebuild the xlsx file from the joined ttl file
```

### Command descriptions

:::{table}
:align: left

| Command | Description |
|---------|-------------|
| `just setup` | Initial setup - creates virtual environment and installs voc4cat |
| `just check` | Validate xlsx files in `inbox-excel-vocabs/` |
| `just convert` | Convert xlsx to turtle format |
| `just docs` | Generate HTML documentation from turtle files |
| `just xlsx` | Rebuild xlsx from turtle (round-trip test) |
| `just all` | Run the complete pipeline (check → convert → docs → xlsx) |
| `just clean` | Remove generated files and directories |
| `just update` | Update voc4cat-tool to the latest version |

:::

## Typical local workflow

### First-time setup

```bash
# Clone your vocabulary repository
git clone https://github.com/yourorg/your-vocabulary.git
cd your-vocabulary

# Run initial setup
just setup
```

No environment variables need to be set manually.
The justfile automatically creates `_main_branch/` and copies `idranges.toml` when running `just check` or `just convert`.

:::{tip}
For verbose output, set `LOGLEVEL=DEBUG` before running commands:

```bash
export LOGLEVEL=DEBUG  # Linux/macOS
set LOGLEVEL=DEBUG     # Windows cmd
```
:::

### Testing changes

1. Place your modified xlsx file in `inbox-excel-vocabs/`
2. Run the full pipeline:

  ```bash
  just all
  ```

3. Review the output:
   - Check console for validation errors
   - Inspect the intermediate files and HTML documentation in `outbox/`
   - Inspect generated turtle files in `vocabularies/`

## Troubleshooting

### idranges comparison with main branch

In CI, the workflow prevents unauthorized modification of `idranges.toml` by comparing it against the main branch version.
The justfile automatically creates `_main_branch/` and copies your local `idranges.toml` there.

:::{note}
The automatic setup copies your *current* `idranges.toml`.
If you're testing changes to `idranges.toml` itself and want to simulate exact CI behavior, manually copy the main branch version:

```bash
git show main:idranges.toml > _main_branch/idranges.toml
```
:::

### Virtual environment issues

If you encounter Python environment issues:

```bash
just clean
just setup
```

This removes the existing environment and creates a fresh one.

## See also

- {doc}`contributing` - Full contribution workflow
- {doc}`../reference/cli` - Complete CLI reference
- {doc}`maintaining` - Maintainer guide (includes local testing)
