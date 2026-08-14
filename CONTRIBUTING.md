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

Before changing architecture, component boundaries, decisions, constraints, findings, relationships, or maintenance procedures, read `skills/maintain-repository-documentation/SKILL.md` and evaluate the documentation impact.

The LORE maintenance workflow is:

1. generate a bounded maintainer context packet for the task;
2. use the shipped maintenance skill to produce exactly one `lore-proposal/v1` artifact;
3. cite repository evidence at full Git commit SHAs;
4. validate the proposal with LORE;
5. apply it through LORE's transaction engine;
6. validate accepted records and check deterministic projections.

Do not directly edit:

- `.lore/extracted/`;
- `.lore/records/`;
- `.lore/transactions/`;
- `docs/generated/`.

Accepted semantic history is append-only. Reuse stable record IDs, append the next positive revision, and preserve uncertainty rather than inventing evidence.

## Verification

Run:

```bash
python tools/run_unit_tests.py
python -m compileall -q src tests
```

`python tools/run_unit_tests.py` is the repository's unit-test authority. It first fails closed on module-level `test*` functions that standard-library `unittest` discovery would silently ignore, then executes `unittest` discovery. Tests under `tests/` should use `unittest.TestCase` methods named `test*` rather than pytest-style module functions.

The pinned LORE verification lane runs:

```text
lore extract --check
lore validate
lore project --check
```

Pull requests should report the exact commands actually run and must not claim validation that was not performed.

## Corpus changes

Every non-synthetic source addition must satisfy `docs/corpus-policy.md`. Do not place licensed model-code or standards text in issues, pull requests, fixtures, or generated snapshots merely for convenience.

## Public communication

Repository discussion should contain only repository-facing technical context, evidence, decisions, risks, and next actions. Internal scheduling, agent orchestration, private coordination, and unrelated portfolio state do not belong in this public repository.
