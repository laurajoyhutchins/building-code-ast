# NDS 2018 publication root

This file establishes a durable branch point for work specific to the NDS 2018 publication family.

## Source artifact

- publication key: `nds-2018`
- expected private filename: `nds-2018.pdf`
- observed artifact size: 6,791,825 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, and rights classification must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own NDS-specific source characterization, document AST extraction, definitions and references, tables and figures, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new NDS-specific work should branch from `root/nds-2018`. After it lands, descendants may be rebased or retargeted onto the merged root.