# Source evidence contract

Status: scope-only stacked PR stub.

## Purpose

Define the shared, publication-neutral source-evidence contract used by retrieval tooling without adding indexing, search, embeddings, or publication semantics.

## Owns

- source artifact identity (`publication_key`, SHA-256, size, page count)
- deterministic evidence identity
- page/block/source-coordinate vocabulary
- source observation versus derived-feature boundary
- serialization and validation contracts
- synthetic tests for identity stability and source mismatch

## Excludes

- private source text in Git
- search/index storage
- semantic classification
- AST node production
- publication-specific parser behavior

## Completion criteria

The same verified artifact and source coordinates reproduce the same evidence IDs; a different source identity cannot masquerade as the same evidence; source observations remain distinguishable from parser or retrieval inference.

## Stack

Base: `main`.

Successor: `feature/source-evidence-extraction`.
