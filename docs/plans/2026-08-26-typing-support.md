# Typing Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Annotate every function in `src/voc4cat` so `just typecheck` passes under a strict zuban configuration, gated by a pre-commit hook.

**Architecture:** Task 1 adopts the final strict configuration immediately, together with a `[[tool.zuban.overrides]]` table that sets `ignore_errors = true` for every module not yet annotated. The repository reports zero errors from that commit onward. Each later task annotates one module (or a small group), deletes its override entry, and must leave the checker green. The final task removes the emptied table and adds the PEP 561 marker.

**Tech Stack:** Python >= 3.10, zuban 0.9.2 (mypy-compatible mode), pytest, ruff, just, uv, pre-commit.

**Spec:** `docs/plans/2026-08-26-typing-support-design.md`

## Global Constraints

- Target configuration is `strict = true` minus `no_implicit_reexport` and `disallow_untyped_decorators`. Exact block in Task 1.
- Scope is `src/` only. Do not annotate `tests/` or `example/`.
- zuban resolves imports by auto-detecting `.venv` **relative to the config file**. Configuration lives in `pyproject.toml` at the project root. Never move it.
- The `assistant` extra is deliberately NOT installed in the lint environment. `click`, `torch`, `sentence_transformers` and `Levenshtein` resolve to `Any`. Do not install the extra to "fix" `assistant.py` — that changes the error set.
- Escape-hatch order: (1) fix the annotation or code, (2) `cast()` with a comment explaining why the narrowing holds, (3) `# type: ignore[specific-code]` with a comment. Never `Any` as a silencer, never a bare `# type: ignore`.
- `warn_unused_ignores` is active, so a stale ignore becomes an error.
- This is annotation-only work. If a genuine behaviour bug surfaces, STOP: write a failing test first, then fix, then report it separately. Do not fold a behaviour fix silently into a typing commit.
- Every task ends with `just typecheck` green, `just test` passing, and `uv run ruff check src/` reporting no more than its pre-existing 62-finding baseline.
- **Do NOT run `just lint`.** It runs `ruff format` and `ruff check --fix` over `src/`, `example/` and `tests/`, so it rewrites files rather than checking them, and it can never exit clean: `src/` carries 62 pre-existing complexity findings (76 across all three directories) that are present on `main` and are out of scope here. Use `uv run ruff check src/` to check, and `uv run ruff format --check src/` if you need to confirm formatting. The pre-commit hooks still run `ruff-format` and `ruff --fix` on staged files at commit time; that remains the formatting gate.
- Never modify a file outside your task's stated scope. If a tool rewrites unrelated files, revert them before committing.
- Commit messages: first line under 60 characters, no attribution footers.

## Verification commands

```bash
just typecheck                                    # must print "Success: no issues found"
just test                                         # full suite must pass
uv run ruff check src/                            # must stay at the 62-finding baseline
uv run ruff format --check src/                   # must report "26 files already formatted"
uv run zuban check src/ 2>&1 | grep 'MODULE\.py'  # errors for one module while working
```

To see a module's real errors while its override is still active, temporarily
delete that module from the override list, run the check, and restore it — or
just delete the entry as the task instructs and work from there.

---

### Task 1: Adopt strict configuration behind an override table

**Files:**
- Modify: `pyproject.toml` (`[tool.zuban]` section, currently at line 283)
- Modify: `.pre-commit-config.yaml`
- Modify: `docs/conf.py` (`exclude_patterns`, line 47)

**Interfaces:**
- Consumes: nothing.
- Produces: the `[[tool.zuban.overrides]]` table that every later task deletes one entry from. Module names use dotted form; `__init__.py` is addressed as `"voc4cat"`, not `"voc4cat.__init__"`.

- [ ] **Step 1: Replace the `[tool.zuban]` section in `pyproject.toml`**

Replace the existing three-line section with:

```toml
[tool.zuban]
# https://docs.zubanls.com/
# Zuban's own default mode infers far more aggressively than the annotations in
# this code base assume, so stay on mypy-compatible semantics.
mode = "mypy"
# Suppress all missing import errors for all untyped libraries
ignore_missing_imports = true
strict = true
# openpyxl's submodules define no __all__, so no_implicit_reexport reports
# about 25 documented-public imports (load_workbook, Font, get_column_letter)
# as private.
implicit_reexport = true
# click reaches the checker as Any because the `assistant` extra is absent from
# the lint environment, which would make every click decorator untyped.
disallow_untyped_decorators = false

# Burn-down list: modules still to be annotated for issue #362. Each entry is
# removed by the commit that annotates that module. When the list is empty,
# delete this table.
[[tool.zuban.overrides]]
module = [
  "voc4cat",
  "voc4cat.assistant",
  "voc4cat.check",
  "voc4cat.checks",
  "voc4cat.cli",
  "voc4cat.config",
  "voc4cat.convert",
  "voc4cat.convert_043",
  "voc4cat.convert_v1",
  "voc4cat.convert_v1_helpers",
  "voc4cat.docs",
  "voc4cat.fields",
  "voc4cat.gen_template",
  "voc4cat.gh_index",
  "voc4cat.merge_vocab",
  "voc4cat.transform",
  "voc4cat.utils",
  "voc4cat.xlsx_api",
  "voc4cat.xlsx_common",
  "voc4cat.xlsx_keyvalue",
  "voc4cat.xlsx_table",
]
ignore_errors = true
```

`voc4cat.models_v1` is absent on purpose: it already reports zero errors.

- [ ] **Step 2: Verify the checker is green**

Run: `just typecheck`
Expected: `Success: no issues found in 23 source files`

If it reports errors, a module is missing from the list. Add it and note the discrepancy — do not weaken the top-level flags.

- [ ] **Step 3: Add the pre-commit hook**

In `.pre-commit-config.yaml`, after the `ruff-pre-commit` block and before the `typos` block:

```yaml
  - repo: https://github.com/dunossauro/zuban-pre-commit
    rev: v0.9.2
    hooks:
      # Run `zuban check`. The hook runs in its own environment holding only
      # zuban and resolves project imports by auto-detecting .venv, so the
      # project environment must be synced (`uv sync`) for it to work.
      - id: zuban
        args: [src/, --pretty]
```

`rev` must track the zuban version resolved in `uv.lock` (currently 0.9.2). Bump both together.

- [ ] **Step 4: Verify the hook runs and passes**

Run: `pre-commit run zuban --all-files`
Expected: `Passed`

If it reports errors that `just typecheck` does not, `.venv` is missing or stale. Run `uv sync` and retry.

- [ ] **Step 5: Keep design docs out of the published site**

In `docs/conf.py` line 47, change:

```python
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
```

to:

```python
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "plans"]
```

- [ ] **Step 6: Verify the docs still build without new warnings**

Run: `just docs`
Expected: build completes; no "document isn't included in any toctree" warning naming a file under `plans/`.

- [ ] **Step 7: Verify tests and lint**

