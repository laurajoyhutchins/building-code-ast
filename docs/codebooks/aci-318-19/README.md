# ACI 318-19 publication root

This file establishes a durable branch point for work specific to ACI 318-19.

## Source artifact

- publication key: `aci-318-19`
- expected private filename: `aci-318-2019.pdf`
- observed artifact size: 10,010,981 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, rights classification, and any normative-versus-commentary boundaries must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own ACI-specific source characterization, document AST extraction, definitions and references, tables and figures, equations, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new ACI-specific work should branch from `root/aci-318-19`. After it lands, descendants may be rebased or retargeted onto the merged root.

## Knowledge bootstrap

LORE bootstrap starts from `.lore/tasks/bootstrap-aci-318-19-publication.yaml`. Accepted LORE records remain deferred until durable merge evidence exists.

Deciduous handoff metadata:

- semantic ID: `action.establish-aci318-19-publication-root`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/aci-318-19/README.md`
- causal context: `decision.family-grammar-boundary`

This is handoff metadata, not a canonical Deciduous patch. Materialize it into `.deciduous/patches/` and regenerate the shared archaeology projections only after integration evidence is available.
