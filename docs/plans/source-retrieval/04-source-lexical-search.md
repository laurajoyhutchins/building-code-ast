# Source lexical search

Status: scope-only stacked PR stub.

Purpose: deliver the first useful retrieval capability over the local evidence store, using SQLite FTS where supported.

Owns exact/token/phrase search, publication filters, deterministic result shape, and retrieval-score metadata.

Excludes semantic search, AST confidence, and publication interpretation.

Completion: a developer can locate source regions by identifiers or phrases and receive exact evidence provenance.

Predecessor: `feature/source-evidence-store`.
Successors: `feature/source-context-navigation` and `feature/source-structural-metadata`.
