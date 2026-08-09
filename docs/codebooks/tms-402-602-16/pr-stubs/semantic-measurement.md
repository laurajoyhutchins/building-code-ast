# TMS 402-16 semantic measurement

Status: draft PR scaffold; implementation not started.

## Purpose

Measure generated, parsed, reviewed, unsupported, and ambiguous TMS 402 semantic coverage without conflating those compiler stages.

## Scope

- denominators for eligible normative semantic candidates
- generated-candidate counts
- automatically parsed semantic counts
- reviewed/approved counts
- unsupported and ambiguous counts
- coverage by major semantic family
- separate reporting for commentary/informational evidence
- deterministic repeated-run measurements

## Boundaries

Do not modify parsers merely to improve percentages, automatically approve generated semantics, or report project-compliance coverage.

## Completion gate

Semantic coverage is reproducibly measured with separate denominators and states for candidate, parsed, reviewed, unsupported, and ambiguous material. Remove this scaffold file when implementation replaces it.
