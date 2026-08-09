# Source evidence store

Status: implemented on this branch.

## Purpose

Persist extracted retrieval evidence as disposable local derived state using standard-library SQLite. The database is a rebuildable projection, not a source of authority.

## Owns

- store schema version `source-evidence-store/0.1.0`
- one exact-artifact manifest containing source ID, retrieval publication key, SHA-256, byte size, page count, and evidence count
- complete `SourceEvidence` persistence, including source coordinates, raw text, extraction method, printed-page label, and observed/derived metadata
- deterministic source-order reads by PDF page, block index, and evidence ID
- atomic replacement-style rebuilds rather than incremental merging
- source-identity checks before writes
- manifest checks before reads
- reconstruction through the shared `SourceEvidence` validator so persisted evidence-ID tampering fails closed

## Derived-state boundary

The SQLite database is intentionally disposable. Rebuilding from the same exact artifact and evidence records reproduces the same evidence identities regardless of input tuple ordering.

The store does not establish source authority, publication state, rights, semantic truth, or parser correctness. Those remain outside this derived persistence layer.

## Excludes

- committed private database artifacts
- append/merge semantics that allow stale evidence to survive a rebuild
- retrieval ranking or lexical query behavior
- embeddings
- AST semantics
- source registration

## TDD evidence

RED head: `80e17dbfb0b35f80f2140780786dbe4038cf1f30`.

At RED, all inherited tests passed and CI failed only because `building_code_ast.retrieval.store` did not yet exist.

First GREEN implementation head: `b1f44a54ff78d13aa5f36bd87c1133ec68b07a74`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

Behavioral coverage includes deterministic round-trip ordering, replacement-style rebuilds, foreign-source rejection, artifact-manifest mismatch rejection, schema-version visibility, and detection of tampered persisted evidence IDs.

## Stack

Predecessor: `feature/source-evidence-extraction` / PR #89.

Successor: `feature/source-lexical-search` / PR #91.
