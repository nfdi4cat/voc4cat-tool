# Schemas

Technical specifications for configuration and xlsx template formats.

## Configuration (idranges.toml)

The `idranges.toml` file is the central configuration for vocabulary projects.
It defines metadata, settings, and contributor ID ranges for one or more vocabluaries.
This general information is specified via a configuration file, because it should not be editable via xlsx.

### Structure overview

```toml
config_version = "v1.0"     # Required
single_vocab = true         # Optional (default: true)

[vocabs.VOCAB_NAME]
id_length = 6               # Required
permanent_iri_part = "..."  # Required

# ConceptScheme metadata
vocabulary_iri = "..."      # Required
title = "..."               # Required
description = "..."         # Required
created_date = "YYYY-MM-DD" # Required
creator = "..."             # Required
repository = "..."          # Required

# Optional metadata
prefix = "..."
publisher = "..."
custodian = "..."
homepage = "..."
catalogue_pid = "..."
documentation = "..."
issue_tracker = "..."
helpdesk = "..."
conforms_to = "..."

[vocabs.VOCAB_NAME.checks]       # Required section
allow_delete = false

[vocabs.VOCAB_NAME.prefix_map]   # Required section
prefix = "namespace"

[[vocabs.VOCAB_NAME.id_range]]
first_id = 1
last_id = 1000
gh_name = "username"
orcid = "0000-0000-0000-0000"  # Optional
name = "Name"           # Optional
ror_id = "..."          # Optional
```

### General settings

:::{table}
:align: left

| Field | Required | Description |
|-------|----------|-------------|
| `config_version` | Yes | Must be `"v1.0"` |
| `single_vocab` | No | `true` (default) for one vocabulary, `false` for multiple |

:::

### Vocabulary settings

Under `[vocabs.VOCAB_NAME]`:

:::{table}
:align: left

| Field | Required | Description |
|-------|----------|-------------|
| `id_length` | Yes | Number of digits in concept IDs (e.g., `6` for IDs like `000001`) |
| `permanent_iri_part` | Yes | Base IRI for concept identifiers |

:::

### ConceptScheme metadata

These fields define vocabulary metadata shown in the Concept Scheme sheet.

**Required fields:**

:::{table}
:align: left

| Field | Description | SKOS/RDF |
|-------|-------------|----------|
| `vocabulary_iri` | IRI identifying the vocabulary | skos:ConceptScheme |
| `title` | Human-readable name | skos:prefLabel |
| `description` | What the vocabulary covers | skos:definition |
| `created_date` | Creation date (YYYY-MM-DD) | dct:created |
| `creator` | Creators: name(s) with identifier(s), newline-separated | dct:creator |
| `repository` | Source repository URL | - |

:::

**Optional fields:**

:::{table}
:align: left

| Field | Description | SKOS/RDF |
|-------|-------------|----------|
| `prefix` | Preferred prefix for CURIEs | - |
| `publisher` | Publishers: name(s) with identifier(s), newline-separated | dct:publisher |
| `custodian` | Custodians: name(s) with identifier(s), newline-separated | - |
| `homepage` | Public website URL | foaf:homepage |
| `catalogue_pid` | DOI or persistent identifier | dct:identifier |
| `documentation` | Documentation URL | - |
| `issue_tracker` | Issue tracker URL | - |
| `helpdesk` | Helpdesk URL | - |
| `conforms_to` | SHACL profile URL | dct:conformsTo |
| `provenance_url_template` | Jinja template for provenance URLs | - |
| `history_note` | Auto-generated if empty from created_date and creator | skos:historyNote |
| `profile_local_path` | Path to local SHACL profile file (relative to idranges.toml) | - |

:::

### Creator and contributor format

For `creator`, `publisher`, and `custodian` fields, use multi-line format with name and identifier:

```toml
creator = """
Alice Smith https://orcid.org/0000-0001-2345-6789
Bob Jones https://orcid.org/0000-0002-3456-7890
"""

publisher = "NFDI4Cat Consortium https://w3id.org/nfdi4cat/"

custodian = """
Vocabulary Curator Group https://github.com/orgs/example/teams/curators
"""
```

### Prefix map (required)

Define namespace prefixes for CURIE expansion:

```toml
[vocabs.myvocab.prefix_map]
myvoc = "https://example.org/myvocab_"
skos = "http://www.w3.org/2004/02/skos/core#"
```

### Checks configuration (required)

Configure validation behavior:

```toml
[vocabs.myvocab.checks]
# Allow concept deletion (useful for CI pipelines)
allow_delete = false
```

### ID ranges

ID ranges allocate concept ID blocks to contributors:

```toml
[[vocabs.myvocab.id_range]]
first_id = 1
last_id = 5000
gh_name = "contributor1"
name = "First Contributor"  # optional
orcid = "0000-0001-2345-6789"
ror_id = "https://ror.org/012345678"  # optional

[[vocabs.myvocab.id_range]]
first_id = 5001
last_id = 6000
gh_name = "contributor2"
orcid = "0000-0002-3456-7890"
```

**ID range fields:**

:::{table}
:align: left

| Field | Required | Description |
|-------|----------|-------------|
| `first_id` | Yes | First ID in range (inclusive) |
| `last_id` | Yes | Last ID in range (inclusive) |
| `gh_name` | Yes* | GitHub username |
| `orcid` | Yes* | ORCID identifier (without URL prefix) |
| `name` | No | Human-readable name |
| `ror_id` | No | ROR identifier for institution |

:::

*At least one of `gh_name` or `orcid` is required.

### Complete example

```toml
config_version = "v1.0"
single_vocab = true

[vocabs.voc4cat]
id_length = 7
permanent_iri_part = "https://w3id.org/nfdi4cat/voc4cat_"

# ConceptScheme metadata
vocabulary_iri = "https://w3id.org/nfdi4cat/voc4cat"
prefix = "voc4cat"
title = "Voc4Cat - A SKOS vocabulary for Catalysis."
description = """The Voc4Cat vocabulary is a collection of concepts from the field
of catalysis and related disciplines."""

created_date = "2023-06-29"

creator = """
David Linke https://orcid.org/0000-0002-5898-1820
Nikolaos Moustakas https://orcid.org/0000-0002-6242-2167
"""

publisher = "NFDI4Cat Consortium https://w3id.org/nfdi4cat/"

custodian = """
Voc4Cat curator group https://github.com/orgs/nfdi4cat/teams/voc4cat-curators
"""

repository = "https://github.com/nfdi4cat/voc4cat"
homepage = "https://nfdi4cat.github.io/voc4cat/"
catalogue_pid = "https://doi.org/10.5281/zenodo.8313340"
documentation = "https://nfdi4cat.github.io/voc4cat/"
issue_tracker = "https://github.com/nfdi4cat/voc4cat/issues"
conforms_to = "https://linked.data.gov.au/def/vocpub/validator/4.7"

[vocabs.voc4cat.checks]
allow_delete = false

[vocabs.voc4cat.prefix_map]
voc4cat = "https://w3id.org/nfdi4cat/voc4cat_"

[[vocabs.voc4cat.id_range]]
first_id = 1
last_id = 5000
gh_name = "nmoust"
name = "Nikolaos Moustakas"
orcid = "0000-0002-6242-2167"
ror_id = "https://ror.org/029hg0311"

[[vocabs.voc4cat.id_range]]
first_id = 5001
last_id = 6000
gh_name = "dalito"
name = "David Linke"
orcid = "0000-0002-5898-1820"
ror_id = "https://ror.org/029hg0311"
```

### Tips

- **Match names**: The vocabulary section name (e.g., `vocabs.voc4cat`) should match your xlsx/ttl filename
- **Plan ID ranges**: Allocate generous ranges to avoid needing to add more later
- **Use ORCIDs**: They provide persistent identification for contributors
- **Keep descriptions updated**: The description appears in generated documentation

---

## Excel/xlsx template (v1.0)

Template version: `v1.0.rev-2025-12a`

The voc4cat v1.0 xlsx vocabularies contain six sheets for entering and viewing vocabulary data.

### Sheets overview

:::{table}
:align: left

| Sheet | Purpose | Editable |
|-------|---------|----------|
| Concept Scheme | Vocabulary metadata | Read-only |
| Concepts | Concept definitions | Yes |
| Collections | Groupings of concepts | Yes |
| Mappings | Links to external vocabularies | Yes |
| ID Ranges | Contributor ID allocations | Read-only |
| Prefixes | Namespace prefix definitions | Read-only |

:::

Any changes in read-only sheets will be ignored.

### Concept Scheme sheet

This sheet displays vocabulary metadata from your `idranges.toml` configuration and dynamically generated data.
It is read-only in xlsx. Edit the configuration file to change these values.

### Concepts sheet

The main sheet where you define vocabulary concepts. Each row represents one concept in one language.

**Required columns** (marked with `*`):

:::{table}
:align: left

| Column | Description | SKOS mapping | Example |
|--------|-------------|--------------|---------|
| Concept IRI* | Unique identifier | - | `voc4cat:0001234` |
| Language Code* | ISO language code | - | `en`, `de` |
| Preferred Label* | Main name | skos:prefLabel | `Catalyst` |
| Definition* | What the concept means | skos:definition | `A substance that...` |

