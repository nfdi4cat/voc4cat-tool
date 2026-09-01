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
├── templates/                 # xlsx template
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

When you are done, add this configuration to the repository:

```bash
# Commit & push
git add idranges.toml
git commit -m "Initial vocabulary config"
git push
```

## Generate your first vocabulary

```bash
# Generate xlsx template from configuration
voc4cat template --config idranges.toml --outdir vocabularies/ myvocab

# Edit the xlsx file in Excel or LibreOffice
# Add your initial concepts
```

## Configure GitHub settings

### Branch protection

It is recommended to prevent accidental changes to the main branch.
On GitHub this can be achieved via branch protection rules.

Settings → Branches → Add rule for `main` (or Settings → Rules → Rulesets, which is the newer equivalent):

- Require pull request reviews before merging
- Require status checks to pass, and list `No spreadsheet in the branch history` among them
- Do not allow bypassing the above settings

The last two belong together. The pipeline removes a submitted spreadsheet from the pull request branch by itself, but it can only do so when it is able to push to the branch; when it cannot - a failed conversion, or a fork owned by an organization - GitHub still reports the pull request as mergeable. The check reports that state, and only "do not allow bypassing" keeps a repository administrator from merging past it. In a ruleset the equivalent of that setting is an empty bypass list.

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

:::{note}
Any merge strategy may be used. Two earlier constraints have both been removed.

Provenance dates no longer depend on the commits: the pull-request workflow passes `--modified-date` to `voc4cat transform --prov-from-git`, so a changed concept is dated with the run date and an unchanged one keeps the date it already has. Earlier versions of this page said to disable squash merging for that reason.

Submitted spreadsheets no longer depend on the merge strategy either: the workflow removes them from every commit of the pull request branch, not only from its tip. Earlier the spreadsheet was deleted in a follow-up commit, which left it in the branch's earlier commits, so only squash merging kept it out of the history of `main` - the opposite of what the dates required. See {doc}`../reference/cli` for details.
:::

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

While most sheets in the xlsx vocabulary are created automatically, you can still provide a base-template to which the auto-created sheets will be added.
This could for example be used to provide a help sheet.

Drop a custom template file `template_myvocab.xlsx` to the folder `templates/`.
The sheets that you put into this template may not have the same name as any of the auto-generated sheets
(see {ref}`list in migration guide <step-4-generate-v1-0-excel-template>`).

(keeping-in-sync-with-the-template)=
## Keeping in sync with the template

It is suggested to merge the changes from the template repository before every new release of your vocabulary.
This ensures that the centrally maintained features and best practices trickle into your project.

To review the changes made in a new template version 26.x and compare to when you last pulled it use:

```bash
# View changes
git fetch --no-tags https://github.com/nfdi4cat/voc4cat-template refs/tags/v26.x
git diff ...FETCH_HEAD
```

If you decide to take over the changes, merge them into your repository and push them to GitHub.

```bash
# Apply changes
git merge FETCH_HEAD -m "Merge voc4cat-template v26.x"
# -- resolve any conflicts --
git push
```

Conflicts may occur if you and the template-maintainers have changed the same files since the last template-update.

:::{important}
Fetch the template with `--no-tags` and the full `refs/tags/...` path.
The shorter form `git fetch <url> tag v26.x` writes that tag into your repository and brings the remaining tags of the template with it.
There they are indistinguishable from the release tags of your own vocabulary, and any command that pushes tags publishes them.
:::

If an earlier sync copied template tags into your repository, delete them locally with `git tag -d <tag>` and, where they were pushed, with `git push --delete origin <tag>`.

### Handling merge conflicts

If conflicts occur during sync:

1. Resolve conflicts in your editor
2. Be careful to keep your customizations (README.md, idranges.toml)
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

See also [IRI design](https://github.com/nfdi4cat/voc4cat-template/blob/main/iri-design.md) (in voc4cat-template).

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