Run: `just test && uv run ruff check src/`
Expected: suite passes, ruff clean.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml docs/conf.py
git commit -m "Add strict zuban config behind a burn-down list"
```

---
## Module tasks: shared procedure

Tasks 2 to 17 all follow the same five steps. They are written out per task so
each can be executed without reading its neighbours, but the shape is:

1. Delete the module's entry from the `module = [...]` list in `pyproject.toml`.
2. Run `just typecheck` to see that module's real errors.
3. Annotate until the checker is green, following the escape-hatch order in
   Global Constraints.
4. Run `just test` and `uv run ruff check src/`.
5. Commit `pyproject.toml` together with the module.

Error lists below are the measured baseline at the target configuration. Counts
can shift slightly as dependencies get annotated, so always work from the live
`just typecheck` output rather than from the list. The list tells you what kind
of work to expect.

---

### Task 2: Annotate the trivial leaves

**Files:**
- Modify: `src/voc4cat/__init__.py`, `src/voc4cat/fields.py`, `src/voc4cat/merge_vocab.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: Task 1's override table.
- Produces: annotated `voc4cat`, `voc4cat.fields`, `voc4cat.merge_vocab`. `fields` is a dependency of `config` (Task 6).

Baseline, 4 errors:

```
__init__.py:20: Function is missing a return type annotation  [no-untyped-def]
fields.py:164: Argument "orcid" to "Researcher" has incompatible type "str"; expected "HttpUrl"  [arg-type]
fields.py:165: Argument "home_organization" to "Researcher" has incompatible type "str"; expected "HttpUrl"  [arg-type]
merge_vocab.py:47: Function is missing a type annotation for one or more parameters  [no-untyped-def]
```

- [ ] **Step 1: Remove three entries from the override list**

In `pyproject.toml`, delete these lines from `module = [...]`:

```toml
  "voc4cat",
  "voc4cat.fields",
  "voc4cat.merge_vocab",
```

- [ ] **Step 2: Run the checker to see the real errors**

Run: `just typecheck`
Expected: FAIL with the 4 errors above.

- [ ] **Step 3: Fix them**

`__init__.py:20` and `merge_vocab.py:47`: add the missing annotations.

`fields.py:164-165` are inside the `if __name__ == "__main__":` demo block.
`ORCIDIdentifier` and `RORIdentifier` are `Annotated[HttpUrl, ...]`, so the
checker demands `HttpUrl` even though pydantic's `BeforeValidator` accepts
`str` at runtime. Wrap the literals rather than suppressing:

```python
    jane = Researcher(
        name="Jane Smith",
        orcid=HttpUrl("https://orcid.org/0000-0002-1825-0097"),
        home_organization=HttpUrl("https://ror.org/02y72wh86"),
    )
```

`HttpUrl` is already imported at `fields.py:10`.

- [ ] **Step 4: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/voc4cat/__init__.py src/voc4cat/fields.py src/voc4cat/merge_vocab.py
git commit -m "Type __init__, fields and merge_vocab"
```

---

### Task 3: Annotate `checks`

**Files:**
- Modify: `src/voc4cat/checks.py`, `pyproject.toml`

**Interfaces:**
- Consumes: `voc4cat.config` via `from voc4cat import config` (`checks.py:15`), which is annotated later in Task 6. This is deliberate and verified: `checks` only reads `config.IDRANGES`, a pydantic model whose attributes are already typed, so it calls no unannotated function and this task produces exactly the 11 errors below and no `no-untyped-call` extras. `IDrangeConfig` can be imported as a type regardless of whether `config` itself is annotated yet.
- Produces: annotated `voc4cat.checks`, a dependency of `gh_index` (Task 7), `utils` (Task 10), `convert_v1` (Task 11), `gen_template` (Task 12), `transform` (Task 13), `convert` (Task 15), `check` (Task 16) and `cli` (Task 17).

Baseline, 11 errors:

```
checks.py:24: Function is missing a type annotation  [no-untyped-def]
checks.py:37: Function is missing a return type annotation  [no-untyped-def]
checks.py:37: Missing type arguments for generic type "dict"  [type-arg]
checks.py:39: Incompatible types in assignment (expression has type "IDrangeConfig | dict[Any, Any]", variable has type "dict[Any, Any] | None")  [assignment]
checks.py:42: Item "dict[Any, Any]" of "dict[Any, Any] | None" has no attribute "single_vocab"  [union-attr]
checks.py:42: Item "None" of "dict[Any, Any] | None" has no attribute "single_vocab"  [union-attr]
checks.py:47: Function is missing a return type annotation  [no-untyped-def]
checks.py:119: Function is missing a return type annotation  [no-untyped-def]
checks.py:139: Need type annotation for "voc"  [var-annotated]
checks.py:140: Item "dict[Any, Any]" of "Vocab | dict[Any, Any]" has no attribute "checks"  [union-attr]
checks.py:293: Argument 1 to "sorted" has incompatible type "Generator[Node, None, None]"; expected "Iterable[SupportsDunderLT[Any] | SupportsDunderGT[Any]]"  [arg-type]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.checks",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 11 errors above.

- [ ] **Step 3: Fix the declared type of `idranges`**

Lines 37 to 42 are one defect. The parameter is declared `dict | None` but the
default path assigns `config.IDRANGES`, which is an `IDrangeConfig`. Change the
annotation to match reality:

```python
def check_number_of_files_in_inbox(
    inbox_dir: Path, idranges: IDrangeConfig | None = None
) -> None:
    """Check that inbox has not more than one file if single_vocab option is true."""
    idranges = config.IDRANGES if idranges is None else idranges
```

Import `IDrangeConfig` from `voc4cat.config` if it is not already imported.
That single change clears the `type-arg`, `assignment` and both `union-attr`
errors.

Lines 139 to 140 are the same shape: annotate `voc` with the model type it
actually holds so that `.checks` resolves.

Line 293 is rdflib: graph subject generators are declared to yield `Node`,
which is not ordered, while the values are `URIRef` at runtime. Narrow with a
cast that carries a reason:

```python
# Subjects of this graph pattern are always URIRef, which sorts as str.
sorted(cast("Iterable[URIRef]", <the generator>))
```

- [ ] **Step 4: Add the remaining signatures**

Lines 24, 47 and 119 are missing annotations that no other step covers. Line 37
gets its return type as part of Step 3.

