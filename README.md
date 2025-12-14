[![DOI](https://zenodo.org/badge/598213054.svg)](https://zenodo.org/badge/latestdoi/598213054)
[![](https://github.com/nfdi4cat/voc4cat-tool/workflows/CI/badge.svg)](https://github.com/nfdi4cat/voc4cat-tool/actions)
[![PyPI - Version](https://img.shields.io/pypi/v/voc4cat)](https://pypi.org/project/voc4cat)

# SKOS vocabulary management with GitHub & Excel

## Overview

For **[voc4cat](https://github.com/nfdi4cat/voc4cat)**, a term collection for catalysis created in [NFDI4Cat](https://www.nfdi4cat.org), we developed a **toolbox for collaboratively maintaining SKOS vocabularies on GitHub using Excel** (xlsx-files) as user-friendly interface. It consists of several parts:

- **voc4cat-tool** (this package)
  - A command-line tool to convert vocabularies from Excel to SKOS (turtle/rdf) and validate the vocabulary. Validation includes formal validation with SHACL-profiles but also additional checks. The `voc4cat` tool can be run locally but is also well suited for integration in CI-pipelines. It was inspired by [RDFlib/VocExcel](https://github.com/nfdi4cat/VocExcel). Parts of the vocexcel code base were merged into this repository (see git history).
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)**
  - A github project template for managing SKOS-vocabularies using a GitHub-based workflows including automation by gh-actions.
- **[voc4cat](https://github.com/nfdi4cat/voc4cat)**
  - A SKOS vocabulary for the catalysis disciplines that uses the voc4cat workflow for real work.

## Command-line tool voc4cat

voc4cat was mainly developed to be used in gh-actions but it is also useful as a locally installed command line tool. It has the following features.

- Convert between SKOS-vocabularies in Excel/xlsx format and rdf-format (turtle) in both directions.
- Check/validate SKOS-vocabularies in rdf/turtle format with the [vocpub](https://w3id.org/profile/vocpub) SHACL-profile.
- Manage vocabulary metadata (title, description, creator, publisher, etc.) via configuration file.
- Allocate ID ranges to contributors and track their contributions.
- Check xlsx vocabulary files for errors or incorrect use of IDs (voc4cat uses pydantic for this validation).
- Generate documentation from SKOS/turtle vocabulary file using [pyLODE](https://github.com/RDFLib/pyLODE).

voc4cat works on files or folders. If a folder is given all matching files are processed at once.

### Installation requirements

To start you need:

- Python (3.10 or newer)

voc4cat is platform independent and should work at least on windows, linux and mac.

### Installation steps

If you just want to use the command line interface it is strongly suggested to use [pipx](https://pypa.github.io/pipx/) or [uv tool](https://docs.astral.sh/uv/concepts/tools/) for the installation.
Both make installing and managing python command line application very easy.

`pipx install voc4cat`

or

`uv tool install voc4cat`

Alternatively you can `pip`-install voc4cat like any other Python package.

To install including all development tools use `pip install .[dev]` for just the test tools `pip install .[tests]`. For testing we use [pytest](https://docs.pytest.org).

### Typical use

The available commands and options can be explored via the help system:

```bash
voc4cat --help
```

which lists all available sub commands. These have their own help, for example:

```bash
voc4cat transform --help
```

To create a new vocabulary, first set up a configuration file `idranges.toml` for your vocabulary.
This file defines vocabulary metadata and ID ranges for contributors.
Then create an xlsx-template:

```bash
voc4cat template --config myvocab/idranges.toml --outdir myvocab/
```

This creates `myvocab.xlsx` (named after your vocabulary) with the structure for entering concepts.

To express hierarchies in SKOS ("broader"/"narrower") voc4cat uses parent IRIs in the sheet "Concepts".
Enter a list of parent IRIs in the Parent IRIs column to define the concept hierarchy.
Each concept can have zero, one or even multiple parents.

### Configuration file (idranges.toml)

The `idranges.toml` file is central to vocabulary management. It contains:

- **Vocabulary metadata**: Title, description, creator, publisher, and other ConceptScheme properties.
- **ID ranges**: Pre-allocated ranges of concept IDs for each contributor (with ORCID, GitHub username).
- **Vocabulary settings**: ID length, base IRI, prefix mappings.

The xlsx file shows ConceptScheme metadata as read-only information derived from this config.

### Converting vocabularies

Convert the vocabulary file from xlsx to SKOS/turtle format:

```bash
voc4cat convert --config myvocab/idranges.toml myvocab/myvocab.xlsx
```

A turtle file `myvocab.ttl` is created in the same directory.

The reverse is also possible. Create an xlsx file from a turtle vocabulary:

```bash
voc4cat convert --config myvocab/idranges.toml --outdir myvocab/ myvocab/myvocab.ttl
```

In addition to `transform` and `convert` voc4cat offers checking and validation under the sub-command `check` and documentation generation under `docs`.
See the command line help for details.

For maintainers a tool for similarity checks is provided which is based on sentence-transformer model to identify similar preferred labels and definitions.
It also performs other consistency checks. The tool can either check a single vocabulary

`voc-assistant check voc4cat.ttl`

or compare the additions made against existing concepts:

`voc-assistant compare voc4cat.ttl voc4cat_new.ttl`

It creates reports in markdown format.

## Migrating from older versions

Vocabularies created with voc4cat-tool v0.10.0 or earlier (format "043") can be converted to the v1.0 format.
See [docs/migration-to-v1.0.md](docs/migration-to-v1.0.md) for details.

## Feedback and code contributions

We highly appreciate your feedback. Please create an [issue on GitHub](https://github.com/nfdi4cat/voc4cat-tool/issues).

If you plan to contribute code, we suggest to also create an issue first to get early feedback on your ideas before you spend too much time.

By contributing you agree that your contributions fall under the project´s BSD-3-Clause [license](LICENSE).

## Acknowledgement

This work was funded by the German Research Foundation (DFG) through the project "[NFDI4Cat](https://www.nfdi4cat.org) - NFDI for Catalysis-Related Sciences" (DFG project no. [441926934](https://gepris.dfg.de/gepris/projekt/441926934)), within the National Research Data Infrastructure ([NFDI](https://www.nfdi.de)) programme of the Joint Science Conference (GWK).

This project uses the [vocpub](https://w3id.org/profile/vocpub) SHACL profile, which is licensed under the Creative Commons Attribution 4.0 International License (CC-BY 4.0).
The original work was created by [Nicholas J. Car](https://github.com/nicholascar).
A copy of the license can be found at: https://creativecommons.org/licenses/by/4.0/.
Changes were made to the original work for this project.
