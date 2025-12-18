# Setting up a Vocabulary Project

This section is about how to create a new vocabulary project using the voc4cat-template repository.

The [voc4cat-template](https://github.com/nfdi4cat/voc4cat-template) provides a complete GitHub repository structure with CI/CD workflows, issue templates, and documentation generation.

## Creating your repository

Create an empty repository on GitHub first, then:

```bash
git init my-vocabulary
cd my-vocabulary
git pull https://github.com/nfdi4cat/voc4cat-template
git remote add origin https://github.com/my-gh-name/my-vocabulary.git
git push -u origin main
```

This preserves the template's commit history, making future syncs easier.
By syncing you can update your repositories with features or bug fixes made in the template.

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
last_id = 100
gh_name = "your-username"
orcid = "0000-0000-0000-0000"
```

See {doc}`../reference/schemas` for the complete documentation of the configuration fields.

When your are done, add this configuration to the repository:

```bash
# Commit & push
git add idranges.toml
git commit -m "Initial vocabulary config"
git push
```

## Generate your first vocabulary

First, add the configuration for your vocabularies to the repository:

```bash
# Generate Excel template from configuration
voc4cat template --config idranges.toml --outdir vocabularies/

# Edit the xlsx file in Excel or LibreOffice
# Add your initial concepts
```

## Configure GitHub settings

### Branch protection

It is recommended to prevent accidental changes to the main branch.
On Github this can be achieved via branch preptection rules.

Settings → Branches → Add rule for `main`:

- Require pull request reviews before merging
- Require status checks to pass
- Do not allow bypassing the above settings

### GitHub Pages

GitHub pages are used to serve the documentation and vocabulary.

Settings → Pages:

- Source: Deploy from a branch
- Branch: `gh-pages` / `root`
- Save

The gh-pages branch will be created automatically on the first successful merge of a pull request with vocabulary data.

### Repository settings

Recommended settings:

- Enable Issues (for ID range requests and discussions)
- Disable Wiki (optional, storing documentation in the code-repository is typically preferred)
- Disable "Allow merge commits" (optional, the remaining options "squash" and "rebase" give a cleaner git history)

## Customize your project

### Update README.md

Replace the template README with your own:

- Describe your vocabulary's scope and purpose
- Add contribution guidelines
- Include links to documentation on gh-pages
- Review/change the license
- Add badges (CI status, DOI if available)

### Adjust issue templates

The templates in `.github/ISSUE_TEMPLATE/` can be customized:

- `request-ids.yaml` - ID range request form
- `improvement.yaml` - Vocabulary improvement suggestions
- `bug.yaml` - Bug reports

### Customize the xlsx template

While most sheets in the xlsx vocdabulary are created automatically, you can still provide a base-template to which the auto-created sheets will be added.
This could for example be used to provide a help sheet.

Drop a custom template file `template_myvocab.xlsx` to the folder `templates/`.
The sheets that you put into this template may not have the same name as any of the auto-generated sheets.

(keeping-in-sync-with-the-template)=
## Keeping in sync with the template

It is suggested to merge the changes from the template repository before every new release of your vocabulary.
This ensures that the centrally maintained features and best practices trickle into your project.

To review the changes made in the template after you last pulled it use:

```bash
# View changes
git fetch https://github.com/nfdi4cat/voc4cat-template
git diff ...FETCH_HEAD
```

If you decide to take over the changes, pull them into your repository and push them to GitHub.

```bash
# Apply changes
git pull https://github.com/nfdi4cat/voc4cat-template
git push
```

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

:::{admonition} **Deeper Customization**
:class: tip

Study [Voc4Cat](https://nfdi4cat.github.io/voc4cat/), the vocabulary for Catalysis, and look at its [code](https://github.com/nfdi4cat/voc4cat/) for inspiration how to further customize your vocabulary.
For, example you may also want to include a [custom homepage](https://github.com/nfdi4cat/voc4cat) built with [Sphinx](https://www.sphinx-doc.org)/[MyST](https://myst-parser.readthedocs.io/).

Also take a look at its w3id.org [redirect configuration](https://github.com/perma-id/w3id.org/tree/master/nfdi4cat) if you struggle to create your own.
:::

- {doc}`contributing` - Learn the contribution workflow
- {doc}`local-development` - Set up local development
- {doc}`maintaining` - Maintainer guide for managing contributors and releases
