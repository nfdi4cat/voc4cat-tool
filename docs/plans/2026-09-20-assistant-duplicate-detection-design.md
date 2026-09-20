# Duplicate detection in voc-assistant

Design for [issue #387](https://github.com/nfdi4cat/voc4cat-tool/issues/387):
`voc-assistant` did not flag `voc4cat:0007795` and `voc4cat:0008124`, which
both carried `skos:prefLabel "co-precipitation"@en`
([nfdi4cat/voc4cat#310](https://github.com/nfdi4cat/voc4cat/issues/310)).

## Goal

A pair of concepts carrying the same label is always reported, whatever their
definitions say. The `compare` subcommand reports the additions it was written
to screen. Maintainers can declare reviewed pairs in `idranges.toml` so that an
accepted collision stops competing for attention with a real one. The selection
and reporting logic is covered by tests that run in CI.

Out of scope, deliberately:

- **Matching quality.** `--method sbert` scores orthographic variants poorly
  (`coprecipitation` / `co-precipitation` = 0.5781, below the 0.9 label
  threshold), so such pairs never reach the definition check at all.
  `--method levenshtein` normalises case and hyphens and scores them near 1.
  Choosing a better default, normalising labels before embedding, or running
  both methods together needs its own evaluation against real vocabulary data.
- **Using Levenshtein to score definitions.** Measured on the fixture pairs,
  the Levenshtein ratio of two definitions sits in 0.41–0.49 whatever they
  mean, while sbert spreads 0.25–0.79 and tracks meaning. A Levenshtein
  definition score would look like a score and rank nothing, so definitions
  are either scored semantically or not scored at all.
- **The reach of `check_parents`.** It reports concepts with no or several
  broader concepts across the whole of `vocab_new`. In `compare` that is the
  entire submission, not the additions, so the compare report carries an issue
  list about concepts the submitter did not touch. Restricting it to
  `added_concepts` is a behaviour change that this issue does not ask for, so
  it is left alone and noted for a follow-up.

## Defects

Defects 1 to 3 together hide the duplicate. The first two are the ones reported
in the issue; the third surfaced while reading the code and is why the fix is
not a two-line patch. Defects 4 to 6 are unrelated to the duplicate and were
found in the same code; they are fixed here because the code is being rewritten
around them.

### 1. `compare` reports nothing

The concept-selection guard in `find_similarities` reads

```python
if (not compare_all) or (idx_i not in self.idx_new):
    continue
```

`compare` passes `compare_all=False`, so the first clause is true for every
concept and every concept is skipped. The subcommand's reason to exist —
screening a submission against the published vocabulary — is silently useless.
The operator must be `and`.

### 2. An exact label match is discarded on its definition score

`find_similarities` requires both thresholds to pass. A pair above
`threshold_labels` is dropped unless it also clears `threshold_definitions`.
Measured for the reported pair with `all-MiniLM-L6-v2`:

| comparison | score | threshold | result |
| --- | --- | --- | --- |
| prefLabel `co-precipitation` / `co-precipitation` | 1.0000 | 0.9 | passes |
| definition `0007795` / `0008124` | 0.6614 | 0.8 | fails, pair dropped |

### 3. `idx_new` indexes the wrong collection

`CompareVocabularies.__init__` builds `idx_new` as positions in `vocab_new`,
which holds concepts. `find_similarities` uses it to index
`new_vocab_labels`, which holds pref labels **followed by** alt labels. The two
collections have the same order only for their first `len(vocab_new)` entries.

Two consequences, both invisible today because defect 1 masks them. After
defect 1 is fixed, `compare` would still skip every alt label of a newly added
concept, because no alt-label position can ever be in `idx_new`. And the
A-B/B-A de-duplication, which tests `idx_j in self.idx_new and idx_i >= idx_j`,
does not fire for alt-label positions, so those pairs would be reported twice.

### 4. The report is written in the locale encoding

`markdown_report` opens its output with `open(fname, "w")` and no `encoding`
argument. On Windows that is the locale encoding, so a non-ASCII label raises
`UnicodeEncodeError` and no report is written.

### 5. `--include-alt-labels` cannot be switched off

The option is declared `is_flag=True` with `default=True`, so it evaluates to
`True` whether or not it is passed. Alt labels are always included and the
documented way to exclude them does not exist.

### 6. `check_parents` takes an unused parameter

`method` is accepted and never read.

## Design

### Module split

`src/voc4cat/similarity.py` is new and holds everything that does not need a
scoring backend: `Concept`, `ConceptSimilarity`, `ConceptIssue`, `Problem`,
`load_vocab`, `check_parents`, `ComparisonResult`, candidate selection, the
threshold rule, accepted-pair partitioning, sorting and markdown rendering.
`ComparisonResult` gains the new threshold and the accepted and unused entries,
so that rendering stays a function of its argument. Its imports are
`rdflib`, `voc4cat.config` and the standard library, all core dependencies, so
it is importable and testable wherever the package is installed.

`src/voc4cat/assistant.py` keeps the click CLI and the two scoring backends as
adapters over sentence-transformers and Levenshtein. It holds no selection or
reporting logic.

The seam between them is two-phase rather than a callback, so that both pure
phases take plain data:

1. The backend computes the full label score matrix and returns it as
   `list[list[float]]`. `SentenceTransformer.similarity` returns a torch
   `Tensor`; the backend converts it with `Tensor.tolist()` before handing it
   over. `similarity.py` therefore never imports torch, and the score matrix
   has one representation regardless of method. Verify the conversion locally
   with the extra installed; CI cannot exercise it.
2. `similarity.select_candidates` takes the labels, the score matrix, the
   thresholds and the set of label keys to screen, and returns the candidate
   concept pairs. A label key is the pair `(concept_iri, label_role)`, where
   `label_role` is `pref_label` or `altLabel-<n>`, matching the keys of the
   label dict itself. For `check`, every key is screened; for `compare`, the
   keys whose concept is in `added_concepts`, alt labels included. This is
   what replaces `idx_new` and what defect 3 got wrong.
3. The caller scores the definitions of those candidates in **one** batched
   call. Today `find_similarities` calls `get_similarities_sbert` separately
   for every candidate pair.
4. `similarity.apply_definition_rule` takes the candidates and their definition
   scores and returns the final, sorted list.

### Reporting rule

A pair is reported when

```text
label >= threshold_labels_certain
  or (label >= threshold_labels and definition >= threshold_definitions)
```

Defaults: `threshold_labels_certain = 0.98`, `threshold_labels = 0.9`,
`threshold_definitions = 0.8`. The two existing thresholds keep the meaning
they have today; the new one is the documented escape hatch for pairs whose
labels agree so closely that the definitions cannot argue them away.

Candidate selection in phase 2 admits a pair that clears either
`threshold_labels_certain` or `threshold_labels`, which is to say
`threshold_labels`, since the certain threshold is the higher of the two. The
rule above is applied in phase 4, once definition scores exist. Configurations
that set `threshold_labels_certain` below `threshold_labels` are rejected with
an error at startup rather than silently ignored.

Results are sorted by label score descending, then definition score descending.

### Pair identity and de-duplication

Two concepts can match on several label combinations at once: pref/pref,
pref/alt, alt/alt. Today this is handled twice and badly — by comparing
positional indices in `find_similarities`, and again by an O(n²) scan over a
list of `{a, b}` sets in `markdown_report`, which keeps whichever match was
encountered first.

Both mechanisms go. Candidates are accumulated in a dict keyed by
`frozenset({concept_id_i, concept_id_j})`, keeping the **highest**-scoring
label combination for each concept pair. Equal scores are broken by label key,
so the output does not depend on dict iteration order. A concept pair therefore
appears exactly once, represented by its strongest evidence, and the result
agrees with the sort order instead of depending on iteration order.

### Accepted similarities

`config.Vocab` gains a list of reviewed pairs:

```python
class AcceptedSimilarity(BaseModel):
    concepts: list[str]   # exactly two, validated
    reason: str           # non-empty, validated
```

```toml
[[vocabs.voc4cat.accepted_similarity]]
concepts = ["voc4cat:0007795", "voc4cat:0008124"]
reason = "Distinct processes that share a label; resolved in nfdi4cat/voc4cat#310."
```

`reason` is mandatory. An accepted pair without a recorded reason is a
suppression nobody can review later.

The assistant resolves the vocabulary the way `convert_v1` and `check` already
do: `vocab_name = path.stem.lower()`, then `config.IDRANGES.vocabs[vocab_name]`
for the settings and `config.CURIES_CONVERTER_MAP[vocab_name]` to expand the
CURIEs to IRIs. Entries are matched on the pair of IRIs irrespective of order.

Reported pairs are partitioned, not filtered: accepted pairs move to their own
report section (below) instead of disappearing.

Entries that do not apply are surfaced rather than ignored, because an
allow-list nobody prunes eventually hides a real duplicate:

- **Unknown concept** — an entry naming an IRI that is not in the vocabulary.
  Detected in both subcommands.
- **No matching pair** — an entry whose pair was not among this run's
  candidates. Detected only for `check`, which scans the whole vocabulary. In
  `compare`, only additions are scanned, so most accepted pairs legitimately
  produce no candidate and reporting them would be noise.

Both are listed in the report and logged as warnings.

### Concept links

`assistant.py` currently hardcodes the voc4cat development documentation site
as the link base for every report, which is wrong for every other vocabulary
and goes stale for this one.

`config.Vocab` gains an optional `concept_url_template`, a Jinja template
validated to contain `{{ entity_id }}`, mirroring the existing
`provenance_url_template` and its validator. `entity_id` is the numeric concept
ID, extracted from the IRI with `config.ID_PATTERNS[vocab_name]` as `checks.py`
does.

```toml
concept_url_template = "https://nfdi4cat.github.io/voc4cat/dev/voc4cat/index.html#https://w3id.org/nfdi4cat/voc4cat_{{ entity_id }}"
```

When the template is unset, or no configuration was found, links point at the
concept's own permanent IRI. A report is then still useful without any
configuration, which matters because the assistant is also run ad hoc against a
vocabulary file on its own.

### Running without sentence-transformers

`--definitions none` turns definition scoring off, so nothing imports
sentence-transformers or torch and duplicate detection works from the
Levenshtein backend alone. The rule degrades accordingly: a pair at or above
`--threshold-labels-certain` is still reported, its definition score recorded
as not scored; a pair below it cannot be judged and is not reported, and the
run says how many were dropped that way.

Definition scoring is **not** skipped merely because the label score already
settles a pair. With `--definitions sbert` every candidate is scored, so the
report column is always filled: that column is what identified the defect in
issue #387 in the first place.

What the torch-free mode reaches depends on `--threshold-labels-certain`,
because Levenshtein scores orthographic variants below the 0.98 default:

| pair | Levenshtein |
| --- | --- |
| `co-precipitation` / `coprecipitation` | 0.9677 |
| `catalyser` / `catalyzer` | 0.8889 |
| `sulphur` / `sulfur` | 0.7692 |

At the default only exact matches (after case and hyphen normalisation) are
reported. Lowering the threshold to 0.96 catches the first of these; the
second and third do not even reach `--threshold-labels`.

### CLI

`check` and `compare` both gain:

| option | default | effect |
| --- | --- | --- |
| `--threshold-labels-certain FLOAT` | `0.98` | label score above which the definition score is not consulted |
| `--config PATH` | `idranges.toml` in the working directory | source of accepted pairs and the link template; a missing file is a warning, not an error |
| `-o, --output PATH` | `check_report_<method>.md` / `compare_report_<method>.md` | report destination |
| `--hide-accepted` | off | omit the accepted-similarities section |
| `--definitions sbert\|none` | `sbert` | `none` scores no definitions and needs no model |

`--include-alt-labels` becomes a click boolean flag pair,
`--include-alt-labels/--no-alt-labels`, default on. This changes the CLI
surface: the option now does what its name says instead of being permanently
true.

### Report format

The main table keeps its current columns and gains nothing. Two sections are
added after it:

```markdown
## Accepted similarities

| Concept ID | Concept label | Similar Concept ID | Similar Concept label | Score Label | Score Definition | Reason |

## Unused accepted-similarity entries

| Concepts | Reason | Status |
```

`Status` is `unknown concept` or `no matching pair`. Both sections are omitted
when they would be empty. `--hide-accepted` omits the first; the second is
always shown, because it reports a configuration problem rather than a
reviewed decision.

The report is written with `encoding="utf-8"`.

## Dependency change

`click` and `levenshtein` move from the `assistant` extra to the core
dependencies, and what remains of the extra is renamed `sbert`. click is small,
pure Python, and adds no transitive dependency that is not already core
(`colorama`). `torch`, `sentence-transformers` and `Levenshtein` stay in the
extra and are imported lazily, inside the scoring functions that need them.

The consequence is that `voc4cat.assistant` becomes importable without the
extra, so the CLI layer — option parsing, configuration loading, output paths,
report assembly — can be tested in CI. Only the two scoring backends cannot.

Each lazy import sits behind a `try`/`except ImportError` that raises with a
message naming the `sbert` extra and the flags that avoid it. Without it, a user
who installed plain `voc4cat` now reaches a bare `ModuleNotFoundError` deep in
a command that used to refuse to start.

## Testing

`tests/test_similarity.py` covers `similarity.py` against fixture Turtle files
and hand-written score matrices: the threshold rule at each boundary, the
`compare` guard, the label-key indexing that defect 3 got wrong, pair
de-duplication and best-match selection, sort order, the accepted-pair
partition, unknown-concept and no-matching-pair detection, link construction
with and without a template, and markdown rendering including non-ASCII labels.
No extra required; runs in every CI job.

A fixture reproduces the issue directly: two concepts with an identical
`skos:prefLabel` and unrelated definitions must be reported.

`tests/test_assistant.py` covers the CLI with an injected score matrix, and the
two scoring backends behind `pytest.importorskip`. The backend tests are
skipped in CI and are the one part of the change that only runs locally with
the extra installed.

## Project configuration

- `tool.coverage.run.omit` drops its `**/voc4cat/assistant.py` entry. The two
  scoring backends carry `# pragma: no cover` with a comment naming the extra
  as the reason.
- `tool.ruff.lint.per-file-ignores` keeps `PLR0913`/`PLR0917` for
  `assistant.py`; the commands gain four options each. `similarity.py` is
  written to need no ignores.
- `tool.zuban.disallow_untyped_decorators` is currently `false` because click
  is absent from the lint environment and its decorators reach the checker as
  `Any`. Once click is a core dependency, re-check whether the override can be
  removed; keep it if the decorators still type as untyped.
</content>
</invoke>
