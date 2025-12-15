# Setting up a Vocabulary Project

How to create a new vocabulary project using the voc4cat-template.

## Use voc4cat-template (recommended)

The [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template) provides a complete GitHub repository structure with CI/CD workflows, issue templates, and documentation generation.

## Creating your repository

### Option 1: GitHub template (simple)

1. Go to [github.com/nfdi4cat/voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)
2. Click "Use this template" → "Create a new repository"
3. Choose your organization and repository name
4. Clone your new repository

### Option 2: Git clone (preserves history)

Create an empty repository on GitHub first, then:

```bash
git init my-vocabulary
cd my-vocabulary
git pull https://github.com/nfdi4cat/voc4cat-template
git remote add origin https://github.com/yourorg/my-vocabulary.git
git push -u origin main
```

This preserves the template's commit history, making future syncs easier.

## What's included

```
my-vocabulary/
├── idranges.toml              # Vocabulary configuration
├── justfile                   # Local development commands
├── README.md                  # Customize for your project
├── README_TEMPLATE.md         # Template documentation
├── inbox-excel-vocabs/        # Drop xlsx files here for PRs
├── vocabularies/              # Converted turtle files
├── templates/                 # Excel template
└── .github/
    ├── workflows/             # CI/CD pipelines
    │   ├── ci-pr.yml         # Pull request validation
    │   ├── merge.yml         # Main branch build
    │   └── publish.yml       # Release publication
    └── ISSUE_TEMPLATE/        # Issue forms
```

## Initial configuration

Edit `idranges.toml` with your vocabulary metadata:

```toml
config_version = "v1.0"

[vocabs.myvocab]
id_length = 6
permanent_iri_part = "https://example.org/myvocab_"

# Required metadata
vocabulary_iri = "https://example.org/myvocab"
prefix = "myvoc"
title = "My Vocabulary"
description = "A vocabulary for..."
created_date = "2025-01-01"
creator = "Your Name https://orcid.org/0000-0000-0000-0000"
repository = "https://github.com/yourorg/my-vocabulary"

# Namespace prefixes
[vocabs.myvocab.prefix_map]
myvoc = "https://example.org/myvocab_"

# Your initial ID range
[[vocabs.myvocab.id_range]]
first_id = 1
last_id = 10000
gh_name = "your-username"
orcid = "0000-0000-0000-0000"
```

See {doc}`../reference/schemas` for complete field documentation.

## Generate your first vocabulary

```bash
# Generate Excel template from configuration
voc4cat template --config idranges.toml --outdir vocabularies/

# Edit the xlsx file in Excel or LibreOffice
# Add your initial concepts

# Convert to turtle
voc4cat convert --config idranges.toml vocabularies/myvocab.xlsx

# Commit
git add .
git commit -m "Initial vocabulary"
git push
```

## Configure GitHub settings

### Branch protection

Settings → Branches → Add rule for `main`:

- Require pull request reviews before merging
- Require status checks to pass
- Do not allow bypassing the above settings

### GitHub Pages

Settings → Pages:

- Source: Deploy from a branch
- Branch: `gh-pages` / `root`
- Save

The gh-pages branch will be created automatically on the first successful merge.

### Repository settings

Recommended settings:

- Enable Issues (for ID range requests and discussions)
- Enable Wiki (optional, for extended documentation)
- Disable "Allow merge commits" (use squash or rebase for cleaner history)

## Customize your project

### Update README.md

Replace the template README with your own:

- Describe your vocabulary's scope and purpose
- Add contribution guidelines
- Include links to documentation on gh-pages
- Add badges (CI status, license, DOI if available)

### Adjust issue templates

The templates in `.github/ISSUE_TEMPLATE/` can be customized:

- `request-ids.yaml` - ID range request form
- `improvement.yaml` - Vocabulary improvement suggestions
- `bug.yaml` - Bug reports

### Configure validation

In `idranges.toml`, under `[vocabs.myvocab.checks]`:

```toml
[vocabs.myvocab.checks]
# Set to true to allow concept deletion in PRs
allow_delete = false
```

## Keeping in sync with the template

Periodically sync with the template to get workflow improvements:

```bash
# View changes
git fetch https://github.com/nfdi4cat/voc4cat-template
git diff ...FETCH_HEAD

# Apply changes
git pull https://github.com/nfdi4cat/voc4cat-template
git push
```

**Recommended**: Sync before each release.

### Handling merge conflicts

If conflicts occur during sync:

1. Resolve conflicts in your editor
2. Keep your customizations (README.md, idranges.toml)
3. Accept template updates for workflows and justfile
4. Commit the merge

## IRI design

Plan your vocabulary's IRI structure early. The default pattern:

```
https://example.org/myvocab_0000001
                    └─────────┬────┘
                    permanent_iri_part + concept ID
```

For persistent IRIs, consider using [w3id.org](https://w3id.org/) redirect service:

```
https://w3id.org/yourorg/myvocab_0000001
```

This allows content negotiation (HTML for browsers, RDF for machines).

## Next steps

- {doc}`contributing` - Learn the contribution workflow
- {doc}`local-development` - Set up local development
- {doc}`maintaining` - Maintainer guide for managing contributors and releases
