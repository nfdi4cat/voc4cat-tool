# Migrating from 043 to v1.0 format

This guide explains how to migrate vocabularies created with voc4cat-tool v0.10.0 or earlier to the v1.0 format.

## What changed in v1.0

- **Configuration file**: The `idranges.toml` now includes a `config_version = "v1.0"` field and stores all vocabulary metadata (title, description, creator, publisher, etc.).
- **ConceptScheme metadata**: No longer editable in xlsx; managed via `idranges.toml` and shown as read-only in Excel.
- **RDF changes**: `skos:historyNote` converted to `skos:changeNote`.
- **Excel template**: Dynamically generated based on config; no longer distributed as a static file.

## Migration steps

### Step 1: Create a v1.0 idranges.toml

Start with the template from `src/voc4cat/templates/vocab/idranges.toml` and fill in:

1. Set `config_version = "v1.0"`
2. Copy structural data from your existing idranges.toml (id_length, permanent_iri_part, prefix_map, id_ranges)
3. Add vocabulary metadata extracted from your TTL file's ConceptScheme:
   - `vocabulary_iri`, `prefix`, `title`, `description`
   - `created_date`, `creator`, `publisher`, `custodian`
   - `repository`, `homepage` (if applicable)

### Step 2: Convert RDF from 043 to v1.0

```bash
voc4cat convert --from 043 --config path/to/v1.0/idranges.toml --outdir output/ source/vocab.ttl
```

This converts `skos:historyNote` to `skos:changeNote` and enriches the ConceptScheme with metadata from the config.

### Step 3: Generate v1.0 Excel template

```bash
voc4cat convert --config path/to/v1.0/idranges.toml --outdir output/ output/vocab.ttl
```

This creates the xlsx file with all concepts, collections, and the new v1.0 structure.

### Step 4: Verify the output

Check that:
- Concept and collection counts match the source
- ConceptScheme metadata is correctly set
- Excel ID Ranges sheet shows all contributors

```bash
# Count concepts
grep -c "a skos:Concept" output/vocab.ttl

# Count collections
grep -c "a skos:Collection" output/vocab.ttl
```

## Notes

- The `dcterms:modified` and `owl:versionInfo` fields are auto-generated and not stored in the config.
- Contributors in id_range entries can have an optional `name` field for display purposes.
