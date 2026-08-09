# TMS 402-16 cross-publication and external references

Status: draft PR scaffold; implementation not started.

## Purpose

Extend the TMS 402 reference graph beyond same-component targets while retaining source and target publication identity, edition scope, exact mention spans, and resolution state.

## Scope

- TMS 402 -> TMS 602 reference typing and resolution
- TMS 402 -> external-standard reference classification
- source publication, source locator/span, target publication, target locator, and edition scope
- deterministic resolved targets and explicit unresolved/ambiguous state
- no copied referenced prose
- measured exact-source coverage

## Dependencies

Requires the TMS 402 internal-reference lane and the minimal `tms-602-16/reference-target-index` sibling prerequisite before TMS 402 -> TMS 602 targets can be claimed resolved.

## Boundaries

Do not import external standards, copy TMS 602 content, flatten cross-document edges into same-document links, or infer project applicability.

## Completion gate

Measured TMS 402 cross-publication/external reference families are explicitly typed and resolved where supported, with publication/edition identity and unresolved states intact. Remove this scaffold file when implementation replaces it.
