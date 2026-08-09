# Source structural search

Status: implemented and converged with the landed retrieval trunk.

## Purpose

Compose lexical retrieval with publication-neutral source-observation constraints without changing lexical scores or assigning semantic confidence.

## Owns

`structural_search_evidence_store()` composes the existing lexical evidence-store search with typed structural filters for:

- PDF page ranges;
- observed font size;
- derived relative font size;
- publication-neutral heading, table, figure, and equation candidates.

Filtering is applied to the complete lexical match set before the caller result limit. Missing metadata does not satisfy a requested numeric filter. Malformed candidates, page ranges, and numeric ranges fail closed.

The result remains the existing `LexicalSearchResult`; retrieval score and score method are preserved unchanged.

## TDD and verification coordinates

RED head: `76248ae9a8e2418e5a82a615c46c90e4bb19fd38`.

First GREEN implementation head: `befc361b04ddab093517545b198a75760514fe1a`.

The implementation was then explicitly converged with current `main`, including the independently landed CLI and structural-metadata work, rather than carrying the stale stacked snapshot forward.

## Boundaries

- no publication-specific meaning;
- no semantic/vector ranking;
- no AST construction;
- no requirement, exception, or definition inference;
- no source-authority model;
- no conversion of structural candidates into parser confidence.

## Dependency

Real predecessor: merged structural metadata PR #95.

Independent retrieval CLI PR #94 is also landed before Phase 1 closeout.

The old planning-only Phase 1 closeout PR #97 and optional #98-#100 branches remain retired. Any later closeout should be opened freshly from measured repository/source evidence.
