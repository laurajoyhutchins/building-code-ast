# ASHRAE 90.1-2016 publication root

This file establishes a durable branch point for work specific to ANSI/ASHRAE/IES Standard 90.1-2016.

## Source artifact

- publication key: `ashrae-90.1-2016`
- expected private filename: `ashrae-90_1-2016.pdf`
- observed artifact size: 3,475,675 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, rights classification, and included-addenda state must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own ASHRAE 90.1-specific source characterization, document AST extraction, definitions and references, tables and figures, equations, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new ASHRAE 90.1-specific work should branch from `root/ashrae-90.1-2016`. After it lands, descendants may be rebased or retargeted onto the merged root.

## Knowledge bootstrap

LORE bootstrap starts from `.lore/tasks/bootstrap-ashrae-90.1-2016-publication.yaml`. Accepted LORE records remain deferred until durable merge evidence exists.

Deciduous handoff metadata:

- semantic ID: `action.establish-ashrae90-1-2016-publication-root`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/ashrae-90.1-2016/README.md`
- causal context: `decision.family-grammar-boundary`

This is handoff metadata, not a canonical Deciduous patch. Materialize it into `.deciduous/patches/` and regenerate the shared archaeology projections only after integration evidence is available.
