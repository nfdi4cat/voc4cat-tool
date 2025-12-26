[![DOI](https://zenodo.org/badge/598213054.svg)](https://zenodo.org/badge/latestdoi/598213054)
[![](https://github.com/nfdi4cat/voc4cat-tool/workflows/CI/badge.svg)](https://github.com/nfdi4cat/voc4cat-tool/actions)
[![PyPI - Version](https://img.shields.io/pypi/v/voc4cat)](https://pypi.org/project/voc4cat)

# SKOS vocabulary management with GitHub & Excel

## Overview

For **[voc4cat](https://github.com/nfdi4cat/voc4cat)**, a term collection for catalysis created in [NFDI4Cat](https://www.nfdi4cat.org), we developed a **toolbox for collaboratively maintaining SKOS vocabularies on GitHub using Excel** (xlsx-files) as user-friendly interface. It consists of several parts:

- **voc4cat-tool** (this package)
  - A command-line tool to convert vocabularies from Excel/xlsx to SKOS (turtle/rdf) and validate the vocabulary. Validation includes formal validation with SHACL-profiles but also additional checks. The `voc4cat` tool can be run locally but is also well suited for integration in CI-pipelines. It was inspired by [RDFlib/VocExcel](https://github.com/nfdi4cat/VocExcel). Parts of the vocexcel code base were merged into this repository (see git history).
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)**
  - A github project template for managing SKOS-vocabularies using a GitHub-based workflows including automation by gh-actions.
- **[voc4cat](https://github.com/nfdi4cat/voc4cat)**
  - A SKOS vocabulary for the catalysis disciplines that uses the voc4cat workflow for real work.

## Command-line tool voc4cat

voc4cat was mainly developed to be used in gh-actions but it is also useful as a locally installed command line tool. It has the following features.

- Convert between SKOS-vocabularies in Excel/xlsx format and rdf-format (turtle) in both directions.
- Check/validate SKOS-vocabularies in rdf/turtle format with the [vocpub](https://w3id.org/profile/vocpub) SHACL-profile.
- Manage vocabulary metadata (title, description, creator, publisher, etc.) via configuration file.
- Extract provenance information from git history (created, updated).
- Allocate ID ranges to contributors and track their contributions.
- Check xlsx vocabulary files for errors or incorrect use of IDs (voc4cat uses pydantic for this validation).
- Generate documentation from SKOS/turtle vocabulary file using [pyLODE](https://github.com/RDFLib/pyLODE).

### Installation

voc4cat is platform independent and works on windows, linux and mac. It requires Python (3.10 or newer).

If you only want to use the command line interface it is strongly suggested to install with [uv tool](https://docs.astral.sh/uv/concepts/tools/) or [pipx](https://pypa.github.io/pipx/).
Both simplify installing and managing python command line applications.

```bash
uv tool install voc4cat
```

or

```bash
pipx install voc4cat
```

To validate the successful installation, run

```bash
voc4cat --version
```

The available commands and options can be explored via the help system:

```bash
voc4cat --help
```

Optionally you may install the "assistant" which uses [sentence-transformers](https://sbert.net/) for concept similarity analysis.
This adds >100 MB to the download so we don't include it in the default installer.
To include it modify the command (for uv tool) to

```bash
uv tool install "voc4cat[assistant]"
```

Alternatively you can `pip`-install voc4cat like any other Python package.

To install including all development tools use `pip install .[dev]`.

### Getting started

See the [Documentation](https://nfdi4cat.github.io/voc4cat-tool/) for detailed guidance.

To create a new vocabulary, first set up a configuration file `idranges.toml` for your vocabulary (see [example](https://nfdi4cat.github.io/voc4cat-tool/user-guide/project-setup.html#initial-configuration)).
This file defines vocabulary metadata and ID ranges for contributors.
Then create an xlsx-template:

```bash
voc4cat template --config myvocab/idranges.toml --outdir myvocab/
```

This creates `myvocab.xlsx` (named after your vocabulary) with the structure for entering concepts.

Convert the vocabulary file from xlsx to SKOS/turtle format:

```bash
voc4cat convert --config myvocab/idranges.toml myvocab/myvocab.xlsx
```

A turtle file `myvocab.ttl` is created in the same directory.

The reverse is also possible. Create an xlsx file from a turtle vocabulary:

```bash
voc4cat convert --config myvocab/idranges.toml --outdir myvocab/ myvocab/myvocab.ttl
```

## Migrating from older versions

Vocabularies created with voc4cat-tool v0.10.x or earlier (format "043") can be converted to the v1.0 format.
See [migrating to v1.0](https://nfdi4cat.github.io/voc4cat-tool/migration-to-v1.0.html) for details.

## Feedback and code contributions

We highly appreciate your feedback. Please create an [issue on GitHub](https://github.com/nfdi4cat/voc4cat-tool/issues).

Before you contribute code, we suggest to first create an issue to get early feedback on your ideas before you spend too much time.

By contributing you agree that your contributions fall under the project´s BSD-3-Clause [license](LICENSE).

## Contributors

For details see the [Zenodo record](https://doi.org/10.5281/zenodo.8277925).

**A big thanks to our GitHub contributors:**

<a href="https://github.com/nfdi4cat/voc4cat/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=nfdi4cat/voc4cat-tool" alt="Voc4Cat-tool contributors"/>
</a>

*Figure made with [contrib.rocks](https://contrib.rocks).*

## Acknowledgement

This work was funded by the German Research Foundation (DFG) through the project "[NFDI4Cat](https://www.nfdi4cat.org) - NFDI for Catalysis-Related Sciences" (DFG project no. [441926934](https://gepris.dfg.de/gepris/projekt/441926934)), within the National Research Data Infrastructure ([NFDI](https://www.nfdi.de)) programme of the Joint Science Conference (GWK).

This project includes the [vocpub](https://w3id.org/profile/vocpub) SHACL profile, which is licensed under the Creative Commons Attribution 4.0 International License (CC-BY 4.0) and was created by [Nicholas J. Car](https://github.com/nicholascar).
A copy of the license can be found at: https://creativecommons.org/licenses/by/4.0/.
