# File templates

## Vocabulary configuration file template "idranges.toml"

The `idranges.toml` file configures vocabulary management. Key features:

- **ID ranges**: Pre-allocate ranges of concept IDs to specific contributors
- **Contributor info**: ORCID, GitHub username, and optionally ROR ID per contributor
- **Vocabulary metadata**: Title, description, creator, publisher, etc. (v1.0+)

### Version 1.0

The v1.0 format (`config_version = "v1.0"`) adds vocabulary metadata to the config file.
ConceptScheme metadata is now managed in `idranges.toml` and shown as read-only in xlsx.

### Older versions (voc4cat-tool <= 0.10.0)

Older config files lack the `config_version` field and do not include vocabulary metadata.
See [v0.10.0](https://github.com/nfdi4cat/voc4cat-tool/tree/v0.10.0/src/voc4cat/templates/vocab) for an example.

## Excel templates

### Version 1.0

The v1.0 xlsx template is dynamically created and no longer stored in git.
Use the `voc4cat template` command to generate one.

For details on the v1.0 format changes, see [issue #124](https://github.com/nfdi4cat/voc4cat-tool/issues/124).

### Version 0.4.3 (voc4cat-tool <= 0.10.0)

The 0.4.3 template was distributed with git and matched the [VocExcel](https://github.com/rdflib/VocExcel) structure.
See [v0.10.0](https://github.com/nfdi4cat/voc4cat-tool/tree/v0.10.0/src/voc4cat/templates/vocab) for the last version.
