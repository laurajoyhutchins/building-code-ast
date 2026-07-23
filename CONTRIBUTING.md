# Contributing

## Before changing the AST

Changes to the public AST contract require:

1. a documented use case;
2. schema and runtime-model updates;
3. reviewed synthetic fixtures;
4. provenance-invariant tests;
5. compatibility notes or an AST version change.

Do not add a field solely because one example is difficult to parse. Prefer a small, coherent vocabulary that can preserve uncertainty.

## Verification

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Pull requests should report the exact commands actually run and must not claim validation that was not performed.

## Corpus changes

Every non-synthetic source addition must satisfy `docs/corpus-policy.md`. Do not place licensed model-code or standards text in issues, pull requests, fixtures, or generated snapshots merely for convenience.

## Public communication

Repository discussion should contain only repository-facing technical context, evidence, decisions, risks, and next actions. Internal scheduling, agent orchestration, private coordination, and unrelated portfolio state do not belong in this public repository.
