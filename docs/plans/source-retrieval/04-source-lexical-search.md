# Source lexical search

Status: implemented on this branch.

## Purpose

Deliver the first directly useful retrieval capability over the validated local evidence store while keeping lexical relevance separate from source authority and AST semantics.

## Owns

- explicit `exact`, `phrase`, and `token` search modes
- case-sensitive literal identifier lookup for exact mode
- case-insensitive contiguous phrase lookup
- all-token retrieval using SQLite FTS5/BM25 when available
- deterministic token-coverage fallback when FTS5 is unavailable
- source-ID and retrieval publication-key filters
- deterministic physical source-order result emission
- provenance-rich `LexicalSearchResult` values containing the exact `SourceEvidence`
- explicit retrieval score and score-method metadata
- bounded result limits and fail-closed query/mode validation

## Retrieval-score boundary

Retrieval score describes only how a lexical candidate matched. It is not source authority, semantic confidence, AST confidence, or engineering correctness.

Results are therefore emitted in deterministic physical source order rather than silently treating backend ranking as authority. FTS/BM25 or fallback score remains visible metadata for later consumers that deliberately choose to use it.

## Excludes

- semantic/vector search
- embeddings
- AST confidence or semantic promotion
- publication interpretation
- automatic parser fixture promotion
- cross-artifact authority decisions

## TDD evidence

RED head: `2a90b1c7bbef8fa1d13142471bc978a526600bf9`.

At RED, 372 inherited tests passed and CI failed only because `building_code_ast.retrieval.search` did not yet exist.

First GREEN implementation head: `195616e59959ea32ca4364ec1f3bcfdd7c621ec3`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

Behavioral coverage includes literal identifier search with exact provenance, case-insensitive contiguous phrase search, token-order-independent all-token search, deterministic repeated results, source/publication filtering, bounded result shape, and explicit absence of semantic `confidence` / AST fields.

## Stack

Predecessor: `feature/source-evidence-store` / PR #90.

Successors: `feature/source-context-navigation` / PR #92 and `feature/source-structural-metadata` / PR #95.
