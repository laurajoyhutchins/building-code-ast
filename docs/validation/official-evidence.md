# Official Evidence Validation

## Purpose

The supplementary evidence adapters are validated against exact registered official artifacts without committing source publications, page images, or extracted protected expression to public Git.

The durable source-free receipt is [`official-evidence-2026-08-02.json`](official-evidence-2026-08-02.json). It records source URLs, media types, exact byte counts and SHA-256 digests, adapter versions, record and diagnostic counts, projection digests, and repeat-run results.

## Validated sources

The August 2, 2026 validation used:

- the official ICC 2024 Group A IBC General proposed-change monograph;
- the official ICC 2024 Group A CAH1 committee-action report;
- the official ICC 500-2020 errata PDF posted October 2023;
- the official Washington WAC 51-50-0403 HTML page.

Each downloaded artifact was registered as an exact source before adapter execution. `run_evidence_adapter` enforced source role, media type, and SHA-256 identity.

## Results

The validation produced:

- 24 single-part ICC proposal roots;
- 24 linked CAH1 committee actions for those proposal roots;
- four ICC erratum records;
- two direct Washington amendment records;
- two project-normalized Washington derivative records.

Every projection digest matched on a second extraction from the same registered bytes.

The Washington validation preserved different effective dates within one WAC citation:

- `403.4.8.3`: March 16, 2024;
- `403.5.4`: March 15, 2024.

## Fail-closed findings

The official corpus confirmed that ICC proposal monographs and action reports are separate artifacts. Official extraction therefore uses `IccProposalMonographPdfAdapter` and `IccCommitteeActionReportPdfAdapter`, joined by explicit proposal identifiers and a locator mapping derived from the registered proposal source.

Multipart proposals such as `Part I` and `Part II` remain unsupported. They are retained as diagnostics rather than collapsed into a false single proposal lineage.

Committee-action entries outside the selected proposal monograph remain explicit unresolved-locator diagnostics. The action adapter does not invent affected provisions.

The Washington state site stores operative section text in leaf `span` elements inside `div.section-page`. `WashingtonWacHtmlAdapter` version `0.4.0` captures only those scoped blocks plus citation headings. Locator-like navigation text outside the section body is ignored.

## Errata boundary

ICC Digital Codes rejected automated retrieval of the 2021 IBC editorial-changes page during validation. The errata contract was therefore replayed against an exact official ICC 500 errata PDF using a source-specific page normalizer injected into `IccErrataPdfAdapter`.

This validates the guarded errata record pipeline and deterministic adapter behavior. It does not claim exact-byte replay of the blocked Digital Codes page.

## Reproduction

Run the manual validation with network access and the optional PDF dependency:

```bash
python -m pip install -e '.[evidence-pdf]'
python tools/validate_official_evidence.py
```

The command emits `official-evidence-validation.json`. Network retrieval is deliberately not part of routine CI because upstream pages can change independently of this repository. A new receipt should be reviewed and committed when official-source validation is intentionally repeated.
