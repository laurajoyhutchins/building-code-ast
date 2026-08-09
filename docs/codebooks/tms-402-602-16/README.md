# TMS 402/602-16 publication root

This file establishes a durable branch point for work specific to the TMS 402/602-16 publication family.

## Source artifact

- publication key: `tms-402-602-16`
- expected private filename: `tms-402_602-2016.pdf`
- observed artifact size: 53,081,346 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, rights classification, and the boundary between TMS 402 and TMS 602 content must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own TMS-specific source characterization, document AST extraction, definitions and references, tables and figures, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new TMS-specific work should branch from `root/tms-402-602-16`. After it lands, descendants may be rebased or retargeted onto the merged root.

## Knowledge bootstrap

LORE bootstrap starts from `.lore/tasks/bootstrap-tms-402-602-16-publication.yaml`. Accepted LORE records remain deferred until durable merge evidence exists.

Deciduous handoff metadata:

- semantic ID: `action.establish-tms402-602-16-publication-root`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/tms-402-602-16/README.md`
- causal context: `decision.family-grammar-boundary`

This is handoff metadata, not a canonical Deciduous patch. Materialize it into `.deciduous/patches/` and regenerate the shared archaeology projections only after integration evidence is available.
