# TMS 402-16 reviewed rule corpus

Status: draft PR scaffold; implementation not started.

## Purpose

Join independently reviewed semantic lanes into a source-safe corpus of reviewed TMS 402 semantic outputs without turning partial review into a broad support claim.

## Required evidence joins

Before this PR can land as the reviewed-rule corpus, integrate or rebase onto completed evidence from:

- `tms-402-16/applicability-semantics`
- `tms-402-16/table-semantics`
- `tms-402-16/equation-semantics`
- `tms-402-16/definition-reference-review`

## Scope

- reviewed semantic output identity and provenance
- review/approval state distinct from generated candidates
- contrasting rule families and explicit family coverage
- source-safe reviewed fixtures/cases and aggregate counts
- links back to structural nodes, definitions, references, tables, and equations
- unsupported/ambiguous semantic registry

## Boundaries

Do not publish protected source reconstruction, equate reviewed samples with whole-publication semantic coverage, or perform project compliance evaluation.

## Completion gate

A bounded, source-safe set of reviewed TMS 402 semantic outputs spans contrasting rule families with exact provenance and explicit review state. Remove this scaffold file when implementation replaces it.
