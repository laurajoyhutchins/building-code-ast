# Source evidence store

Status: scope-only stacked PR stub.

Purpose: persist extracted evidence as disposable local derived state using standard-library SQLite first.

Owns local schema/versioning, artifact/evidence tables, manifest, rebuild behavior, and source-identity checks.

Excludes committed private databases, retrieval ranking, and AST semantics.

Completion: rebuilding from the same verified source reproduces the same evidence identities.

Predecessor: `feature/source-evidence-extraction`.
Successor: `feature/source-lexical-search`.
