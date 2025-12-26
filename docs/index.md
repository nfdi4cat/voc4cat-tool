# voc4cat-tool Documentation

A toolbox for collaboratively maintaining SKOS vocabularies on GitHub using Excel (xlsx-files) as a user-friendly interface.

## What is voc4cat-tool?

**voc4cat-tool** is a command-line tool that enables:

- Bidirectional conversion between Excel (xlsx) and SKOS/RDF (turtle) formats
- Validation with SHACL profiles and additional consistency checks
- Vocabulary metadata management via configuration files
- ID range allocation for contributors for opaque URIs
- Extract provenance information from git history
- HTML documentation generation from SKOS/RDF vocabularies

It is part of the voc4cat ecosystem:

- **voc4cat-tool** (this package) - The command-line conversion and validation tool
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)** - GitHub repository template with workflows for collaborative vocabulary projects
- **[voc4cat](https://github.com/nfdi4cat/voc4cat)** - A SKOS vocabulary for catalysis based on the template.

```{toctree}
:hidden:
GitHub page <https://github.com/nfdi4cat/voc4cat-tool>
about
```

```{toctree}
:maxdepth: 2
:caption: Getting Started

getting-started/installation
getting-started/core-principles
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/project-setup
user-guide/contributing
user-guide/maintaining
user-guide/local-development
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/cli
reference/schemas
migration-to-v1.0
changelog
```