- [ ] **Step 5: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/voc4cat/checks.py
git commit -m "Type checks module"
```

---

### Task 4: Annotate `assistant`

**Files:**
- Modify: `src/voc4cat/assistant.py`, `pyproject.toml`

**Interfaces:**
- Consumes: nothing.
- Produces: annotated `voc4cat.assistant`. No other module imports it.

Do NOT install the `assistant` extra. `click`, `torch`, `sentence_transformers`
and `Levenshtein` are meant to resolve to `Any` here; installing the extra
changes the error set and makes the gate irreproducible for everyone else.

Baseline, 20 errors, being three defects plus missing signatures:

```
assistant.py:40:  Function is missing a type annotation for one or more parameters  [no-untyped-def]
assistant.py:80:  Missing type arguments for generic type "dict"  [type-arg]
assistant.py:91:  Incompatible types in assignment (expression has type "list[Any]", target has type "str")  [assignment]
assistant.py:92:  Incompatible types in assignment (expression has type "list[Any]", target has type "str")  [assignment]
assistant.py:97:  "str" has no attribute "append"  [attr-defined]
assistant.py:101: "str" has no attribute "append"  [attr-defined]
assistant.py:131: Function is missing a type annotation for one or more parameters  [no-untyped-def]
assistant.py:144: "None" has no attribute "encode"  [attr-defined]
assistant.py:147: "None" has no attribute "similarity"  [attr-defined]
assistant.py:151: Function is missing a type annotation for one or more parameters  [no-untyped-def]
assistant.py:151: Missing type arguments for generic type "list"  [type-arg]
assistant.py:160: Missing type arguments for generic type "list"  [type-arg]
assistant.py:171: Function is missing a type annotation  [no-untyped-def]
assistant.py:233: Function is missing a type annotation for one or more parameters  [no-untyped-def]
assistant.py:240: Missing type arguments for generic type "dict"  [type-arg]
assistant.py:267: Call to untyped function "find_similarities" in typed context  [no-untyped-call]
assistant.py:275: Function is missing a type annotation for one or more parameters  [no-untyped-def]
assistant.py:275: Missing type arguments for generic type "dict"  [type-arg]
assistant.py:302: Missing type arguments for generic type "dict"  [type-arg]
assistant.py:418: Function is missing a return type annotation  [no-untyped-def]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.assistant",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 20 errors above.

- [ ] **Step 3: Fix the `holder` dict, lines 91 to 101**

`holder = {}` is inferred as `dict[str, str]` from the first write. It also
holds lists. Annotate it for what it actually holds:

```python
        holder: dict[str, str | list[str]] = {}
```

If that makes the `Concept(**holder)` construction complain, prefer collecting
`alt_labels` and `parents` in local lists and constructing `Concept` with
keyword arguments, rather than widening to `dict[str, Any]`.

- [ ] **Step 4: Fix the lazily loaded model, lines 144 and 147**

`self.model` starts as `None` and receives a `SentenceTransformer` on first
use. Declare it optional, then bind a local after the load so the narrowing
survives:

```python
        self.model: SentenceTransformer | None = None
```

```python
        if self.model is None:
            self.model = SentenceTransformer(model)
        model_obj = self.model
        embeddings = model_obj.encode(sentences)
        similarities = model_obj.similarity(embeddings, embeddings)
```

- [ ] **Step 5: Add the remaining signatures and generic parameters**

Annotate the functions at lines 40, 131, 151, 171, 233, 275 and 418, and
parameterise the bare `dict` and `list` annotations at lines 80, 151, 160, 240,
275 and 302. Line 267 clears once `find_similarities` is annotated.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

`assistant.py` has no tests, so `just test` only confirms nothing else broke.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/assistant.py
git commit -m "Type assistant module"
```

---

### Task 5: Annotate `xlsx_common`

**Files:**
- Modify: `src/voc4cat/xlsx_common.py`, `pyproject.toml`

**Interfaces:**
- Consumes: nothing.
- Produces: annotated `voc4cat.xlsx_common`, the base layer for `xlsx_keyvalue` and `xlsx_table` (Task 8), `models_v1` and `xlsx_api` (Task 9), `convert_v1` (Task 11), `gen_template` (Task 12), `convert` (Task 15) and `check` (Task 16). The `XLSXConfig` dataclass at line 953 and the `XLSXFormatter` base at line 989 are what Task 8's design decision hangs off.

This is the largest module (1,562 LOC) and the largest error count. Fourteen of
the errors are a run of missing return annotations between lines 688 and 745,
which is repetitive rather than hard.

Baseline, 30 errors:

```
xlsx_common.py:78:   Missing type arguments for generic type "Callable"  [type-arg]
xlsx_common.py:79:   Missing type arguments for generic type "Callable"  [type-arg]
xlsx_common.py:298:  Missing type arguments for generic type "Callable"  [type-arg]
xlsx_common.py:305:  Missing type arguments for generic type "Callable"  [type-arg]
xlsx_common.py:374:  Need type annotation for "trivial_defaults"  [var-annotated]
xlsx_common.py:394:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:625:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:659:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:672:  Returning Any from function declared to return "str"  [no-any-return]
xlsx_common.py:688:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:693:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:698:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:703:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:708:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:713:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:718:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:724:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:729:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:734:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:740:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:745:  Function is missing a return type annotation  [no-untyped-def]
xlsx_common.py:751:  Missing type arguments for generic type "dict"  [type-arg]
xlsx_common.py:758:  Missing type arguments for generic type "dict"  [type-arg]
xlsx_common.py:763:  Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
xlsx_common.py:769:  Missing type arguments for generic type "list"  [type-arg]
xlsx_common.py:776:  Missing type arguments for generic type "list"  [type-arg]
xlsx_common.py:781:  Returning Any from function declared to return "list[Any]"  [no-any-return]
xlsx_common.py:906:  Missing type arguments for generic type "dict"  [type-arg]
xlsx_common.py:914:  Missing type arguments for generic type "list"  [type-arg]
xlsx_common.py:1018: Function is missing a type annotation for one or more parameters  [no-untyped-def]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.xlsx_common",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 30 errors above.

- [ ] **Step 3: Parameterise the `Callable` annotations**

Lines 78, 79, 298 and 305 use bare `Callable`. Give each the real signature it
is called with, for example `Callable[[Any], str]`. Read the call sites before
choosing; do not default to `Callable[..., Any]`, which defeats the check.

- [ ] **Step 4: Annotate `trivial_defaults` at line 374 and the serializer returns**

The three `no-any-return` errors at 672, 763 and 781 come from returning a value
the checker sees as `Any` out of an annotated function. Where the value really
is the declared type, narrow it at the source rather than widening the return
annotation.

- [ ] **Step 5: Add the missing return annotations**

Lines 394, 625, 659, and the run from 688 to 745, plus the parameter annotations
at 1018. Parameterise the bare `dict` and `list` at 751, 758, 769, 776, 906 and 914.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/xlsx_common.py
git commit -m "Type xlsx_common module"
```

---

### Task 6: Annotate `config`

**Files:**
- Modify: `src/voc4cat/config.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `voc4cat.fields` from Task 2.
- Produces: annotated `voc4cat.config`, including `IDrangeConfig`, which Task 3 imports for the `checks` signature and which `convert_v1_helpers` (Task 10), `gen_template` (Task 12) and `convert_043` (Task 14) depend on.

Baseline, 10 errors:

```
config.py:84:  Function is missing a type annotation  [no-untyped-def]
config.py:123: Function is missing a type annotation  [no-untyped-def]
config.py:124: Need type annotation for "ids_defined" (hint: "ids_defined: Set[<type>] = ...")  [var-annotated]
config.py:186: Need type annotation for "ID_PATTERNS" (hint: "ID_PATTERNS: Dict[<type>, <type>] = ...")  [var-annotated]
config.py:187: Need type annotation for "ID_RANGES_BY_ACTOR"  [var-annotated]
config.py:191: Function is missing a type annotation  [no-untyped-def]
config.py:211: Function is missing a return type annotation  [no-untyped-def]
config.py:212: Need type annotation for "new_conf" (hint: "new_conf: Dict[<type>, <type>] = ...")  [var-annotated]
config.py:229: Item "None" of "IDrangeConfig | None" has no attribute "model_dump_json"  [union-attr]
config.py:242: Call to untyped function "_id_ranges_by_actor" in typed context  [no-untyped-call]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.config",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 10 errors above.

- [ ] **Step 3: Annotate the module-level containers**

Lines 186, 187 and 212 are empty-literal containers. Annotate each with the key
and value types it is later populated with. Line 124 is the same for a `set`.

- [ ] **Step 4: Handle the optional config at line 229**

`IDRANGES` is `IDrangeConfig | None`. Line 229 calls `.model_dump_json()` on it.
Establish whether `None` is genuinely reachable there:

- If it cannot be `None` at that point, add an explicit guard that raises
  `Voc4catError` with a clear message, which both documents and narrows.
- If it can, handle the `None` branch.

Do not silence this one with a cast; it is the only `union-attr` in the module
and the guard is cheap. If the guard would change behaviour on a path that is
currently reachable, STOP and follow the behaviour-bug rule in Global Constraints.

- [ ] **Step 5: Add the remaining signatures**

Lines 84, 123, 191 and 211. Line 242 clears once `_id_ranges_by_actor` is annotated.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/config.py
git commit -m "Type config module"
```

---

### Task 7: Annotate `gh_index`

**Files:**
- Modify: `src/voc4cat/gh_index.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `voc4cat.checks` from Task 3.
- Produces: annotated `voc4cat.gh_index`, including `build_multirelease_index`, which `docs` (Task 9) calls.

This module currently has no annotations at all (0 of 7 functions). Seven of the
17 errors are `no-untyped-call` between its own functions and clear as the
signatures land.

Baseline, 17 errors:

```
gh_index.py:21:  Function is missing a type annotation for one or more parameters  [no-untyped-def]
gh_index.py:25:  Need type annotation for "vocabs" (hint: "vocabs: List[<type>] = ...")  [var-annotated]
gh_index.py:27:  Need type annotation for "tags" (hint: "tags: List[<type>] = ...")  [var-annotated]
gh_index.py:29:  Function is missing a type annotation  [no-untyped-def]
gh_index.py:34:  Function is missing a return type annotation  [no-untyped-def]
gh_index.py:62:  Function is missing a return type annotation  [no-untyped-def]
gh_index.py:63:  Call to untyped function "_load_template" in typed context  [no-untyped-call]
gh_index.py:69:  Function is missing a return type annotation  [no-untyped-def]
gh_index.py:73:  Call to untyped function "_load_template" in typed context  [no-untyped-call]
gh_index.py:76:  Call to untyped function "_make_versions" in typed context  [no-untyped-call]
gh_index.py:77:  Call to untyped function "_make_versions" in typed context  [no-untyped-call]
gh_index.py:83:  Function is missing a return type annotation  [no-untyped-def]
gh_index.py:84:  Call to untyped function "_make_document" in typed context  [no-untyped-call]
gh_index.py:87:  Function is missing a type annotation  [no-untyped-def]
gh_index.py:99:  Call to untyped function "get_version_data" in typed context  [no-untyped-call]
gh_index.py:100: Call to untyped function "generate_document" in typed context  [no-untyped-call]
gh_index.py:108: Call to untyped function "build_multirelease_index" in typed context  [no-untyped-call]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.gh_index",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 17 errors above.

- [ ] **Step 3: Annotate every function, innermost first**

Annotate in this order so each `no-untyped-call` resolves as you go:
`_load_template` (line 62 area), `_make_versions`, `_make_document`,
`get_version_data`, `generate_document`, `build_multirelease_index`.

The jinja2 template object returned by `_load_template` is `jinja2.Template`.

- [ ] **Step 4: Annotate the containers at lines 25 and 27**

`vocabs` and `tags` are empty list literals. Annotate with the element type
each is populated with.

- [ ] **Step 5: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/voc4cat/gh_index.py
git commit -m "Type gh_index module"
```

---
### Task 8: Annotate `xlsx_keyvalue` and `xlsx_table`, and resolve the formatter/config typing

**Files:**
- Modify: `src/voc4cat/xlsx_keyvalue.py`, `src/voc4cat/xlsx_table.py`, `pyproject.toml`
- Possibly modify: `src/voc4cat/xlsx_common.py` (base classes at lines 953 and 989)

**Interfaces:**
- Consumes: annotated `voc4cat.xlsx_common` from Task 5.
- Produces: annotated `voc4cat.xlsx_keyvalue` and `voc4cat.xlsx_table`, plus whatever typing shape is chosen for `XLSXFormatter.config`. Task 9 (`xlsx_api`) reads `self.formatter.join_config` and depends directly on that choice.

**This task carries the one design decision deferred from the spec.** Five of
the 11 errors are a single pattern: `XLSXFormatter.__init__` stores
`self.config: XLSXConfig` (the base dataclass at `xlsx_common.py:953`), but
`XLSXTableFormatter` reads `bold_fields` and `table_style`, which exist only on
`XLSXTableConfig` (`xlsx_table.py:43` and `:46`). `XLSXJoinedTableFormatter`
sets `self.join_config` at `xlsx_table.py:799`, which `xlsx_api.py` then reads
through a base-typed attribute.

Baseline, 11 errors:

```
xlsx_keyvalue.py:555: Returning Any from function declared to return "BaseModel"  [no-any-return]
xlsx_table.py:233:  Incompatible types in assignment (expression has type "Any | str", target has type "list[str]")  [assignment]
xlsx_table.py:261:  Incompatible types in assignment (expression has type "None", target has type "list[str]")  [assignment]
xlsx_table.py:322:  Argument 2 to "_add_title" of "XLSXFormatter" has incompatible type "str | None"; expected "str"  [arg-type]
xlsx_table.py:586:  "XLSXConfig" has no attribute "bold_fields"  [attr-defined]
xlsx_table.py:617:  "XLSXConfig" has no attribute "table_style"  [attr-defined]
xlsx_table.py:817:  Argument 2 to "_add_title" of "XLSXFormatter" has incompatible type "str | None"; expected "str"  [arg-type]
xlsx_table.py:1017: Returning Any from function declared to return "list[BaseModel]"  [no-any-return]
xlsx_table.py:1036: "XLSXFormatter" has no attribute "join_config"  [attr-defined]
xlsx_table.py:1057: "XLSXFormatter" has no attribute "join_config"  [attr-defined]
xlsx_table.py:1075: Returning Any from function declared to return "list[BaseModel]"  [no-any-return]
```

- [ ] **Step 1: Remove both entries**

Delete these lines from the `module = [...]` list in `pyproject.toml`:

```toml
  "voc4cat.xlsx_keyvalue",
  "voc4cat.xlsx_table",
