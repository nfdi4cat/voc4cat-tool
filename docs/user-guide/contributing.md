# Contributing to a Vocabulary

How to contribute concepts, collections, and mappings to a voc4cat-template-based vocabulary.

:::{seealso}

Our Catalysis Vocabulary **Voc4Cat** includes a [comprehensive contribution guide](https://nfdi4cat.github.io/voc4cat/docs_usage/how-to-contribute.html) that you may find helpful.
:::

## Overview

You can contribute to vocabularies in two ways:

1. **Excel-based** (recommended): Edit an xlsx file and submit via pull request
2. **Turtle-based** (advanced): Edit RDF/Turtle files directly

This guide covers the Excel/Spreadsheet-based workflow, which is suitable for most contributors.

## Get the current vocabulary

Download the latest vocabulary file from the repository's GitHub Pages:

```
https://<org>.github.io/<repo>/dev/<vocab-name>.xlsx
```

For example, the voc4cat vocabulary is available at:
`https://nfdi4cat.github.io/voc4cat/dev/voc4cat.xlsx`

## Make your changes

Open the xlsx file and edit the relevant sheets:

- **Concepts**: Add or modify concept definitions
- **Collections**: Group related concepts together
- **Mappings**: Link concepts to external vocabularies

See {doc}`../reference/schemas` for detailed column specifications.

### Adding new concepts

1. Choose an ID from your allocated range (check the "ID Ranges" sheet)
2. Add a row with the required fields:
   - Concept IRI (e.g., `voc4cat:0001234`)
   - Language Code (e.g., `en`)
   - Preferred Label
   - Definition

For multi-language support, add one row per language with the same Concept IRI.

### Modifying existing concepts

Edit the relevant cells in the Concepts sheet. Use the "Change Note" column to document the reason for the changes.

### Deprecating concepts

Select a reason from the "Obsoletion reason" dropdown. Do not delete the row - deprecated concepts remain in the vocabulary for reference.
Note that version 1.0 does not support linking an successor of the deprecated concept. Let us know via an issue if you need this feature.

## Request an ID range

If you need to add new concepts but don't have an ID range allocated:

1. Go to the repository's Issues tab
2. Select "Request ID range" from the issue templates
3. Provide your GitHub name and ORCID (reocmmended) and the number of IDs needed
4. A maintainer will update `idranges.toml` with your allocation

## Submit your contribution

See also voc4cat´s help.

### Prepare your repository

1. Fork the vocabulary repository (if you haven't already)
2. Sync your fork with the latest changes ("Sync fork" button)
3. Create a feature branch for your contribution

### Add your changes

1. Place your xlsx file in the `inbox-excel-vocabs/` folder
2. The filename must match the vocabulary name (e.g., `voc4cat.xlsx`)
3. Commit the file to your feature branch

### Create a pull request

1. Push your branch to your fork
2. Open a pull request against the main branch
3. Describe your changes and motivation in the PR description
4. Link to any related issues

## Understand CI/CD feedback

When you submit a pull request, an automated pipeline runs:

1. **Validation**: Checks xlsx format and content
2. **Conversion**: Converts xlsx to RDF/Turtle
3. **Merge**: Integrates changes with existing vocabulary
4. **Artifacts**: Generates updated xlsx and documentation

### Review the results

After the pipeline completes:

1. Check the workflow status (green checkmark = success)
2. Download the workflow artifacts:
   - Updated xlsx file (with any auto-generated fields)
   - Log files (for debugging)
   - HTML documentation preview

### Common validation errors

:::{table}
:align: left

| Error | Cause | Fix |
|-------|-------|-----|
| Missing required field | Empty Definition or Label | Add the missing content |
| Invalid IRI format | Malformed CURIE | Use format `prefix:id` |
| ID outside range | Using unallocated ID | Request an ID range first |

:::

## Fix issues in your PR

If the pipeline fails or reviewers request changes:

1. Pull the latest changes from your PR branch (the CI may have committed updates)
2. Make the necessary fixes in the xlsx file
3. Commit and push - this triggers the pipeline again

## What happens after merge

When your PR is merged:

1. Your changes are integrated into the vocabulary files in `vocabularies/`
2. The CI/CD pipeline rebuilds documentation
3. Updated files are published to GitHub Pages:
   - `dev/` - Latest from main branch
   - `latest/` - Most recent release
   - `vYYYY-MM-DD/` - Tagged releases

## Typical edit cycle

For local testing before submitting a PR, see {doc}`local-development`.

Quick workflow summary:

1. Download current vocabulary (xlsx from gh-pages)
2. Edit in your Spreadsheet software
3. Place in `inbox-excel-vocabs/`
4. Submit PR
5. Review CI results
6. Address feedback
7. Merge

## See also

- {doc}`../reference/cli` - Command reference for local validation
- {doc}`local-development` - Test changes locally before submitting
