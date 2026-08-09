# TMS 402-16 semantic candidate layer

Status: draft PR scaffold; implementation not started.

## Purpose

Generate reviewable semantic candidates from structurally closed TMS 402 nodes while preserving the boundary between generated interpretation and reviewed meaning.

## Scope

- source-node and exact-provenance binding
- candidate interpretation identity
- candidate type/family and producer identity
- uncertainty, diagnostics, and unsupported state
- review lifecycle/state without automatic approval
- links to structural definitions, references, tables, equations, and figures where relevant

## Boundaries

Do not treat parser output as reviewed, execute masonry design calculations, decide project compliance, or erase source-role/component distinctions.

## Completion gate

Selected TMS 402 structural nodes can produce deterministic, provenance-bound semantic candidates whose review state is explicit and never implies approval by generation alone. Remove this scaffold file when implementation replaces it.
