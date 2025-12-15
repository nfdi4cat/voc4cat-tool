# Maintaining a Vocabulary

Guide for vocabulary maintainers and editors.

## Roles

### Editors

Editors are responsible for:

- Reviewing and merging pull requests
- Managing contributor ID ranges
- Creating releases
- Maintaining documentation quality

### Contributors

Contributors submit changes via pull requests. They need:

- A GitHub account
- An allocated ID range (for adding new concepts)
- Access to fork the repository

## Onboarding contributors

### Allocating ID ranges

When a contributor requests IDs (via the issue template):

1. Review their request for:
   - Valid ORCID identifier
   - Reasonable number of IDs requested
   - ROR identifier (optional, for institutional affiliation)

2. Choose a range that doesn't overlap with existing allocations

3. Update `idranges.toml`:

```toml
[[vocabs.myvocab.id_range]]
first_id = 5001
last_id = 6000
gh_name = "new-contributor"
name = "New Contributor Name"
orcid = "0000-0001-2345-6789"
ror_id = "https://ror.org/012345678"  # optional
```

4. Commit and push the change to main (or create a PR for review)

5. Close the issue and notify the contributor

### ID range planning

- Allocate generous ranges (1000+ IDs) to avoid frequent updates
- Leave gaps between ranges for future expansion
- Document the allocation strategy in your repository's README

## Reviewing pull requests

### Automated checks

The CI/CD pipeline validates:

- xlsx file format and required fields
- ID usage within allocated ranges
- SHACL profile compliance (vocpub)
- Concept deletion (if `allow_delete = false`)

Review the workflow run before manual review.

### Manual review checklist

- [ ] Concepts are well-defined and unambiguous
- [ ] Preferred labels are clear and consistent with existing terms
- [ ] Definitions follow the vocabulary's style guidelines
- [ ] Hierarchies make semantic sense (broader/narrower relationships)
- [ ] No duplicate concepts (check for similar existing terms)
- [ ] Mappings to external vocabularies are accurate
- [ ] PR description explains the changes and motivation

### Common issues to address

| Issue | Action |
|-------|--------|
| Vague definitions | Request clarification |
| Overlapping concepts | Suggest merging or differentiating |
| Wrong hierarchy | Discuss intended relationships |
| Missing translations | Note for future (optional) |
| Style inconsistency | Request alignment with existing patterns |

### Providing feedback

- Be constructive and specific
- Reference existing concepts as examples
- Suggest improvements rather than just rejecting
- Use GitHub's suggestion feature for small fixes

## Creating releases

Releases publish a stable version of the vocabulary.

### Tagging convention

Use date-based tags: `vYYYY-MM-DD`

Example: `v2025-01-15`

### Release process

1. Ensure main branch is in a releasable state:
   - All desired PRs merged
   - CI passing
   - Documentation up to date

2. Create a release on GitHub:
   - Go to Releases → "Draft a new release"
   - Create a new tag (e.g., `v2025-01-15`)
   - Write release notes summarizing changes
   - Publish the release

3. The publish workflow automatically:
   - Builds the vocabulary
   - Creates versioned documentation
   - Updates `latest/` directory on gh-pages

### Release notes

Include:

- Summary of new concepts added
- Significant changes or deprecations
- Contributors acknowledged
- Link to the HTML documentation

## Managing gh-pages

GitHub Pages hosts your vocabulary documentation.

### Directory structure

```
gh-pages/
├── index.html        # Links to all versions
├── dev/              # Latest from main branch
│   ├── vocab.ttl
│   ├── vocab.xlsx
│   └── vocab.html
├── latest/           # Most recent release
└── vYYYY-MM-DD/      # Tagged releases
```

### Updating index page

The index page is auto-generated. To customize:

- Edit the index template in your workflow files
- Or add custom HTML/CSS to gh-pages branch

### Troubleshooting gh-pages

If documentation doesn't update:

1. Check GitHub Pages settings (Settings → Pages)
2. Verify gh-pages branch exists
3. Check workflow run logs for errors

## Local testing

Use the justfile to test locally before merging:

```bash
# Clone and setup
git clone https://github.com/yourorg/vocabulary.git
cd vocabulary
just setup

# Test a contributor's changes
git fetch origin pull/123/head:pr-123
git checkout pr-123
just all
```

See {doc}`local-development` for detailed local development instructions.

## Keeping in sync with voc4cat-template

Periodically pull updates from the template repository:

```bash
# View changes since last sync
git fetch https://github.com/nfdi4cat/voc4cat-template
git diff ...FETCH_HEAD

# Apply updates
git pull https://github.com/nfdi4cat/voc4cat-template
git push
```

Recommended: Sync before each release to get the latest workflow improvements.

## Repository settings

### Branch protection

Configure branch protection for `main`:

- Require pull request reviews
- Require status checks to pass (CI/CD)
- Prevent force pushes

### GitHub Pages

Settings → Pages:

- Source: Deploy from a branch
- Branch: gh-pages

### Issue templates

The template repository includes issue templates for:

- Requesting ID ranges
- Suggesting improvements
- Reporting bugs

Customize these for your vocabulary's needs.

## See also

- {doc}`project-setup` - Initial repository setup
- {doc}`local-development` - Local testing workflow
