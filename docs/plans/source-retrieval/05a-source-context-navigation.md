# Source context navigation

Status: implemented on this branch.

## Purpose

Expand a known retrieval evidence identity deterministically into exact neighboring source evidence without issuing a fuzzy or semantic re-search.

## Owns

- exact lookup by durable evidence ID
- deterministic physical-PDF page retrieval
- bounded previous/next evidence expansion in source order
- explicit page-local context expansion that cannot cross a PDF-page boundary
- provenance-preserving context serialization through the underlying `SourceEvidence` values
- fail-closed missing identity, page-range, and context-bound validation

## Navigation boundary

Navigation follows the persisted source order established by the evidence store. It does not rerank, infer semantic relationships, interpret publication hierarchy, or fabricate missing context.

Cross-page context is explicit. Page-local mode is also explicit and guarantees that adjacent evidence from another PDF page is excluded.

## Excludes

- fuzzy re-search
- lexical re-ranking
- semantic/vector search
- AST interpretation
- publication hierarchy inference
- context summarization

## TDD evidence

RED head: `83072d0eb987e7ecb7900681e4aa1788adde2047`.

At RED, 378 inherited tests passed and CI failed only because `building_code_ast.retrieval.context` did not yet exist.

First GREEN implementation head: `c28fdab062771564c6fc05e62a5a6169e1a19897`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

Behavioral coverage includes exact evidence-ID lookup, deterministic page retrieval, bounded cross-page context, hard page-local context, provenance-preserving serialization, missing-ID failure, invalid-page failure, and invalid before/after ranges.

## Stack

Predecessor: `feature/source-lexical-search` / PR #91.

Successor: `feature/source-search-cli` / PR #94.