```

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 11 errors above.

- [ ] **Step 3: STOP and confirm the formatter/config approach with David**

Two options. Do not pick unilaterally; the decision was explicitly deferred to
this point in `docs/plans/2026-08-26-typing-support-design.md`.

Option A, generic base. `XLSXFormatter` becomes generic in its config type:

```python
ConfigT = TypeVar("ConfigT", bound=XLSXConfig)


class XLSXFormatter(ABC, Generic[ConfigT]):
    def __init__(self, config: ConfigT) -> None:
        self.config: ConfigT = config
        self.serialization_engine = XLSXSerializationEngine()
        self.row_calculator = XLSXRowCalculator(config)
```

with `class XLSXTableFormatter(XLSXFormatter[XLSXTableConfig])`. Type-safe and
self-documenting, but touches the base class and every subclass, and callers
holding a bare `XLSXFormatter` need a parameter.

Option B, narrowed re-annotation in each subclass:

```python
class XLSXTableFormatter(XLSXFormatter):
    def __init__(self, config: XLSXTableConfig) -> None:
        super().__init__(config)
        self.config: XLSXTableConfig = config
```

Smaller diff, confined to the subclasses, but the narrowing is repeated per
subclass and a caller holding the base type still sees `XLSXConfig`.

Recommend Option A if `xlsx_api.py:144` (Task 9) also becomes cleaner under it;
otherwise Option B. Report the recommendation and wait for the decision.

- [ ] **Step 4: Apply the agreed approach**

Implement the option David chose. That clears lines 586, 617, 1036 and 1057.

- [ ] **Step 5: Fix the `_add_title` argument type**

Lines 322 and 817 pass `str | None` where `_add_title` declares `str`.
`XLSXConfig.title` is `str | None = None` (`xlsx_common.py:957`). Either guard
at the call site or widen `_add_title` to accept `str | None` and return early
when it is `None` — choose whichever matches what the code already does when no
title is configured.

- [ ] **Step 6: Fix the remaining assignments and `Any` returns**

Lines 233 and 261 assign a non-list into a `list[str]` target; correct the
declared type or the assignment to match actual contents. Lines 555, 1017 and
1075 return values the checker sees as `Any`; narrow at the source.

- [ ] **Step 7: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

`tests/test_xlsx_table.py` (858 lines) and `tests/test_xlsx_keyvalue.py` (645
lines) cover this area well. Any failure here is a real behaviour change.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/voc4cat/xlsx_keyvalue.py src/voc4cat/xlsx_table.py src/voc4cat/xlsx_common.py
git commit -m "Type xlsx table and keyvalue formatters"
```

---

### Task 9: Annotate `docs` and `xlsx_api`

**Files:**
- Modify: `src/voc4cat/docs.py`, `src/voc4cat/xlsx_api.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `voc4cat.gh_index` from Task 7, `voc4cat.xlsx_common` from Task 5, and the formatter typing from Task 8.
- Produces: annotated `voc4cat.docs` and `voc4cat.xlsx_api`. `voc4cat.models_v1` needs no work; it already reports zero errors and has no override entry.

Baseline, 3 errors:

```
docs.py:57:      Function is missing a type annotation  [no-untyped-def]
docs.py:88:      Call to untyped function "build_multirelease_index" in typed context  [no-untyped-call]
xlsx_api.py:144: Incompatible return value type (got "type", expected "type[BaseModel]")  [return-value]
```

- [ ] **Step 1: Remove both entries**

Delete these lines from the `module = [...]` list in `pyproject.toml`:

```toml
  "voc4cat.docs",
  "voc4cat.xlsx_api",
```

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 3 errors above. `docs.py:88` may already be gone if
Task 7 annotated `build_multirelease_index`.

- [ ] **Step 3: Annotate `docs.py:57` and fix `xlsx_api.py:144`**

`xlsx_api.py:144` returns a bare `type` where `type[BaseModel]` is declared.
Narrow the value at its source so the declared return type holds, rather than
widening the signature.

- [ ] **Step 4: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/voc4cat/docs.py src/voc4cat/xlsx_api.py
git commit -m "Type docs and xlsx_api modules"
```

---

### Task 10: Annotate `convert_v1_helpers` and `utils`

**Files:**
- Modify: `src/voc4cat/convert_v1_helpers.py`, `src/voc4cat/utils.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `voc4cat.config` (Task 6), `voc4cat.checks` (Task 3), `voc4cat.models_v1` (already clean).
- Produces: annotated `voc4cat.convert_v1_helpers` and `voc4cat.utils`, both dependencies of `convert_v1` (Task 11), `gen_template` (Task 12), `transform` (Task 13), `convert_043` (Task 14), `convert` (Task 15), `check` (Task 16) and `cli` (Task 17). `utils.extract_numeric_id_from_iri` is called from `transform.py:525`.

Baseline, 8 errors:

```
convert_v1_helpers.py:275: Function is missing a type annotation for one or more parameters  [no-untyped-def]
convert_v1_helpers.py:316: Missing type arguments for generic type "dict"  [type-arg]
convert_v1_helpers.py:317: Missing type arguments for generic type "dict"  [type-arg]
convert_v1_helpers.py:665: Missing type arguments for generic type "dict"  [type-arg]
utils.py:38:  Function is missing a return type annotation  [no-untyped-def]
utils.py:47:  Function is missing a type annotation  [no-untyped-def]
utils.py:57:  Need type annotation for "seen" (hint: "seen: Set[<type>] = ...")  [var-annotated]
utils.py:105: Function is missing a type annotation for one or more parameters  [no-untyped-def]
```

- [ ] **Step 1: Remove both entries**

Delete these lines from the `module = [...]` list in `pyproject.toml`:

```toml
  "voc4cat.convert_v1_helpers",
  "voc4cat.utils",
```

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 8 errors above.

- [ ] **Step 3: Add the annotations**

All eight are missing signatures, bare `dict` generics, or an empty `set`
literal. Parameterise each `dict` with the key and value types actually stored.

- [ ] **Step 4: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/voc4cat/convert_v1_helpers.py src/voc4cat/utils.py
git commit -m "Type convert_v1_helpers and utils"
```

---

### Task 11: Annotate `convert_v1`

