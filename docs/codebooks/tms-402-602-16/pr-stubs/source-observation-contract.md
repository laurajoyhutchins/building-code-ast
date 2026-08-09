# TMS 402-16 source observation contract

Status: draft PR scaffold; implementation not started.

## Purpose

Define the exact-source observation/OCR boundary required to ingest the image-based retained TMS 402 artifact without pretending OCR text is embedded PDF text.

## Scope

- exact artifact SHA and canonical TMS 402 PDF region provenance
- explicit OCR text origin and producer identity
- PDF page, printed page, bounding-box, and observation coordinates
- duplicate-prefix handling that preserves evidence without emitting duplicate logical nodes
- deterministic observation identity and diagnostics
- private exact-source replay plus synthetic public fixtures

## Boundaries

Do not broaden hierarchy parsing, infer normative meaning, add TMS 602 parsing, or commit protected OCR/source corpora.

## Completion gate

Coordinate-bearing observations from the exact retained artifact retain OCR provenance, canonical-region identity, and duplicate-prefix diagnostics deterministically. Remove this scaffold file when implementation replaces it.
