# Source semantic index

Status: scope-only stacked PR stub.

Purpose: add optional local semantic candidate retrieval over existing evidence identities only after Phase 1 proves useful.

Owns embedding records, model/configuration identity, vector dimensions, index versioning, and invalidation rules.

Excludes changing source extraction, evidence identity, source authority, or requiring a remote embedding service.

Completion: a known evidence block can retrieve plausible differently worded analogues while preserving exact evidence provenance.

Predecessor: `feature/source-retrieval-phase-1` after its value gate.
Successor: `feature/source-hybrid-search`.
