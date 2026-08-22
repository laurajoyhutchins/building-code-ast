# Contributing

## Before changing the AST

Changes to the public AST contract require:

1. a documented use case;
2. schema and runtime-model updates;
3. reviewed synthetic fixtures;
4. provenance-invariant tests;
5. compatibility notes or an AST version change.

Do not add a field solely because one example is difficult to parse. Prefer a small, coherent vocabulary that can preserve uncertainty.

## Repository knowledge changes

Reviewed repository knowledge lives in `.lore/knowledge/`. Edit it directly in the same Git branch as the repository change it documents. Cite stable repository evidence paths, run LORE validation, and review the result through the normal Git pull-request workflow.

Generated files under `docs/lore/` are non-authoritative projections. Do not hand-edit them; regenerate them with LORE after changing reviewed knowledge. There is no LORE proposal, apply, transaction, receipt, or append-only semantic-history workflow.

## Verification

Run:

```bash
python tools/run_unit_tests.py
python -m compileall -q src tests
```

`python tools/run_unit_tests.py` is the repository's unit-test authority. It first fails closed on module-level `test*` functions that standard-library `unittest` discovery would silently ignore, then executes `unittest` discovery. Tests under `tests/` should use `unittest.TestCase` methods named `test*` rather than pytest-style module functions.

CI also runs the pinned LORE documentation checks:

```text
lore validate .
lore project . --check
```

Pull requests should report the exact commands actually run and must not claim validation that was not performed.

## Corpus changes

Every non-synthetic source addition must satisfy `docs/corpus-policy.md`. Do not place licensed model-code or standards text in issues, pull requests, fixtures, or generated snapshots merely for convenience.

## Public communication

Repository discussion should contain only repository-facing technical context, evidence, decisions, risks, and next actions. Internal scheduling, agent orchestration, private coordination, and unrelated portfolio state do not belong in this public repository.
