# IBC 2018 Corpus Closeout Design

## Purpose

Close the remaining acceptance gaps in the source-backed 2018 IBC corpus without turning provisional detection into asserted legal meaning. The exact user-supplied PDF remains private; committed artifacts retain only identifiers, geometry, hashes, constrained captions, review states, and correction history.

## Scope

The closeout has six independent lanes:

1. exact-environment verification and GitHub publication;
2. vector-only technical-graphic candidate detection;
3. deterministic internal-reference normalization and review classification;
4. external-reference alias reconciliation without semantic overclaiming;
5. reviewer workflow improvements for structural and semantic-pilot records;
6. provenance, coverage, and acceptance documentation.

Human semantic review cannot be manufactured by code. The implementation may prepare evidence packets, deterministic classifications, and review-state transitions, but may mark a record `verified` only when a source-backed rule or an explicit reviewed fixture establishes that state.

## Architecture

Private extraction code reads the exact PDF and emits private evidence files. Source-safe corpus builders consume those evidence files and generate committed inventories. Vector extraction is separated from classification: PDF drawing paths become private region evidence first, then the source-safe classifier filters page furniture, table rulings, captioned figures, and tiny decorative marks.

Reference resolution uses normalized target indexes with explicit reasons. It must distinguish a known target, a context-relative candidate, an external-standard ambiguity, and a genuinely absent target. External reference matching uses conservative aliases derived from Chapter 35 observations and keeps unmatched citations disputed.

Reviewer tooling produces bounded queues and evidence packets. It never embeds reconstructive source text in public artifacts.

## Data contracts

Vector-region private evidence records contain the PDF page, bounding box, path count, drawing-item count, stroke/fill counts, and stable geometry fingerprint. They do not contain page images or extracted source text.

Diagram inventory records add `evidence_kind`, `geometry`, `classification_reason`, `candidate_source`, and a review state. Automatically accepted vector candidates remain `provisional` unless a checked fixture establishes the classification.

Internal cross-reference records add a machine-readable `resolution_reason` and preserve the raw citation, normalized target, source section, and review state. No unresolved record is silently rewritten as resolved.

Review queue records add priority, evidence category, and recommended action so that human work can be processed by risk rather than file order.

## Error handling

Every private-evidence input is bound to the exact source SHA-256, byte size, and 761-page count. Missing pages, malformed geometry, source mismatch, duplicate stable IDs, or corpus-count drift fail closed. Publication is not considered complete until the exact pushed commit passes the repository verification lanes on Python 3.12.

## Testing

New behavior follows test-first development. Synthetic drawing-region fixtures test vector clustering and exclusion. Corpus tests verify source-safe serialization, deterministic IDs, review-state constraints, and reference resolution reasons. The complete suite, corpus validator, JSON Schema validation, compileall, package build, and LORE checks run before publication.

## Non-goals

This closeout does not perform exhaustive legal interpretation, certify code compliance, publish copyrighted page content, replace ICC source materials, or claim human verification that did not occur.
