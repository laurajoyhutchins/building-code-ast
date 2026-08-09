# Source context navigation

Status: scope-only stacked PR stub.

Purpose: expand a retrieval hit deterministically into neighboring evidence and page-local context.

Owns lookup by evidence ID, page retrieval, previous/next block ranges, and deterministic context expansion.

Excludes fuzzy re-search, semantic ranking, and AST interpretation.

Completion: a hit can be inspected with surrounding source evidence while preserving identities and coordinates.

Predecessor: `feature/source-lexical-search`.
Successor: `feature/source-search-cli`.