**Files:**
- Modify: `src/voc4cat/convert_v1.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `checks`, `convert_v1_helpers`, `models_v1`, `utils`, `xlsx_api`, `xlsx_common`, `xlsx_keyvalue`, `xlsx_table` — Tasks 3, 5, 8, 9 and 10.
- Produces: annotated `voc4cat.convert_v1`, a dependency of `convert_043` (Task 14) and `convert` (Task 15).

Largest module at 2,970 LOC, but the work is repetitive: 17 of 29 errors are
bare `dict` generics and 6 more are missing parameter annotations on adjacent
functions between lines 1157 and 1323.

Baseline, 29 errors:

```
convert_v1.py:226,304,318,323,414,425,430,519,528,652,772,775,936,938,1051,1052,2924:
    Missing type arguments for generic type "dict"  [type-arg]
convert_v1.py:1157,1194,1229,1268,1284,1323:
    Function is missing a type annotation for one or more parameters  [no-untyped-def]
convert_v1.py:1714: Returning Any from function declared to return "ConceptSchemeV1"  [no-any-return]
convert_v1.py:1731: Returning Any from function declared to return "list[ConceptV1]"  [no-any-return]
convert_v1.py:1749: Returning Any from function declared to return "list[CollectionV1]"  [no-any-return]
convert_v1.py:1767: Returning Any from function declared to return "list[MappingV1]"  [no-any-return]
convert_v1.py:1785: Returning Any from function declared to return "list[PrefixV1]"  [no-any-return]
convert_v1.py:2642: Argument 3 to "Collection" has incompatible type "list[URIRef]"; expected "list[Node]"  [arg-type]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.convert_v1",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 29 errors above.

- [ ] **Step 3: Fix the list invariance at line 2642**

rdflib's `Collection` declares `list[Node]`. `list` is invariant, so
`list[URIRef]` is rejected even though `URIRef` is a `Node`. zuban's own note
points at the fix: the parameter should be a covariant `Sequence`. Since the
signature belongs to rdflib, convert at the call site:

```python
# rdflib types Collection's items as list[Node]; list is invariant, so the
# list[URIRef] we built has to be widened explicitly.
Collection(graph, subject, list(cast("list[Node]", items)))
```

Prefer whichever of a cast or an explicitly `list[Node]`-annotated local reads
better in context.

- [ ] **Step 4: Fix the five `Any` returns at lines 1714 to 1785**

These read values out of an untyped structure and return them as declared model
types. Narrow at the source so the declared return type is honest.

- [ ] **Step 5: Parameterise the bare `dict` annotations and add the six signatures**

Work top to bottom through the `type-arg` lines, then the run of functions from
1157 to 1323.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/convert_v1.py
git commit -m "Type convert_v1 module"
```

---

### Task 12: Annotate `gen_template`

**Files:**
- Modify: `src/voc4cat/gen_template.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `checks`, `config`, `convert_v1_helpers`, `models_v1`, `utils`, `xlsx_api`, `xlsx_common`, `xlsx_keyvalue` — Tasks 3, 5, 6, 8, 9 and 10.
- Produces: annotated `voc4cat.gen_template`, called from `cli` (Task 17).

Baseline, 5 errors, all missing signatures:

```
gen_template.py:213: Function is missing a return type annotation  [no-untyped-def]
gen_template.py:237: Function is missing a type annotation for one or more parameters  [no-untyped-def]
gen_template.py:248: Function is missing a type annotation for one or more parameters  [no-untyped-def]
gen_template.py:259: Function is missing a type annotation for one or more parameters  [no-untyped-def]
gen_template.py:333: Function is missing a type annotation for one or more parameters  [no-untyped-def]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.gen_template",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 5 errors above.

- [ ] **Step 3: Add the five signatures**

- [ ] **Step 4: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/voc4cat/gen_template.py
git commit -m "Type gen_template module"
```

---

### Task 13: Annotate `transform`

**Files:**
- Modify: `src/voc4cat/transform.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `voc4cat.checks` (Task 3) and `voc4cat.utils` (Task 10).
- Produces: annotated `voc4cat.transform`, a dependency of `check` (Task 16) and `cli` (Task 17). `join_split_turtle` is imported by `check.py:26`.

Baseline, 19 errors:

```
transform.py:63:  Incompatible types in assignment (expression has type "None", variable has type "datetime")  [assignment]
transform.py:66:  Incompatible types in assignment (expression has type "None", variable has type "datetime")  [assignment]
transform.py:190: Function is missing a return type annotation  [no-untyped-def]
transform.py:205: Missing type arguments for generic type "set"  [type-arg]
transform.py:216: Function is missing a type annotation for one or more parameters  [no-untyped-def]
transform.py:216: Missing type arguments for generic type "dict"  [type-arg]
transform.py:230: Function is missing a type annotation for one or more parameters  [no-untyped-def]
transform.py:230: Missing type arguments for generic type "dict"  [type-arg]
transform.py:246: Function is missing a type annotation for one or more parameters  [no-untyped-def]
transform.py:282: Function is missing a type annotation for one or more parameters  [no-untyped-def]
transform.py:452: Function is missing a type annotation  [no-untyped-def]
transform.py:520: Value of type "bool" is not indexable  [index]
transform.py:520: No overload variant of "__getitem__" of "tuple" matches argument type "str"  [call-overload]
transform.py:525: Call to untyped function "extract_numeric_id_from_iri" in typed context  [no-untyped-call]
transform.py:605: Function is missing a type annotation  [no-untyped-def]
transform.py:625: Function is missing a type annotation  [no-untyped-def]
transform.py:672: Function is missing a type annotation  [no-untyped-def]
transform.py:694: Call to untyped function "_transform_rdf" in typed context  [no-untyped-call]
transform.py:724: Call to untyped function "_handle_prov_from_git" in typed context  [no-untyped-call]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.transform",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 19 errors above.

- [ ] **Step 3: Fix the `FileGitInfo` dataclass defaults, lines 63 and 66**

Two dataclass fields declare `datetime` but default to `None`:

```python
@dataclass
class FileGitInfo:
    """Git history information for a file."""

    created_by: str = ""
    created_email: str = ""
    created_at: datetime | None = None
    modified_by: str = ""
    modified_email: str = ""
    modified_at: datetime | None = None
```

Then follow the compile errors at the use sites: any code reading
`.created_at` now has to handle `None`. If a use site cannot handle `None`,
that is a signal worth reporting rather than casting away.

- [ ] **Step 4: Narrow the SPARQL result row at line 520**

`Graph.query()` returns a `Result` whose `__iter__` is declared
`Node | bool | ResultRow`. The query at line 506 is a SELECT, which always
yields `ResultRow`, so `qresult["iri"]` is valid at runtime. Narrow with a cast
that says why:

```python
        for qresult in qresults:
            # A SELECT query always yields ResultRow; rdflib's Result.__iter__
            # is declared more widely to cover ASK and CONSTRUCT.
            iri = cast("ResultRow", qresult)["iri"]
```

Import `ResultRow` from `rdflib.query`.

- [ ] **Step 5: Add the remaining signatures and generic parameters**

