# NEC 2017 publication root

This file establishes a durable branch point for work specific to the 2017 National Electrical Code publication family.

## Source artifact

- publication key: `nec-2017`
- expected private filename: `nec-2017.pdf`
- observed artifact size: 7,422,245 bytes
- media type: `application/pdf`
- source bytes remain outside Git

Existing NEC 2017 ingestion, hierarchy, definition, and selected semantic work remains authoritative for its current contracts. This root does not duplicate or reinterpret that work.

## Scope

Descendant pull requests may own NEC-specific source characterization, hierarchy improvements, definitions and references, selected provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim new parser coverage, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new NEC-specific work should branch from `root/nec-2017`. After it lands, descendants may be rebased or retargeted onto the merged root.