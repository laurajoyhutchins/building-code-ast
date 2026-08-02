# NEC Definition Index Reference

The NEC definition index is a versioned, provenance-preserving projection of definition entries extracted from an ArticleSeed document AST. Version `0.1.0` is intentionally conservative: it structures evidence that is visible in the source without asserting an electrical ontology or a universal term meaning.

## Contract

A definition index contains the exact normalized Article 100 source text, immutable source artifact and edition identity, the article locator, structured entries, and diagnostics. Every span addresses `source_text` exactly.

Each entry records:

- a deterministic `necdef:<sha256>` identity derived from artifact, edition, and source locator;
- the display and canonical term;
- alternate parenthetical terms when explicitly present;
- applicability and numeric scope qualifiers;
- body, continuation, and list-item fragments;
- separately attached informational notes;
- code-making-panel markers;
- explicit section, article, and table references;
- the complete source span and any extraction diagnostics.

The index does not silently merge definitions, infer synonyms, resolve conflicts across contexts, or decide which definition applies to a project. Context-sensitive definition resolution remains a later reviewed stage.

## Invariants

- Every entry and attachment round-trips to the exact source text.
- Entry identities are stable for the same artifact, edition, and locator.
- Entry spans contain their terms, qualifiers, fragments, notes, panel markers, references, and diagnostics.
- Source order is preserved.
- Unsupported structures remain visible through diagnostics rather than guessed.

The JSON projection is specified by `schemas/nec-definition-index.schema.json`.
