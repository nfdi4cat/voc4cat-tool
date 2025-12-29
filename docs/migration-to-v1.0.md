# Migrating from 043 to v1.0

This guide explains how to migrate vocabularies created with voc4cat-tool v0.10.x (xlsx template "0.43") to the v1.0 format.

## What changed in v1.0

- **Configuration file**: The `idranges.toml` now includes a `config_version = "v1.0"` field and stores all vocabulary metadata (title, description, creator, publisher, etc.).
- **ConceptScheme metadata**: No longer editable in xlsx; managed via `idranges.toml` and shown as read-only in Excel.
- **RDF changes**: `skos:historyNote` converted to `skos:changeNote`.
- **Excel template**: Dynamically generated based on config; no longer distributed as a static file.

## Migration steps

### Step 0: Upgrade to latest release of voc4cat-template

If you based your repository on voc4cat-template, update to its latest release first (See {ref}`keeping-in-sync-with-the-template`).

### Step 1: Create a v1.0 idranges.toml

Start with the template from `src/voc4cat/templates/vocab/idranges.toml` and fill in:

1. Structural data from your existing idranges.toml (id_length, permanent_iri_part, prefix_map, id_ranges)
2. Add vocabulary metadata extracted from your TTL file's ConceptScheme:
   - `vocabulary_iri`, `prefix`, `title`, `description`
   - `created_date`, `creator`, `publisher`, `custodian`
   - `repository`, `homepage` (if applicable)

The `idrange.toml` files now include a mandatory version number (`config_version = "v1.0"`) to help with future updates.

### Step 2: Convert RDF from 043 to v1.0

**Step 2a** Convert RDF to new v1.0 format

This requires a turtle file `vocab.ttl` containing the current version of the complete vocabulary.

```bash
voc4cat convert --from 043 --config path/to/v1.0/idranges.toml --outdir outbox/ source/vocab.ttl
```

In this step the ConceptScheme is also enriched with metadata from the config.

**Step 2b**

Split the v1.0 vocab.ttl from step 2a into individual version-tracked RDF files.

```bash
voc4cat transform --split --config path/to/v1.0/idranges.toml --logfile outbox/voc4cat.log -O vocabularies/ outbox/
```

This command assumes that your version-tracked files are stored in the `vocabularies/` folder which is the default for `voc4cat-template`-based repositories.

**Step 2c**

Add provenance info based on git history (dct:created and dct:updated) to the split RDF files from step 2b.

```bash
voc4cat transform --prov-from-git --inplace --config path/to/v1.0/idranges.toml --logfile outbox/voc4cat.log vocabularies/
```

**Step 2d**

Create a provenance-enriched new "joined" vocab.ttl file from the individual RDF files from step 2c.

```bash
voc4cat transform --join --config path/to/v1.0/idranges.toml --logfile outbox/voc4cat.log -O outbox/ vocabularies/
```

(step-3-generate-v1-0-excel-template)=
### Step 3: Generate v1.0 Excel template

With voc4cat-tool 1.0.0, all required sheets in the xlsx template are dynamically generated.

**A template is no longer mandatory.** You may still use a template to provide a Help-sheet for your users.
The voc4cat-tool CLI can inject the generated sheets into any given xlsx-template.

To convert your old template, delete all sheets that are now auto-generated:

- Concept Scheme
- Concepts
- Additional Concept Features
- Collections
- Prefix Sheet

To generate the xlsx-representation of your vocabulary run

```bash
voc4cat convert --config path/to/v1.0/idranges.toml --outdir outbox/ outbox/vocab.ttl
```

If you want to use an xlsx-template, the command to run is

```bash
voc4cat convert --config path/to/v1.0/idranges.toml --template templates/your-template.xlsx --outdir outbox/ outbox/vocab.ttl
```

### Step 4: Verify the output

Check that:

- Concept and collection counts match the source
- ConceptScheme metadata is correctly set
- Excel ID Ranges sheet shows all contributors

## Notes

- The `dcterms:modified` and `owl:versionInfo` fields are auto-generated and not stored in the config.
- Contributors in id_range entries can have an optional `name` field in v1.0 for display purposes.
