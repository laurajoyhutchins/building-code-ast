# Source evidence extraction

Status: scope-only stacked PR stub.

## Purpose

Produce deterministic source-evidence records from verified private PDFs using existing positioned-PDF capabilities.

## Owns

- page iteration and deterministic block ordering
- text and bounding-box preservation
- extraction backend identity
- source-artifact verification hook
- generation of the shared evidence contract

## Excludes

- search/index storage
- semantic or publication-specific classification
- AST construction
- private extracted corpora in Git

## Completion criteria

Repeated extraction of the same verified artifact yields identical evidence ordering and identities. Private replay should use an already verified publication source without committing source expression.

## Stack

Predecessor: `feature/source-evidence-contract`.

Successor: `feature/source-evidence-store`.