Lines 190, 216, 230, 246, 282, 452, 605, 625 and 672, plus the bare `set` at 205
and bare `dict` at 216 and 230. Lines 525, 694 and 724 clear once their callees
are annotated (`extract_numeric_id_from_iri` comes from Task 10).

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/transform.py
git commit -m "Type transform module"
```

---

### Task 14: Annotate `convert_043`

**Files:**
- Modify: `src/voc4cat/convert_043.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `config` (Task 6), `convert_v1` (Task 11), `convert_v1_helpers` and `utils` (Task 10).
- Produces: annotated `voc4cat.convert_043`, a dependency of `convert` (Task 15).

Eight of the 10 errors are one rdflib pattern: graph iteration yields `Node`,
while `_transform_triple_043_to_v1` and `_add_provenance_triples` declare
`URIRef`.

Baseline, 10 errors:

```
convert_043.py:396: Argument 1 to "_transform_triple_043_to_v1" has incompatible type "Node"; expected "URIRef"  [arg-type]
convert_043.py:397: Argument 2 to "_transform_triple_043_to_v1" has incompatible type "Node"; expected "URIRef"  [arg-type]
convert_043.py:399: Argument 4 to "_transform_triple_043_to_v1" has incompatible type "set[Node]"; expected "set[URIRef]"  [arg-type]
convert_043.py:400: Argument 5 to "_transform_triple_043_to_v1" has incompatible type "set[Node]"; expected "set[URIRef]"  [arg-type]
convert_043.py:401: Argument 6 to "_transform_triple_043_to_v1" has incompatible type "set[Node]"; expected "set[URIRef]"  [arg-type]
convert_043.py:406: Argument 1 to "add" of "Graph" has incompatible type "tuple[Any, Unpack[Tuple[Any, ...]]]"; expected "tuple[Node, Node, Node]"  [arg-type]
convert_043.py:425: Argument 2 to "_add_provenance_triples" has incompatible type "set[Node]"; expected "set[URIRef]"  [arg-type]
convert_043.py:425: Argument 3 to "_add_provenance_triples" has incompatible type "set[Node]"; expected "set[URIRef]"  [arg-type]
convert_043.py:453: Function is missing a type annotation for one or more parameters  [no-untyped-def]
convert_043.py:462: Missing type arguments for generic type "Tuple"  [type-arg]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.convert_043",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 10 errors above.

- [ ] **Step 3: Decide where to narrow, once**

Do not sprinkle eight casts. Narrow at the point where the `Node` values are
produced — where the graph is iterated to build those sets — so that the sets
are genuinely `set[URIRef]` from creation:

```python
        # Subjects and predicates of a SKOS graph are always URIRef; rdflib
        # types graph iteration as the wider Node.
        concept_iris: set[URIRef] = {cast("URIRef", s) for s in graph.subjects(...)}
```

Then lines 396 to 425 follow without further changes.

If any of these values genuinely can be a `BNode` or `Literal` at runtime, the
cast is wrong and the calling code has a real defect. Check before casting.

- [ ] **Step 4: Fix the triple construction at line 406**

The value passed to `Graph.add()` is a variable-length tuple where a
three-element `tuple[Node, Node, Node]` is required. Build the triple as an
explicit three-tuple so its length is visible to the checker.

- [ ] **Step 5: Annotate line 453 and parameterise the bare `Tuple` at 462**

Use lowercase `tuple[...]`, matching the `py310` target and the pyupgrade rules
already active in ruff.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/convert_043.py
git commit -m "Type convert_043 module"
```

---

### Task 15: Annotate `convert`

**Files:**
- Modify: `src/voc4cat/convert.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `checks` (Task 3), `convert_043` (Task 14), `convert_v1` (Task 11), `models_v1`, `utils` (Task 10), `xlsx_common` (Task 5).
- Produces: annotated `voc4cat.convert`, a dependency of `check` (Task 16) and `cli` (Task 17).

Baseline, 8 errors:

```
convert.py:79:  Function is missing a return type annotation  [no-untyped-def]
convert.py:96:  Incompatible types in assignment (expression has type "str", variable has type "Path")  [assignment]
convert.py:101: Argument "shacl_graph" to "validate" has incompatible type "Path"; expected "DataGraph | Dataset | Graph | BufferedIOBase | TextIOBase | str | bytes | None"  [arg-type]
convert.py:165: Missing type arguments for generic type "dict"  [type-arg]
convert.py:221: Function is missing a type annotation  [no-untyped-def]
convert.py:240: Call to untyped function "has_file_in_multiple_formats" in typed context  [no-untyped-call]
convert.py:249: Function is missing a type annotation  [no-untyped-def]
convert.py:252: Call to untyped function "_check_convert_args" in typed context  [no-untyped-call]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.convert",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 8 errors above.

- [ ] **Step 3: Fix the rebound path variable, lines 96 and 101**

`resolve_profile()` returns a `Path`, which line 96 then rebinds to a `str`.
Both errors are that one rebinding. Use a separate name:

```python
    shacl_graph_path, _profile_name = resolve_profile(profile)

    # validate the RDF file
    _conforms, results_graph, _results_text = pyshacl.validate(
        data_graph,
        shacl_graph=str(shacl_graph_path),
        allow_warnings=allow_warnings,
    )
```

- [ ] **Step 4: Add the remaining signatures**

Lines 79, 221 and 249, plus the bare `dict` at 165. Lines 240 and 252 clear once
their callees are annotated.

- [ ] **Step 5: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/voc4cat/convert.py
git commit -m "Type convert module"
```

---

### Task 16: Annotate `check`

**Files:**
- Modify: `src/voc4cat/check.py`, `pyproject.toml`

**Interfaces:**
- Consumes: annotated `checks` (Task 3), `convert` (Task 15), `models_v1`, `transform` (Task 13), `utils` (Task 10), `xlsx_common` (Task 5).
- Produces: annotated `voc4cat.check`, a dependency of `cli` (Task 17).

Baseline, 9 errors:

```
check.py:40:  Missing return statement  [return]
check.py:69:  Need type annotation for "seen_concept_iris" (hint: "seen_concept_iris: List[<type>] = ...")  [var-annotated]
check.py:117: Return value expected  [return-value]
check.py:122: Function is missing a type annotation  [no-untyped-def]
check.py:155: Function is missing a type annotation  [no-untyped-def]
check.py:170: Function is missing a type annotation  [no-untyped-def]
check.py:173: Call to untyped function "_check_ci_args" in typed context  [no-untyped-call]
check.py:213: Call to untyped function "ci_post" in typed context  [no-untyped-call]
check.py:245: Incompatible types in assignment (expression has type "Vocab | None", variable has type "Vocab")  [assignment]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.check",` from the `module = [...]` list in `pyproject.toml`.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 9 errors above.

- [ ] **Step 3: Correct the return type of `check_xlsx`**

Lines 40 and 117 are one defect. `check_xlsx` is declared `-> int` at line 40
but returns nothing on either path: a bare `return` at line 117 and an implicit
fall-through at line 120. Its only caller, `check.py:231`, discards the result.
The annotation is simply wrong:

