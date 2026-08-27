# Typing support for voc4cat-tool

Design for [issue #362](https://github.com/nfdi4cat/voc4cat-tool/issues/362):
annotate the package, drive zuban to zero errors under a strict configuration,
and gate the result with a pre-commit hook.

## Goal

Every function in `src/voc4cat` carries a complete signature, every function
body is type checked, and `just typecheck` passes under a strict zuban
configuration that prevents regression.

Out of scope: `tests/` (15,385 LOC) and `example/` (4,071 LOC) stay unchecked.

## Baseline

Measured with zuban 0.9.2 against `src/` (23 source files, 12,431 LOC).

Annotation coverage is 233/325 functions (72%). Two modules have none:
`cli.py` (0/13) and `gh_index.py` (0/7).

| Configuration | Errors |
| --- | --- |
| Current (`mode = "mypy"`, `ignore_missing_imports`) | 46 |
| `+ check_untyped_defs` | 51 |
| `+ disallow_untyped_defs` | 131 |
| `+ disallow_incomplete_defs, warn_no_return, warn_unreachable` | 142 |
| **Target: strict minus two flags** | **217** |
| `strict = true` | 255 |

Checking the bodies of unannotated functions adds only 5 errors, so the
untyped parts of the code base are not hiding a large defect backlog. The
gap between 46 and 217 is dominated by absent annotations, not by broken code.

### Why not full strict

Two of strict's flags produce 38 errors that say nothing about this code:

- `no_implicit_reexport` reports about 25 openpyxl imports as private.
  openpyxl's submodules define no `__all__`, yet `load_workbook`,
  `Font` and `get_column_letter` are its documented public API.
- `disallow_untyped_decorators` reports all 13 click decorators in
  `assistant.py`. click reaches the type checker as `Any` because the
  `assistant` extra is not installed in the lint environment.

Suppressing these would need blanket per-module ignores, which weaken the gate
more than the two flags strengthen it.

### Error distribution at the target configuration

| Code | Count | Nature |
| --- | --- | --- |
| `no-untyped-def` | 85 | Missing signatures |
| `type-arg` | 42 | Bare `dict`, `set`, `Tuple` |
| `no-untyped-call` | 28 | Typed code calling our own untyped functions |
| `arg-type` | 15 | Mostly rdflib `Node` vs `URIRef` |
| `no-any-return` | 11 | |
| `var-annotated` | 10 | Empty collection literals |
| `assignment` | 9 | |
| `attr-defined` | 8 | Subclass attributes read through a base-class type |
| `union-attr` | 4 | |
| `return-value`, `return`, `index`, `call-overload` | 5 | |

The 28 `no-untyped-call` errors share a root cause with the 85
`no-untyped-def` errors and disappear as those signatures are added. The
genuine remainder is about 104 fixes.

## Findings

Every error inspected during design is an annotation defect over correct
runtime behaviour. No behaviour bug has been confirmed.

- `transform.py:63,66` — `created_at: datetime = None` in a dataclass; the
  annotation should be `datetime | None`.
- `checks.py:37` — parameter declared `dict | None` but assigned
  `config.IDRANGES`, an `IDrangeConfig`.
- `convert.py:96` — `shacl_graph_path = str(shacl_graph_path)` rebinds a
  `Path` name to `str`; needs a second name.
- `check.py:40` — declared `-> int`, returns nothing on every path. The sole
  caller at `check.py:231` discards the result, so `-> None` is correct.
- `assistant.py:97` — `holder = {}` is inferred `dict[str, str]` from the
  first write, then receives a list.
- `transform.py:520` — rdflib's `Result.__iter__` yields
  `Node | bool | ResultRow`; a SELECT query always yields `ResultRow`.

## Configuration

Final state in `pyproject.toml`. Both `just typecheck` and the pre-commit hook
read it, so there is one source of truth.

```toml
[tool.zuban]
mode = "mypy"
ignore_missing_imports = true
strict = true
# openpyxl's submodules define no __all__, so no_implicit_reexport reports
# about 25 documented-public imports as private.
implicit_reexport = true
# click reaches the checker as Any because the `assistant` extra is absent
# from the lint environment, which makes every click decorator untyped.
disallow_untyped_decorators = false
```

zuban resolves the project's imports by auto-detecting `.venv` **relative to
the configuration file**. A config file outside the project root silently
changes import resolution and the reported error count; keep it in
`pyproject.toml`.

## Approach: per-module burn-down

The first commit adopts the target configuration together with a
`[[tool.zuban.overrides]]` table that relaxes `disallow_untyped_defs` and
`disallow_untyped_calls` for every module not yet annotated. The repository is
green from that commit onward. Each later commit annotates one module and
deletes its override entry, so the table is a visible burn-down list. The final
commit removes the empty table.

This is preferred over ratcheting one flag at a time across the whole
repository: commits stay module-shaped so review has domain context, and each
module is touched once instead of by five successive flag passes.

Modules are ordered leaf-first by the intra-package import graph, because
`disallow_untyped_calls` reports a typed module that calls a still-untyped
dependency. The order below is a topological sort of that graph.

| # | Module | Errors | Intra-package dependencies |
| ---: | --- | ---: | --- |
| 1 | `__init__` | 1 | — |
| 2 | `assistant` | 20 | — |
| 3 | `fields` | 2 | — |
| 4 | `merge_vocab` | 1 | — |
| 5 | `xlsx_common` | 30 | — |
| 6 | `config` | 10 | `fields` |
| 7 | `xlsx_keyvalue` | 1 | `xlsx_common` |
| 8 | `xlsx_table` | 10 | `xlsx_common` |
| 9 | `checks` | 11 | `config` |
| 10 | `models_v1` | 0 | `xlsx_common`, `xlsx_table` |
| 11 | `xlsx_api` | 1 | `xlsx_common`, `xlsx_keyvalue`, `xlsx_table` |
| 12 | `convert_v1_helpers` | 4 | `config`, `models_v1` |
| 13 | `gh_index` | 17 | `checks`, `config` |
| 14 | `utils` | 4 | `checks`, `models_v1` |
| 15 | `convert_v1` | 29 | 9 modules |
| 16 | `docs` | 2 | `gh_index` |
| 17 | `gen_template` | 5 | 8 modules |
| 18 | `transform` | 19 | `checks`, `config`, `utils` |
| 19 | `convert_043` | 10 | `config`, `convert_v1`, `convert_v1_helpers`, `utils` |
| 20 | `convert` | 8 | 7 modules |
| 21 | `check` | 9 | 7 modules |
| 22 | `cli` | 23 | 8 modules |

The graph accounts for all three import forms in use: `from voc4cat.x import y`,
`from .x import y` (in `xlsx_api`, `xlsx_keyvalue` and `xlsx_table`) and
`from voc4cat import x` (in `checks`, `config` and others). It is acyclic.

The implementation plan groups these into 18 tasks and does not follow this
order exactly: `checks` is annotated before `config`. That inversion was
verified to be safe, because `checks` only reads `config.IDRANGES`, a pydantic
model with typed attributes, and calls no unannotated function in `config`.

Adjacent small modules may share a commit; the large ones
(`xlsx_common`, `convert_v1`, `cli`, `assistant`) get their own.

## Escape hatches

In order of preference:

1. Fix the annotation or the code.
2. `cast()` where a library's declared type is genuinely wider than its runtime
   contract, for example `Result.__iter__` yielding `ResultRow` for a SELECT
   query. Each cast carries a comment explaining why the narrowing holds.
3. `# type: ignore[specific-code]` with a comment, as a last resort.

`warn_unused_ignores` is part of `strict = true`, so ignores that become
obsolete are reported rather than accumulating silently.

Never `Any` used as a silencer, and never a bare `# type: ignore`.

## Behaviour changes

The work is annotation-only by default. If a genuine behaviour bug surfaces,
work stops on that module, a failing test is written first, then the fix, per
the project's test-driven development practice. Such a bug is reported rather
than folded silently into a typing commit.

## Open design decision

The 8 `attr-defined` errors are one pattern: `XLSXFormatter` declares
`self.config: XLSXConfig`, but `XLSXTableFormatter` reads `bold_fields` and
`table_style`, which exist only on the `XLSXTableConfig` subclass. The same
applies to `join_config` on `XLSXJoinedTableFormatter`, read through a
base-typed attribute in `xlsx_api.py`.

Two options: make the base generic in its config type
(`XLSXFormatter[ConfigT]`), or re-annotate the attribute narrowly in each
subclass `__init__`. The choice is deferred until `xlsx_table` is reached,
where the surrounding code is in view.

## Deliverables

- Annotated `src/voc4cat`, zero zuban errors under the configuration above.
- `[tool.zuban]` configuration in `pyproject.toml`.
- pre-commit hook, following the pattern already used in the CaReD project:

  ```yaml
  - repo: https://github.com/dunossauro/zuban-pre-commit
    rev: v0.9.2
    hooks:
      - id: zuban
        args: [src/, --pretty]
  ```

  `zuban` is unpinned in `pyproject.toml` and resolved to 0.9.2 by `uv.lock`.
  Tag `v0.9.2` matches that resolution; the hook `rev` and the locked version
  need to be bumped together. The hook runs from its own pre-commit environment
  containing only zuban and resolves project imports by auto-detecting `.venv`,
  so a synced virtual environment must be present.

- `src/voc4cat/py.typed` (PEP 561), added in the final commit once the package
  is fully annotated.
- `docs/conf.py`: add `plans` to `exclude_patterns` so design documents stay
  out of the published Sphinx site.

Not included by decision: a CI job running the type check. The gate therefore
runs only on developer machines with pre-commit installed; CI will not catch a
contributor who skips it.

## Verification

Every commit leaves `just typecheck` green, `just test` passing, and
`uv run ruff check src/` at no more than its pre-existing baseline. Since
annotation changes do not alter runtime behaviour, any test failure indicates a
real behaviour change and is investigated rather than accommodated.

`just lint` is deliberately not part of that contract. It runs `ruff format`
and `ruff check --fix` across `src/`, `example/` and `tests/`, so it rewrites
files instead of checking them, and it cannot exit clean: `src/` carries 62
pre-existing complexity findings, 76 across all three directories, all present
on `main` and all out of scope for a typing change. Formatting is still
enforced, by the `ruff-format` pre-commit hook on staged files.

The pre-commit `ruff` hook lints whole files and has no baseline concept, so it
rejects commits to the ten modules that carry those findings — eight of this
plan's tasks. Those commits use `SKIP=ruff git commit`, which bypasses only the
linter while `ruff format`, `zuban check`, `typos` and the hygiene hooks all
still run. Never `--no-verify`, which would skip the zuban gate this plan
exists to install.

## Follow-up phase: complexity refactor

The 62 findings are not being suppressed, only deferred. Twenty functions
exceed the complexity limits, including `convert_v1.build_concept_scheme_graph`
(complexity 36 against a limit of 10, 38 branches, 70 statements),
`xlsx_table.reconstruct_joined_data` (30, 34 branches, 73 statements) and
`convert_043._enrich_concept_scheme_from_config` (22, 25 branches, 61
statements). Decomposing them is a substantial change to the tool's core
conversion paths.

That work follows this plan rather than preceding it, deliberately. Extracting
functions out of a 38-branch body is precisely where signatures drift
silently, and the strict gate installed here catches that class of mistake.
Refactoring first would mean restructuring untyped code and then annotating
whatever shape emerged. The 690-test suite guards either order; types guard the
second one better.

### Enforcing openpyxl types

openpyxl ships no `py.typed`, so every annotation naming `Worksheet`, `Cell`,
`Workbook` or their kin resolves to `Any`. Thirty-four annotation sites are
affected, 35 of the 37 concentrated in the xlsx layer. Those annotations
document intent; they enforce nothing. `reveal_type` on an annotated
`Worksheet` returns `Any`, and reading a nonexistent attribute off one passes.

`types-openpyxl==3.1.5.20260807` closes that gap, and its version line matches
the pinned `openpyxl >= 3.1.5`. Measured against this branch it produces 17
errors in two files, `xlsx_common` (15) and `xlsx_keyvalue` (2):

- Five at `xlsx_common.py:1155-1163`, where a `_validation_list_col` counter is
  stored on openpyxl's `Workbook` object. It works only because `Workbook`
  defines no `__slots__`, and it puts this project's state on a third-party
  object under a name openpyxl could claim for itself. This needs a design fix,
  not a cast: hold the counter in a module-level map keyed by workbook, or on
  the hidden sheet that already exists for the purpose.
- Four at `xlsx_common.py:1115` and `xlsx_keyvalue.py:133`, assigning `.value`
  on a cell the stubs type as possibly a `MergedCell`, whose `value` is
  read-only `None` behind `__slots__`. A latent `AttributeError`.
- Six at `xlsx_common.py:1518-1546`, where `range_boundaries()` is stubbed as
  returning optional components. It genuinely can, for open-ended refs like
  `"A:B"`, but every input here is a bounded table ref. An assert or a cast is
  the honest fix.
- Two more: a `Workbook | None` argument at `:1214`, and optional
  `max_row`/`max_column`.

Roughly nine of the seventeen are real defects that the `Any` resolution hides
today. Adopting the stubs belongs with the refactor rather than in the typing
plan, because it reopens two modules that plan has already finished.

Delivery is a single pull request on `issue362-improve-typing`, closing #362.
