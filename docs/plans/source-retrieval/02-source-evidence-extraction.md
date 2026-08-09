# Source evidence extraction

Status: implemented on this branch.

## Purpose

Produce deterministic source-evidence records from exact verified PDF artifacts by projecting the repository's existing positioned-PDF layout observations into the shared retrieval evidence contract.

This stage does not reinterpret or normalize source expression. It verifies source bytes separately and preserves the `PdfBlock` text, bounding box, physical PDF page, and extractor block number as retrieval evidence.

## Owns

- exact source-artifact byte verification against retrieval artifact size and SHA-256
- exact page-count agreement between the verified artifact identity and positioned layout
- deterministic page ordering by physical PDF page number
- deterministic block ordering by extractor-assigned block number
- raw block text and bounding-box preservation
- extraction backend identity
- optional printed-page labels that do not alter evidence identity
- generation of the shared `SourceEvidence` contract from existing `PdfLayoutDocument` / `PdfBlock` observations
- fail-closed duplicate page/block and page-membership validation

## Identity boundary

This PR does not assign new source identities. Evidence identity remains defined by PR #88 from exact artifact digest plus physical source coordinates.

Changing printed-page labels or discovery tuple ordering does not change evidence IDs. Changing exact source bytes, PDF page, block number, or bounding box does.

## Excludes

- text normalization, page-furniture filtering, or reading-order inference
- search/index storage
- semantic or publication-specific classification
- AST construction
- private extracted corpora in Git
- embeddings or ranking

## TDD evidence

Corrected RED head: `13b6cc7694a0004a777b5ddba106abb14b1abd52`.

At that head, the existing suite remained green and CI failed only because `building_code_ast.retrieval.extraction` did not yet exist.

First GREEN implementation head: `bf21382379f0f989e09e62c869109617bf1a86f7`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

The behavioral tests cover deterministic output under page/block discovery reordering, raw text/bbox preservation, printed-page annotation without identity churn, page-count and page-membership failure, duplicate coordinate failure, and exact-byte verification.

## Private-source boundary

No private PDF bytes or extracted source corpus are committed. The byte-verification hook is designed for later private replay against already registered artifacts without making the retrieval layer a second source authority.

## Stack

Predecessor: `feature/source-evidence-contract` / PR #88.

Successor: `feature/source-evidence-store` / PR #90.
