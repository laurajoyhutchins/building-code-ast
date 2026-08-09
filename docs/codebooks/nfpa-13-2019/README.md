# NFPA 13 (2019) publication root

This file establishes a durable branch point for work specific to NFPA 13 (2019).

## Source artifact

- publication key: `nfpa-13-2019`
- expected private filename: `nfpa-2019.pdf`
- observed artifact size: 49,070,148 bytes
- media type: `application/pdf`
- source bytes remain outside Git

Existing NFPA 13 hierarchy, bundle, reviewed-case, relationship, and provenance work remains authoritative for its current contracts. This root does not duplicate or reinterpret that work.

## Scope

Descendant pull requests may own NFPA 13-specific source characterization, hierarchy improvements, references, tables, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim new parser coverage, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new NFPA 13-specific work should branch from `root/nfpa-13-2019`. After it lands, descendants may be rebased or retargeted onto the merged root.