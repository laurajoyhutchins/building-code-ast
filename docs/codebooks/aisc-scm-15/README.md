# AISC Steel Construction Manual 15th Edition publication root

This file establishes a durable branch point for work specific to the AISC Steel Construction Manual, 15th Edition.

## Source artifact

- publication key: `aisc-scm-15`
- expected private filename: `scm-15.pdf`
- observed artifact size: 221,820,282 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, rights classification, and internal normative-versus-reference boundaries must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own AISC-specific source characterization, document structure, embedded specification boundaries, references, tables and figures, and selected semantics. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not treat the manual as one undifferentiated normative code and does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new AISC-specific work should branch from `root/aisc-scm-15`. After it lands, descendants may be rebased or retargeted onto the merged root.

## Knowledge bootstrap

LORE bootstrap starts from `.lore/tasks/bootstrap-aisc-scm-15-publication.yaml`. Accepted LORE records remain deferred until durable merge evidence exists.

Deciduous handoff metadata:

- semantic ID: `action.establish-aisc-scm15-publication-root`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/aisc-scm-15/README.md`
- causal context: `decision.family-grammar-boundary`

This is handoff metadata, not a canonical Deciduous patch. Materialize it into `.deciduous/patches/` and regenerate the shared archaeology projections only after integration evidence is available.
