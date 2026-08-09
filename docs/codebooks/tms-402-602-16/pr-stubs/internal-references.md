# TMS 402-16 internal reference graph

Status: draft PR scaffold; implementation not started.

## Purpose

Resolve TMS 402 references to TMS 402-owned structural targets while preserving exact mention spans, target type, edition/component identity, and unresolved states.

## Scope

- section/subsection references
- table, figure, equation, appendix, and definition references
- exact source mention spans and provenance
- deterministic target identity
- explicit unresolved and ambiguous targets
- same-component reference typing distinct from TMS 402 -> TMS 602 and external references
- measured exact-source coverage against the structural inventory

## Boundaries

Do not resolve TMS 602 or external targets here, copy referenced content, infer semantic dependency, or perform applicability analysis.

## Completion gate

Measured same-component TMS 402 reference families are detected and resolved where supported, with unresolved/ambiguous cases preserved explicitly. Remove this scaffold file when implementation replaces it.
