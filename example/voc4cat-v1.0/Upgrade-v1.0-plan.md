# Upgrade Plan: voc4cat 043 to v1.0

## Source
- **Directory:** `example/voc4cat-043/`
- **RDF file:** `voc4cat.ttl` (DO NOT MODIFY)
- **Config:** `idranges.toml` (pre-v1.0, no `config_version` field)
- **Metadata:** `zenodo.json` (contributor names)

## Target
- **Directory:** `example/voc4cat-v1.0/`

---

## Upgrade Steps

The source vocabulary was created with voc4cat v0.10.0 and has the "043" version.

### Step 1: Create v1.0 idranges.toml in target directory

Create `example/voc4cat-v1.0/idranges.toml` by:

1. Start with the v1.0 template: `src/voc4cat/templates/vocab/idranges.toml`
2. Set `config_version = "v1.0"`
3. Copy structural data from source `idranges.toml`:
   - `id_length = 7`
   - `permanent_iri_part = "https://w3id.org/nfdi4cat/voc4cat_"`
   - `prefix_map`: `voc4cat = "https://w3id.org/nfdi4cat/voc4cat_"`
   - `checks.allow_delete = false`
   - All `[[vocabs.voc4cat.id_range]]` entries
4. Add `name` field to id_range entries using names from `zenodo.json`
5. Fill in ConceptScheme metadata fields extracted from the TTL file

**Metadata to extract from `voc4cat.ttl`:**

| v1.0 Config Field | TTL Property | Value |
|-------------------|--------------|-------|
| `vocabulary_iri` | (subject IRI) | `https://w3id.org/nfdi4cat/voc4cat` |
| `prefix` | - | `voc4cat` |
| `title` | `skos:prefLabel` | `Voc4Cat - A SKOS vocabulary for Catalysis.` |
| `description` | `skos:definition` | (multi-line definition text) |
| `created_date` | `dcterms:created` | `2023-06-29` |
| `creator` | `dcterms:creator` | `https://w3id.org/nfdi4cat/` |
| `publisher` | `dcterms:publisher` | `https://w3id.org/nfdi4cat/` |
| `custodian` | `dcat:contactPoint` | (see below) |
| `repository` | (not in TTL) | `https://github.com/nfdi4cat/voc4cat` |
| `homepage` | - | `https://nfdi4cat.github.io/voc4cat/` |

**Important notes:**
- `creator` and `publisher`: Use just the URI (e.g., `https://w3id.org/nfdi4cat/`) if that's what the original TTL has. Do NOT use `"Name URL"` format with a space if the original was a URI reference.
- `custodian`: Convert from `dcat:contactPoint` format. Each line should be `<name> <orcid-URL>`:
  ```
  David Linke https://orcid.org/0000-0002-5898-1820
  Nikolaos Moustakas https://orcid.org/0000-0002-6242-2167
  ```
- `modified_date` and `version`: Not stored in config (auto-generated fields from RDF only)

**Name mappings from zenodo.json to add to id_range entries:**

| gh_name | ORCID | name |
|---------|-------|------|
| nmoust | 0000-0002-6242-2167 | Nikolaos Moustakas |
| dalito | 0000-0002-5898-1820 | David Linke |
| markdoerr | 0000-0003-3270-6895 | Mark Doerr |
| schumnannj | 0000-0002-4041-0165 | Julia Schumann |
| RoteKekse | 0009-0008-1278-8890 | Michael Goette |
| HendrikBorgelt | 0000-0001-5886-7860 | Hendrik Borgelt |
| kara-mela | 0000-0002-5850-4469 | Melanie Nentwich |
| carla-terboven | 0009-0004-3786-0773 | Carla Terboven |
| FranziFlecken | 0000-0003-4418-7455 | Franziska Flecken |

Contributors not in zenodo.json can omit the `name` field.

---

### Step 2: Run 043-to-v1.0 RDF conversion

```bash
voc4cat convert --from 043 --config example/voc4cat-v1.0/idranges.toml --outdir example/voc4cat-v1.0 example/voc4cat-043/voc4cat.ttl
```

This outputs `voc4cat.ttl` in v1.0 RDF format with:
- `skos:historyNote` converted to `skos:changeNote`
- ConceptScheme metadata enriched from `idranges.toml`

**Note:** The output filename is derived from the vocab name in the config (`[vocabs.voc4cat]`).

---

### Step 3: Generate v1.0 Excel template

```bash
voc4cat convert --config example/voc4cat-v1.0/idranges.toml --outdir example/voc4cat-v1.0 example/voc4cat-v1.0/voc4cat.ttl
```

This outputs `voc4cat.xlsx` with:
- All concepts and collections from TTL
- ID Ranges sheet populated from config
- Contributors auto-derived from ID range usage

---

### Step 4: Verify the output

Check the following:
- [ ] `voc4cat.ttl` contains all concepts from source (should be 540)
- [ ] `voc4cat.ttl` contains all collections from source (should be 6)
- [ ] ConceptScheme metadata is correctly set from `idranges.toml`
- [ ] Excel ID Ranges sheet shows all contributors with their ranges
- [ ] Excel Concept Scheme sheet shows contributor field (auto-derived)

**Verification commands:**
```bash
# Count concepts
grep -c "a skos:Concept" example/voc4cat-v1.0/voc4cat.ttl
# Expected: 540

# Count collections
grep -c "a skos:Collection" example/voc4cat-v1.0/voc4cat.ttl
# Expected: 6

# View ConceptScheme
grep -A 30 "a skos:ConceptScheme" example/voc4cat-v1.0/voc4cat.ttl
```

---

### Step 5: Validate roundtrip

Convert Excel back to TTL and compare:

```bash
# Save step 2 output for comparison
cp example/voc4cat-v1.0/voc4cat.ttl example/voc4cat-v1.0/voc4cat_reference.ttl

# Convert xlsx to ttl
voc4cat convert \
  --config example/voc4cat-v1.0/idranges.toml \
  --outdir example/voc4cat-v1.0 \
  example/voc4cat-v1.0/voc4cat.xlsx

# Compare (will show serialization differences, not semantic differences)
diff example/voc4cat-v1.0/voc4cat_reference.ttl example/voc4cat-v1.0/voc4cat.ttl
```

**Expected differences (acceptable):**
- CURIE vs full URI serialization (e.g., `voc4cat:0000016` vs `<https://w3id.org/nfdi4cat/voc4cat_0000016>`)
- Prefix declarations may differ
- Triple count may differ slightly (5130 vs 5127) due to serialization

**Semantic equivalence:** Concept/collection counts must match.

---

## Checklist

- [ ] Step 1: Create v1.0 `idranges.toml` with metadata and name fields
- [ ] Step 2: Convert 043 TTL to v1.0 TTL
- [ ] Step 3: Generate v1.0 Excel
- [ ] Step 4: Verify output (540 concepts, 6 collections)
- [ ] Step 5: Validate roundtrip
- [ ] Clean up temporary files (e.g., `voc4cat_reference.ttl`)
