# TMS 602-16 reference target index

Status: draft PR scaffold; implementation not started.

## Purpose

Provide the minimum TMS 602 publication-native target identity needed to resolve TMS 402 -> TMS 602 references without pretending TMS 602 is fully parsed.

## Scope

- explicit `tms-602-16` publication-component identity
- source-backed publication-native target locators
- target existence and exact artifact coordinates
- deterministic target IDs
- unsupported/ambiguous target diagnostics
- no copied TMS 602 prose

## Boundaries

This is not a TMS 602 Document AST implementation, semantic parser, definition import, or combined-TMS flattening layer.

## Completion gate

TMS 402 cross-publication references can resolve to stable TMS 602-owned targets or explicit unresolved states without reconstructing TMS 602 content. Remove this scaffold file when implementation replaces it.
