# Running Workflows Locally

How to work with voc4cat tools on your local machine.

TODO: Add why/when running locally is required: Debug workflow issues, test/develop code, test migrations etc.

## Prerequisites

The voc4cat-template includes a `justfile` that runs the same commands used in GitHub Actions locally. You need:

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

Just is available at PyPi. So we can use UV (or pipx) to install

```bash
uv tool rust-just
```

Alternatively, you can download from [releases](https://github.com/casey/just/releases)

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

## Typical local workflow

### First-time setup

```bash
# Clone your vocabulary repository
git clone https://github.com/yourorg/your-vocabulary.git
cd your-vocabulary

# Run initial setup
just setup
```

### Testing changes

1. Place your modified xlsx file in `inbox-excel-vocabs/`
2. Run the full pipeline:

```bash
just all
```

3. Review the output:
   - Check console for validation errors
   - Inspect generated turtle files in `vocabularies/`
   - View HTML documentation in the output directory

## Troubleshooting

### idranges copy?

TODO check if an idranges copy is created as in actions. Comment on env vars. (or are they set in just commands?)

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
