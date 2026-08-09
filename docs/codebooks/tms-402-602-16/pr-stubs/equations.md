# TMS 402-16 equation structures

Status: draft PR scaffold; implementation not started.

## Purpose

Represent TMS 402 equations as first-class source structures before any mathematical or engineering semantics are asserted.

## Scope

- equation-region detection and grouping
- publication-native equation identifiers
- source geometry and OCR provenance
- displayed notation and multi-line equation structure
- symbol/unit candidates with explicit unresolved state
- unsupported mathematical-region diagnostics
- measured exact-source coverage against the structural inventory

## Boundaries

Do not create executable masonry calculations, silently normalize mathematics, infer applicability, or promote commentary derivations to normative equations.

## Completion gate

Measured TMS 402 equation regions are structurally represented or explicitly unsupported with stable identity and exact provenance. Remove this scaffold file when implementation replaces it.
