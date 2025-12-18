# Maintaining a Vocabulary

Guide for vocabulary maintainers and editors.

https://nfdi4cat.github.io/voc4cat/
:::{seealso}

Our Catalysis Vocabulary **Voc4Cat** includes [various sections for maintiners](https://nfdi4cat.github.io/voc4cat/) that you may find helpful.
:::

In the vocabulary maintenance, two roles are distinguished, Contributors and Editors (AKA Maintainers).

Editors are responsible for:

- Reviewing and merging pull requests
- Managing contributor ID ranges
- Creating releases
- Maintaining vocabulary and documentation quality

Contributors submit suggestions for vocabulary additions or changes.

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

### Write Release notes

Use GitHub´s feature to create a list of changes made since the last release.

Review and revise as needed but be sure to include

- Significant changes including contributor information
- Deprecations

## Managing gh-pages / documentation

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

Use the justfile to test and debug failing workflows locally:

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

See {ref}`keeping-in-sync-with-the-template` in {doc}`project-setup`.

Recommended: Sync before each release to get the latest workflow improvements.

## See also

- {doc}`project-setup` - Initial repository setup
- {doc}`local-development` - Local testing workflow
