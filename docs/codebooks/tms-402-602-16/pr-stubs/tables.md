# TMS 402-16 table structures

Status: draft PR scaffold; implementation not started.

## Purpose

Reconstruct TMS 402 tables as provenance-preserving structural objects without conflating cell extraction with semantic lookup behavior.

## Scope

- table identity and publication ownership
- geometry, rows, columns, headers, and cell structure
- multi-page/continued-table membership
- notes, footnotes, units, and header associations
- OCR/source-region provenance
- explicit unsupported/ambiguous table layouts
- measured exact-source coverage against the structural inventory

## Boundaries

Do not infer engineering lookup semantics, interpolate values, normalize dimensions silently, or treat commentary tables as normative lookup data.

## Completion gate

Measured TMS 402 table regions are structurally reconstructed or explicitly unsupported with exact source provenance and continuation/footnote relationships. Remove this scaffold file when implementation replaces it.