```python
def check_xlsx(fpath: Path, outfile: Path) -> None:
```

Leave the bare `return` at line 117 as-is; it is an early exit, not a value.

This is an annotation fix, not a behaviour change: nothing observes the return
value today. Do not add an `int` return to satisfy the old annotation.

- [ ] **Step 4: Handle the optional `Vocab` at line 245**

A `Vocab | None` is assigned to a name declared `Vocab`. Establish whether
`None` is reachable. If it is not, guard explicitly and raise `Voc4catError`
with a clear message. If it is, handle the branch. If handling it would change
behaviour on a currently reachable path, STOP and follow the behaviour-bug rule
in Global Constraints.

- [ ] **Step 5: Add the remaining annotations**

Lines 69, 122, 155 and 170. Lines 173 and 213 clear once `_check_ci_args` and
`ci_post` are annotated.

- [ ] **Step 6: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

`tests/test_check.py` covers `check_xlsx` directly; a failure there means the
return-type change was not as inert as expected.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/check.py
git commit -m "Type check module"
```

---

### Task 17: Annotate `cli`

**Files:**
- Modify: `src/voc4cat/cli.py`, `pyproject.toml`

**Interfaces:**
- Consumes: every other module. This is the last one for a reason.
- Produces: annotated `voc4cat.cli`, including `run_cli_app`, the console-script entry point declared in `pyproject.toml`.

Currently zero of 13 functions are annotated. Eleven of the 23 errors are
`no-untyped-call` between its own functions and clear as the signatures land.
Most functions take or return `argparse.ArgumentParser` or `argparse.Namespace`.

Baseline, 23 errors:

```
cli.py:22,67,76,91,168,240,293,384,414,444,482: Function is missing a type annotation  [no-untyped-def]
cli.py:96,116: Function is missing a return type annotation  [no-untyped-def]
cli.py:447: Call to untyped function "create_root_parser" in typed context  [no-untyped-call]
cli.py:457: Call to untyped function "create_common_options_parser" in typed context  [no-untyped-call]
cli.py:464: Call to untyped function "add_transform_subparser" in typed context  [no-untyped-call]
cli.py:465: Call to untyped function "add_convert_subparser" in typed context  [no-untyped-call]
cli.py:466: Call to untyped function "add_check_subparser" in typed context  [no-untyped-call]
cli.py:467: Call to untyped function "add_docs_subparser" in typed context  [no-untyped-call]
cli.py:468: Call to untyped function "add_template_subparser" in typed context  [no-untyped-call]
cli.py:478: Call to untyped function "process_common_options" in typed context  [no-untyped-call]
cli.py:487: Call to untyped function "main_cli" in typed context  [no-untyped-call]
cli.py:497: Call to untyped function "run_cli_app" in typed context  [no-untyped-call]
```

- [ ] **Step 1: Remove the entry**

Delete the line `  "voc4cat.cli",` from the `module = [...]` list in `pyproject.toml`. The list is now empty.

- [ ] **Step 2: Run the checker**

Run: `just typecheck`
Expected: FAIL with the 23 errors above.

- [ ] **Step 3: Annotate the parser builders first**

The `add_*_subparser` and `create_*_parser` functions take and return argparse
objects. Annotate these before the functions that call them so the
`no-untyped-call` errors clear as you go:

```python
def add_transform_subparser(
    subparsers: argparse._SubParsersAction, common: argparse.ArgumentParser
) -> None:
```

Check the real parameters before copying that signature; it is the shape, not a
verbatim answer. `argparse._SubParsersAction` is private but is the type
argparse actually returns from `add_subparsers()`; use it with a short comment
rather than falling back to `Any`.

- [ ] **Step 4: Annotate the command handlers and entry points**

`main_cli` and `run_cli_app` are the console-script entry points declared in
`pyproject.toml`. Give `run_cli_app` the return type the script wrapper needs.

- [ ] **Step 5: Verify green, tests and lint**

Run: `just typecheck && just test && uv run ruff check src/`
Expected: `Success: no issues found in 23 source files`, suite passes, and ruff still at its 62-finding baseline (no new findings).

- [ ] **Step 6: Verify the CLI still runs**

Run: `uv run voc4cat --help`
Expected: usage text, exit status 0.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/voc4cat/cli.py
git commit -m "Type cli module"
```

---

### Task 18: Remove the burn-down list and ship the PEP 561 marker

**Files:**
- Create: `src/voc4cat/py.typed`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: every preceding task.
- Produces: a package that advertises its annotations to downstream consumers.

- [ ] **Step 1: Delete the now-empty override table**

Remove the whole block from `pyproject.toml`, including its comment:

```toml
# Burn-down list: modules still to be annotated for issue #362. ...
[[tool.zuban.overrides]]
module = [
]
ignore_errors = true
```

`[tool.zuban]` keeps `mode`, `ignore_missing_imports`, `strict`,
`implicit_reexport` and `disallow_untyped_decorators`.

- [ ] **Step 2: Verify the strict configuration is green with no overrides at all**

Run: `just typecheck`
Expected: `Success: no issues found in 23 source files`

This is the moment the ratchet actually closes. If anything fails here, a
previous task left an override entry in place rather than fixing the module.

- [ ] **Step 3: Add the PEP 561 marker**

```bash
touch src/voc4cat/py.typed
```

The file is intentionally empty. `[tool.hatch.build.targets.wheel]` already
declares `packages = ["src/voc4cat"]`, so hatchling includes it in the wheel.

- [ ] **Step 4: Verify the marker reaches the built wheel**

```bash
uv build --wheel
python -c "import zipfile,glob; print([n for n in zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist() if 'py.typed' in n])"
```

Expected: `['voc4cat/py.typed']`

If the list is empty, add an explicit `include` for it under
`[tool.hatch.build.targets.wheel]` and re-check.

- [ ] **Step 5: Verify the hook, tests and lint**

Run: `pre-commit run --all-files && just test && uv run ruff check src/`
Expected: all hooks pass, suite passes, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/voc4cat/py.typed
git commit -m "Close the typing ratchet and ship py.typed"
```

- [ ] **Step 7: Update the changelog**

Add an entry to `CHANGELOG.md` describing the change at the level of intent:
the package is now fully annotated and type checked under a strict zuban
configuration, enforced by a pre-commit hook, and ships `py.typed`.

```bash
git add CHANGELOG.md
git commit -m "Update changelog for typing support"
```

---

## Done criteria

- `just typecheck` prints `Success: no issues found in 23 source files` with no
  `[[tool.zuban.overrides]]` table present.
- `pre-commit run --all-files` passes, including the `zuban` hook.
- `just test` passes and `uv run ruff check src/` reports no more than the 62-finding pre-existing baseline.
- `src/voc4cat/py.typed` exists and is present in the built wheel.
- Every function in `src/voc4cat` has a complete signature.
- Any behaviour bug found along the way was reported separately with a test,
  not folded into a typing commit.
