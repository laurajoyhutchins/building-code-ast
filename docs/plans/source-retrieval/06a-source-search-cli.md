# Source search CLI

Status: implemented on this branch.

## Purpose

Expose the local retrieval stack through the existing `building-code-ast` executable so parser and AST work can index, search, inspect, and validate source evidence without direct Python or SQLite access.

## Command surface

The existing `parse` command remains unchanged. A new `source` command family adds:

- `source index`: verify exact PDF bytes, extract positioned layout, project `SourceEvidence`, and atomically rebuild the local store
- `source search`: lexical exact/phrase/token retrieval with provenance-rich JSON results
- `source show`: exact evidence-ID lookup with bounded neighboring context
- `source page`: deterministic physical-PDF page evidence retrieval
- `source status`: validate the requested artifact against the store and report store version/evidence count

Every source command requires explicit exact artifact identity: source ID, retrieval publication key, SHA-256, byte size, and physical page count.

## Output boundary

Source commands emit JSON only, with optional compact formatting. Output preserves exact retrieval provenance and retrieval-score metadata where applicable. It does not promote lexical relevance into semantic confidence or AST authority.

Indexing composes existing verified layers in order: exact-byte verification -> positioned PDF extraction -> retrieval evidence projection -> atomic evidence-store rebuild. The CLI does not duplicate those implementations.

## Excludes

- a second standalone retrieval executable
- semantic/vector search
- embeddings
- AST confidence or semantic promotion
- direct SQLite mutation commands
- source-authority or rights decisions

## TDD evidence

RED head: `3d83d5f9721ff3f092919670c69c9f1bc370a07e`.

At RED, the inherited retrieval stack and existing `parse` command remained green. The new CLI tests failed because the `source` command family and CLI PDF-reader import did not yet exist.

First GREEN implementation head: `8ff022fbd416d219da95c5738f1382e4ac8f2c3a`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

Behavioral coverage includes indexing through exact-byte verification and positioned extraction, search/show/page/status JSON output, provenance preservation, compact JSON, and existing parse-command compatibility.

## Stack

Predecessor: `feature/source-context-navigation` / PR #92.

Sibling dependency before Phase 1 closeout: `feature/source-structural-search` / PR #96.
