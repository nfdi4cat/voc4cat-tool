# Core Principles

Understanding SKOS and the voc4cat approach.

## What is SKOS?

[SKOS](https://www.w3.org/TR/skos-reference/) (Simple Knowledge Organization System) is a W3C standard for representing vocabularies, taxonomies, thesauri, and other knowledge organization systems. It provides a way to express:

- **Concepts** - The terms/ideas in your vocabulary
- **Labels** - Human-readable names in multiple languages
- **Relationships** - How concepts relate to each other (broader/narrower/related)
- **Documentation** - Definitions, notes, and examples

## Key SKOS elements

### Concept Scheme

A Concept Scheme is the container for your vocabulary. It has metadata like title, description, creator, and version.

In voc4cat, the Concept Scheme metadata is defined in your `idranges.toml` configuration file.

### Concepts

Concepts are the core elements - the terms you're defining. Each concept has:

- **IRI** - A unique identifier (e.g., `https://example.org/myvocab/000001`)
- **Preferred Label** - The main name in each language
- **Alternative Labels** - Synonyms or variant names
- **Definition** - What the concept means
- **Scope Note** - Usage guidance or context

### Hierarchies (Broader/Narrower)

SKOS concepts can form hierarchies:

- **Broader** - A more general concept (parent)
- **Narrower** - A more specific concept (child)

Example:
```
Catalyst (broader)
├── Heterogeneous catalyst (narrower)
└── Homogeneous catalyst (narrower)
```

In the xlsx templates, you express this by listing "Parent IRIs" for each concept.

### Related concepts

Concepts can also have non-hierarchical relationships using `skos:related`.

## The voc4cat approach

### Excel as interface

voc4cat uses Excel/xlsx spreadsheets as a user-friendly interface for editing vocabularies:

- Familiar to most users
- Easy data entry and review
- Works offline
- Can be edited collaboratively (with proper workflow)

### RDF/Turtle as storage

Vocabularies are stored as RDF in turtle format (`.ttl` files):

- Standard semantic web format
- Version control friendly
- Machine-readable
- Interoperable with other tools

### Bidirectional conversion

voc4cat converts in both directions:

```
Excel (xlsx) ←→ RDF (turtle)
```

This means you can:
1. Edit in Excel → convert to turtle → commit to git
2. Export turtle → convert to Excel → review/share

This two-way conversion allows to store diff-able RDF/turtle files in git but always provide an equivalent up-to-date xlsx file for the users to edit.
The format conversions happen automatically via the GitHub workflows implemented in vocabulary repositories that are derived from [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template).

### ID ranges for collaboration

To prevent ID conflicts when multiple people edit a vocabulary, voc4cat allocates ID ranges to contributors.
Each person gets a unique range of concept IDs they can use.
The voc4cac-template repository contains an issue-template to request IDs.

## Learn more

- [SKOS Primer](https://www.w3.org/TR/skos-primer/) - W3C introduction to SKOS
- [SKOS Reference](https://www.w3.org/TR/skos-reference/) - Complete SKOS specification
- {doc}`../reference/schemas` - How SKOS maps to configuration and xlsx formats
