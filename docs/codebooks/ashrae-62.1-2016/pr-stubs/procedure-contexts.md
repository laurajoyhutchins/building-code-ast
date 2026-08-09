# ASHRAE 62.1-2016 procedure contexts

Status: draft PR scaffold; implementation not started.

## Depends on

`ashrae-62.1-2016/publication-state-roles`

## Purpose

Preserve publication-defined procedure and method boundaries without performing project applicability evaluation.

## Scope

- Section 6.2 Ventilation Rate Procedure context
- Section 6.3 Indoor Air Quality Procedure context
- Section 6.4 Natural Ventilation Procedure context
- source conditions and hierarchy preserved as publication structure
- reuse existing hierarchy/metadata unless a genuine publication-neutral concept is missing

## Boundaries

Do not decide which procedure applies to a building, and do not introduce a generic `procedure` node solely for convenience.

## Completion gate

A deterministic structural fixture and private replay preserve all three procedure contexts without collapsing them into one requirement stream. Remove this scaffold when implementation replaces it.
