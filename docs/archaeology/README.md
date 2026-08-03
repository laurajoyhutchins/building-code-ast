# Archaeology overview

## Why Building Code AST exists

Building Code AST exists because a building code is not adequately represented by a search index, a RAG corpus, a summary, or a PDF text dump. Downstream systems need stable provision identities, parent-child structure, exact source spans, code-family grammar, diagnostics, and source-edition provenance. The repository therefore evolved into a staged compiler:

```text
source artifact and publication state
  -> layout and source-location evidence
  -> publication-structure Document AST
  -> source-family hierarchy
  -> selected semantic projections
  -> validation and diagnostics
  -> downstream graphs, comparisons, amendments, and products
```

The AST is a technical representation. It does not become authoritative legal text, establish jurisdictional adoption, or determine compliance.

## Canonical graph

The canonical source is nine lexicographically ordered, upstream-compatible Deciduous patch files under `.deciduous/patches/`. They use stable UUIDv5 change IDs, canonical Deciduous node and edge types, exact evidence references, and lifecycle metadata that distinguishes active, edition-specific, branch-only, proposed, rejected, and unresolved decisions.

Generated views include:

- `.deciduous/exports/building-code-ast-archaeology.json`: Deciduous GraphData export;
- `graph.dot`: full causal graph;
- `current-architecture.json`: nodes still governing the repository or its active boundaries;
- `status-summary.json`: counts by arc, lifecycle, and support scope;
- `manifest.json`: patch order, upstream pin, and deterministic hashes.

## Major findings

The earliest useful semantic provision slice did not generalize into a universal document model. It instead exposed the need for a separate Document AST. Real NEC ingestion then showed that PDF blocks are layout evidence rather than hierarchy. NEC hierarchy reconstruction required an NEC grammar, an edition-aware style profile, and a private hierarchy oracle used only for conformance. IBC revealed more severe reading-order, glyph, table, figure, definition, and decimal-numbering behavior, confirming that shared primitives do not imply a shared grammar. NFPA 13 further introduced annex correspondence, external-standard target domains, and unsupported figure semantics.

Current `main` supports shared AST contracts, selected 2017 NEC workflows for Articles 90, 100, and 110, and publication-neutral evidence adapters including ICC and Washington sources. IBC 2018, NFPA 13 2019, the NEC 2020 expected changelog, and Provision AST 0.3 remain open or branch-bound and are not current support.

## Evidence discipline

PR descriptions are treated as claims to reconcile, not proof. The graph distinguishes merged state from branch evidence and checks current paths locally. Private source documents, private links, source prose, credentials, and text-bearing generated artifacts are not included.

See the [root narratives](narratives.md), [current architecture](current-architecture.md), [parser-family evolution](parser-family-evolution.md), [source and provenance model](source-provenance.md), [validation strategy](validation-strategy.md), [downstream boundaries](downstream-boundaries.md), and [evidence gaps](evidence-gaps.md).
