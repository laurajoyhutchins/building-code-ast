# ASCE 7-22 publication root

This file establishes a durable branch point for work specific to ASCE 7-22.

## Source artifact

- publication key: `asce-7-22`
- expected private filename: `asce-7-2022.pdf`
- observed artifact size: 55,404,349 bytes
- media type: `application/pdf`
- source bytes remain outside Git

An exact SHA-256, page count, publication-state identity, and rights classification must be established from the retained artifact before durable ingestion claims are made.

## Scope

Descendant pull requests may own ASCE 7-specific source characterization, document AST extraction, definitions and references, tables and figures, equations, provision semantics, and reviewed rule slices. Generic compiler changes should remain independent when they are useful to more than this publication family.

## Status

This is an organizational root only. It does not claim parser support, corpus completeness, semantic correctness, publication safety, or legal interpretation.

While this root PR is open, new ASCE 7-specific work should branch from `root/asce-7-22`. After it lands, descendants may be rebased or retargeted onto the merged root.