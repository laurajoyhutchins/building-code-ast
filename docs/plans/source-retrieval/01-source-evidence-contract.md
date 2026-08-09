# Source evidence contract

Status: implemented on this branch.

## Purpose

Define the shared, publication-neutral source-evidence contract used by local retrieval tooling without adding indexing, search, embeddings, or publication semantics.

The existing `building_code_ast.evidence` source register remains authoritative for provenance, rights, and publication state. Retrieval consumes that authority rather than creating a parallel source registry.

## Owns

- retrieval-local source artifact coordinates (`source_id`, `publication_key`, SHA-256, byte size, page count)
- deterministic evidence identity from exact artifact digest plus PDF page, block index, and bounding box
- page/block/source-coordinate vocabulary
- explicit observed-metadata versus derived-metadata namespaces
- immutable canonicalized metadata storage
- fail-closed serialization and validation contracts
- synthetic tests for identity stability, source mismatch, coordinate validation, and metadata separation

`source_id` is the provenance link to the existing source register when the artifact is registered there. `publication_key` is a retrieval filter and does not independently assert publication authority.

Evidence identity deliberately excludes extracted text, extraction-method identity, metadata, search rank, and semantic interpretation. Re-extracting the same physical source region therefore does not create a new evidence identity merely because retrieval implementation details changed.

## Excludes

- private source text or generated retrieval corpora in Git
- source-registration replacement or rights modeling
- search/index storage
- semantic classification
- AST node production
- publication-specific parser behavior
- retrieval confidence or ranking

## Completion criteria

The same exact artifact and source coordinates reproduce the same evidence ID; a different exact source digest cannot masquerade as the same evidence; source observations remain distinguishable from derived retrieval features; invalid artifact/page/geometry inputs fail closed.

## TDD evidence

The corrected RED head is `bda0167a6cb521d3b6113d829b485e48815901e6`. Its net diff adds only the retrieval-contract tests, and CI fails at the expected missing `building_code_ast.retrieval` import.

The first GREEN implementation head is `91c651a2223941b11628a942ae5541abf487744a`. CI, LORE, and Deciduous archaeology all pass on that exact head.

## Stack

Base: `main`.

Successor: `feature/source-evidence-extraction`.
