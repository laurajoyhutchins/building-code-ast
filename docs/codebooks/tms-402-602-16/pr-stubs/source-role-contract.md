# TMS 402-16 source-role contract

Status: draft PR scaffold; implementation not started.

## Purpose

Preserve publication-defined source roles so normative TMS 402 text, informational commentary, publication apparatus, page furniture, and unresolved/ambiguous regions cannot collapse into one anonymous text stream.

## Scope

- closed source-role representation suitable for TMS 402 exact-source observations
- normative versus commentary distinction
- publication apparatus and page-furniture handling
- explicit ambiguous/unresolved source-role state
- role-preserving serialization, validation, and deterministic identity behavior
- source-safe synthetic tests plus private exact-source replay

## Boundaries

Do not decide project applicability, promote commentary to governing text, add TMS 602 parsing, or infer roles from modal vocabulary alone.

## Completion gate

Every TMS 402 observation consumed by later hierarchy work carries an explicit validated role or explicit ambiguity. Remove this scaffold file when implementation replaces it.
