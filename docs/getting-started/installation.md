# Installation & Quickstart

voc4cat requires Python 3.10 or newer and works on Windows, Linux, and macOS.

## Installation

For command-line use, we recommend [pipx](https://pypa.github.io/pipx/) or [uv tool](https://docs.astral.sh/uv/concepts/tools/):

```bash
# Using pipx
pipx install voc4cat

# Using uv
uv tool install voc4cat
```

Of course, you can also use pip the standard Python package manager.

```bash
pip install voc4cat
```

To verify the installation, run voc4cat´s command line interface

```bash
voc4cat --version
voc4cat --help
```

which shows the installed version and the command line help.

## Quickstart: Your first vocabulary

### Step 1: Create configuration

Create a directory and configuration file `idranges.toml` for a vocabulary named `myvoc`:

```bash
mkdir myvocab && cd myvocab
```

```toml
config_version = "v1.0"

[vocabs.myvocab]
id_length = 6
permanent_iri_part = "https://example.org/myvocab_"
vocabulary_iri = "https://example.org/myvocab"
prefix = "myvoc"
title = "My First Vocabulary"
description = "A sample SKOS vocabulary"
created_date = "2025-08-31"
creator = "Your Name"
publisher = "Your Organization https://ror.org/012345678"
repository = "https://github.com/yourorg/myvocab"

[vocabs.myvocab.checks]
allow_delete = false

[vocabs.myvocab.prefix_map]
myvoc = "https://example.org/myvocab_"

[[vocabs.myvocab.id_range]]
first_id = 1
last_id = 999
gh_name = "your-github-username"
orcid = "https://orcid.org/0000-0001-2345-6789"
```

### Step 2: Generate template

Generate an xlsx template in the current directory (use `--outdir` to write to a specific directory)

```bash
voc4cat template --config idranges.toml myvocab
```

### Step 3: Add concepts

Open `myvocab.xlsx`, go to the **Concepts** sheet, and add:

| Concept IRI | Language Code | Preferred Label | Definition | Parent IRIs |
|-------------|---------------|-----------------|------------|-------------|
| myvoc:000001 | en | Animal | A living organism that can move and respond to its environment | |
| myvoc:000002 | en | Cat | A small furry animal that says meow and rules the household | myvoc:000001 |

### Step 4: Convert to SKOS

```bash
voc4cat convert --config idranges.toml myvocab.xlsx
```

This creates `myvocab.ttl` containing your vocabulary in SKOS format.

### Step 5: Validate against vocpub profile

```bash
voc4cat check --config idranges.toml myvocab.ttl
```

With this minimal configuration, the check will report several **violations**. This is expected and demonstrates what the vocpub profile requires for a complete vocabulary:

- **creator**: Must be an IRI (ORCID or ROR ID), not just a name
- **empty collection**: The template includes an example collection that needs members or should be deleted

To make the check pass:

1. Update `idranges.toml` with valid creator:

   ```toml
   creator = "Your Name https://orcid.org/0000-0001-2345-6789"
   ```

2. In the xlsx file:
   - Either delete the example collection in the **Collections** sheet, or add members to it

## Next steps

- {doc}`core-principles` - Understand SKOS and the voc4cat approach
- {doc}`../reference/schemas` - Configuration and Excel format specifications