:::

**Optional columns:**

:::{table}
:align: left

| Column | Description | SKOS mapping |
|--------|-------------|--------------|
| Alternate Labels | Synonyms (comma-separated) | skos:altLabel |
| Parent IRIs | Broader concepts (comma-separated) | skos:broader |
| Member of collection(s) | Collection memberships (comma-separated) | skos:member |
| Member of ordered collection # position | Position in ordered collection | - |
| Provenance | Origin of concept (read-only) | dct:provenance |
| Change Note | Documentation of changes | skos:changeNote |
| Editorial Note | Internal notes | skos:editorialNote |
| Obsoletion reason | Why deprecated | owl:deprecated |
| Influenced by IRIs | Related external concepts (comma-separated) | prov:wasInfluencedBy |
| Source Vocab IRI or URL | Original source | prov:hadPrimarySource |
| Source Vocab License | License of source | dct:license |
| Source Vocab Rights Holder | Rights holder of source | dct:rightsHolder |

:::

**Multi-language support:**

To define a concept in multiple languages, create one row per language with the same Concept IRI:

:::{table}
:align: left

| Concept IRI | Language Code | Preferred Label | Definition |
|-------------|---------------|-----------------|------------|
| voc4cat:0001001 | en | Catalyst | A substance that increases... |
| voc4cat:0001001 | de | Katalysator | Ein Stoff, der die... |

:::

**Hierarchies:**

Express parent-child relationships using the "Parent IRIs" column:

:::{table}
:align: left

| Concept IRI | Preferred Label | Parent IRIs |
|-------------|-----------------|-------------|
| voc4cat:0001001 | Catalyst | |
| voc4cat:0001002 | Heterogeneous catalyst | voc4cat:0001001 |
| voc4cat:0001003 | Homogeneous catalyst | voc4cat:0001001 |

:::

Multiple parents are supported (comma-separated).

**Deprecating concepts:**

To mark a concept as obsolete, select a reason from the "Obsoletion reason" dropdown:

- The concept is not clearly defined and usage has been inconsistent.
- This concept was added in error.
- More specific concepts were created.
- This concept was converted to a collection.
- The meaning of the concept is ambiguous.
- Lack of evidence that this function/process/component exists.

Deprecated concept are marked in RDF with `owl:deprecated`.

### Collections sheet

Collections group related concepts together without implying hierarchy.
Members are assigned to collections in the Concepts sheet via the "Member of collection(s)" column.

:::{table}
:align: left

| Column | Description | SKOS mapping | Default |
|--------|-------------|--------------|---------|
| Collection IRI* | Unique identifier for the collection | - | |
| Language Code* | ISO language code | - | |
| Preferred Label* | Name of the collection | skos:prefLabel | |
| Definition* | What the collection contains | skos:definition | |
| Parent Collection IRIs | Nest collections within other collections (comma-separated) | skos:member | |
| Ordered? | "Yes" for ordered collection, blank for unordered | - | No |
| Change Note | Documentation of changes | skos:changeNote | |
| Editorial Note | Internal notes | skos:editorialNote | |
| Obsoletion reason | Why deprecated | owl:deprecated | |

:::

*Required columns are marked with `*`.

### Mappings sheet

Link your concepts to terms in other vocabularies.

:::{table}
:align: left

| Column | Description | SKOS mapping |
|--------|-------------|--------------|
| Concept IRI* | Your concept | - |
| Related Matches | Loosely related external concepts (comma-separated) | skos:relatedMatch |
| Close Matches | Similar but not identical (comma-separated) | skos:closeMatch |
| Exact Matches | Semantically equivalent (comma-separated) | skos:exactMatch |
| Narrower Matches | More specific external concepts (comma-separated) | skos:narrowMatch |
| Broader Matches | More general external concepts (comma-separated) | skos:broadMatch |
| Editorial Note | Internal notes (not exported to RDF) | - |

:::

### ID Ranges sheet

Read-only sheet showing which concept ID ranges are allocated to each contributor.
This information comes mainly from the `idranges.toml` configuration but is updated with on the current usage of IDs.

### Prefixes sheet

Read-only sheet showing namespace prefix mappings for CURIE expansion.
The prefixes come the `idranges.toml` configuration enriched with the default prefixes from [rdflib](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.namespace/).

### Data formats

- **IRIs**: Full IRI or CURIE (`prefix:id`)
- **Language codes**: ISO 639-1 (`en`, `de`)
- **Dates**: ISO 8601 (`YYYY-MM-DD`)

### Tips

- **Use CURIEs**: Write `voc4cat:0001234` instead of full IRIs for readability
- **Save before converting**: Make sure to save your xlsx file before running `voc4cat convert`
