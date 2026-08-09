# IBC 2018 publication root

This file establishes a durable branch point for work specific to the 2018 International Building Code publication family.

## Source artifact

- publication key: `ibc-2018`
- expected private filename: `ibc-2018.pdf`
- observed artifact size: 32,608,171 bytes
- media type: `application/pdf`
- source bytes remain outside Git

The existing IBC 2018 corpus already binds its verified source artifact identity separately. This root does not replace or duplicate that contract.

## Scope

Descendant pull requests may own IBC-specific source characterization, document-structure extraction, references and definitions, tables and figures, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim new parser coverage, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new IBC-specific work should branch from `root/ibc-2018`. After it lands, descendants may be rebased or retargeted onto the merged root.

## Knowledge bootstrap

LORE bootstrap starts from `.lore/tasks/bootstrap-ibc-2018-publication.yaml`. Accepted LORE records remain deferred until durable merge evidence exists.

Deciduous handoff metadata:

- semantic ID: `action.establish-ibc2018-publication-root`
- node type: `action`
- arc: `ibc`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/ibc-2018/README.md`
- causal context: `decision.family-grammar-boundary`

This is handoff metadata, not a canonical Deciduous patch. Materialize it into `.deciduous/patches/` and regenerate the shared archaeology projections only after integration evidence is available.
