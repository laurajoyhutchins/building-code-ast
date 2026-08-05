# IBC 2018 Corpus Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining acceptance gaps in the source-backed 2018 IBC corpus while preserving the exact-source, source-safe, fail-closed evidence model.

**Architecture:** Add a private vector-region evidence extractor and a source-safe classifier, improve reference resolution with explicit reasons, produce prioritized review artifacts, strengthen provenance and verification receipts, then publish the exact tested commit. Generated corpus artifacts remain deterministic projections of private evidence and never contain reconstructive source text.

**Tech Stack:** Python 3.12, standard library, optional PyMuPDF 1.24+, JSON Schema Draft 2020-12, unittest, setuptools, LORE.

## Global Constraints

- The authoritative source is `<private-source-path>/icc-2018.pdf` with SHA-256 `c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d`, size 32,608,171 bytes, and 761 PDF pages.
- The copyrighted PDF, page images, raw page text, and reconstructive extracts remain private and uncommitted.
- Structural detections remain provisional unless deterministic source-backed evidence or explicit human review supports a stronger state.
- Legal meaning and compliance conclusions remain out of scope.
- New production behavior requires a failing test first.
- Each lane ends with independently runnable verification and a focused commit.

---

### Task 1: Pin the closeout contract and clean verification entrypoints

**Files:**
- Create: `docs/superpowers/specs/2026-08-03-ibc-2018-corpus-closeout-design.md`
- Create: `docs/superpowers/plans/2026-08-03-ibc-2018-corpus-closeout.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Test: `tests/test_package_metadata.py`

**Interfaces:**
- Consumes: existing corpus validator and package metadata.
- Produces: one documented Python 3.12 verification command set and optional lint/type-check configuration only when supported by installed tooling.

- [ ] Add a failing metadata test that asserts the IBC PDF extra remains optional and Python support remains `>=3.12,<3.13`.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_package_metadata -v` and confirm the intended assertion fails before configuration changes.
- [ ] Update CI to run the complete source-safe verification lanes under Python 3.12.
- [ ] Run the metadata test and full unit suite.
- [ ] Commit the verified closeout contract and CI entrypoints.

### Task 2: Extract private vector drawing regions

**Files:**
- Create: `tools/extract_ibc_2018_vector_regions.py`
- Create: `src/building_code_ast/ingest/ibc2018/vector_regions.py`
- Modify: `src/building_code_ast/ingest/ibc2018/__init__.py`
- Test: `tests/test_ibc2018_vector_regions.py`

**Interfaces:**
- Consumes: a PyMuPDF page and exact source identity.
- Produces: `extract_vector_regions(document) -> list[dict[str, object]]`, with page coverage, geometry summaries, and stable fingerprints but no source text.

- [ ] Write synthetic tests for clustering nearby drawing paths, excluding page-size borders and tiny marks, deterministic geometry fingerprints, and 761-page coverage validation.
- [ ] Run the vector-region tests and confirm failures because the module does not exist.
- [ ] Implement minimal page drawing extraction and clustering using `Page.get_drawings()`.
- [ ] Run the vector-region tests and full unit suite.
- [ ] Generate private vector evidence from the exact PDF outside the repository.
- [ ] Commit the extractor and tests without private evidence.

### Task 3: Classify source-safe vector technical-graphic candidates

**Files:**
- Modify: `src/building_code_ast/ibc2018_corpus.py`
- Modify: `tools/build_ibc_2018_corpus.py`
- Modify: `schemas/ibc-2018-inventory-record.schema.json`
- Modify: `corpora/ibc-2018/ibc-2018-diagram-inventory.json`
- Modify: `corpora/ibc-2018/ibc-2018-diagram-inventory.csv`
- Test: `tests/test_ibc2018_corpus.py`

**Interfaces:**
- Consumes: existing raster image-region evidence plus private vector-region evidence.
- Produces: `inventory_diagrams(..., vector_regions=...)` records with `candidate_source`, `geometry`, `classification_reason`, stable IDs, and provisional/rejected dispositions.

- [ ] Add failing synthetic tests for accepting a large technical vector cluster and rejecting table-like rulings, captioned-figure overlap, page furniture, and tiny decorative clusters.
- [ ] Run the targeted tests and confirm expected failures.
- [ ] Implement conservative vector candidate classification and source-safe serialization.
- [ ] Rebuild corpus artifacts from private evidence and inspect count changes.
- [ ] Run corpus tests, schema validation, and the deterministic corpus validator.
- [ ] Commit vector candidate support and regenerated source-safe artifacts.

### Task 4: Improve internal-reference resolution reasons

**Files:**
- Modify: `src/building_code_ast/ibc2018_corpus.py`
- Modify: `schemas/ibc-2018-inventory-record.schema.json`
- Modify: `corpora/ibc-2018/ibc-2018-cross-reference-inventory.*`
- Modify: `corpora/ibc-2018/ibc-2018-cross-reference-summary.json`
- Test: `tests/test_ibc2018_corpus.py`

**Interfaces:**
- Consumes: section, table, figure, equation, chapter, appendix, and exception target indexes.
- Produces: deterministic `resolution_reason` values and conservative context-relative candidates.

- [ ] Add failing tests for exact target resolution, external-standard ambiguity, appendix shorthand, parent-relative section candidates, and genuinely nonexistent figure/table targets.
- [ ] Run targeted tests and verify the failures identify missing reasoned resolution.
- [ ] Implement normalized indexes and explicit resolution reasons without converting uncertain candidates to resolved.
- [ ] Rebuild the reference inventory and compare state counts with the prior corpus.
- [ ] Run full verification and commit the resolution improvement.

### Task 5: Reconcile conservative external-reference aliases

**Files:**
- Modify: `src/building_code_ast/ibc2018_corpus.py`
- Modify: `corpora/ibc-2018/ibc-2018-external-reference-inventory.*`
- Modify: `corpora/ibc-2018/ibc-2018-external-citation-inventory.*`
- Modify: `corpora/ibc-2018/ibc-2018-reference-crosschecks.json`
- Test: `tests/test_ibc2018_corpus.py`

**Interfaces:**
- Consumes: Chapter 35 agency, designation, edition, and observed title fields.
- Produces: normalized aliases that preserve observed designations and never infer normative incorporation from a lexical match.

- [ ] Add failing tests for punctuation, hyphen, part-number, and agency-case aliases, plus a negative test preventing a near-match.
- [ ] Run targeted tests and confirm failures.
- [ ] Implement conservative alias keys and match reasons.
- [ ] Rebuild citation artifacts and report matched/unmatched deltas.
- [ ] Run full verification and commit alias reconciliation.

### Task 6: Prioritize review and semantic-pilot evidence packets

**Files:**
- Modify: `tools/build_ibc_2018_corpus.py`
- Create: `tools/build_ibc_2018_review_packets.py`
- Modify: `corpora/ibc-2018/ibc-2018-review-queue.csv`
- Create: `corpora/ibc-2018/ibc-2018-review-summary.json`
- Modify: `corpora/ibc-2018/ibc-2018-semantic-pilot-report.md`
- Test: `tests/test_ibc2018_corpus.py`

**Interfaces:**
- Consumes: all provisional/disputed corpus records.
- Produces: deterministic priority, review category, recommended action, and source-safe evidence pointers. It does not automatically mark human review complete.

- [ ] Add failing tests that disputed records outrank provisional records and high-risk structural records outrank low-risk attachments.
- [ ] Implement deterministic queue priority and evidence packet generation.
- [ ] Generate the review summary and verify no raw source text is emitted.
- [ ] Run schema, safety, and corpus checks.
- [ ] Commit review workflow improvements.

### Task 7: Strengthen provenance and acceptance documentation

**Files:**
- Modify: `corpora/ibc-2018/ibc-2018-source-manifest.json`
- Modify: `corpora/ibc-2018/ibc-2018-source-register.json`
- Modify: `docs/reference/ibc-2018-corpus-contract.md`
- Modify: `docs/how-to/build-ibc-2018-corpus.md`
- Modify: `corpora/ibc-2018/ibc-2018-coverage-report.md`
- Modify: `corpora/ibc-2018/ibc-2018-coverage-report.json`
- Test: `tests/test_ibc2018_corpus.py`

**Interfaces:**
- Consumes: exact file identity and observed source-copy markings.
- Produces: explicit acquisition-status, source-copy provenance, custody expectations, and unresolved official-copy comparison status.

- [ ] Add failing tests for exact-source preservation and explicit unresolved official-copy comparison status.
- [ ] Add provenance fields without claiming an official byte-for-byte match.
- [ ] Update coverage limitations to reflect completed vector scanning and remaining human review.
- [ ] Run source-safety scans and all tests.
- [ ] Commit provenance and acceptance documentation.

### Task 8: Exact Python 3.12 verification and publication

**Files:**
- Create: `corpora/ibc-2018/ibc-2018-closeout-verification.json`
- Modify: `corpora/ibc-2018/ibc-2018-validation-report.json`

**Interfaces:**
- Consumes: the final clean commit.
- Produces: exact command results, artifact hashes, branch/commit identity, and a draft pull request.

- [ ] Run the full suite under Python 3.12: unit tests, compileall, corpus validator, JSON Schema validation, package build, and LORE checks.
- [ ] Record exact command outcomes and generated package hashes in the closeout receipt.
- [ ] Confirm the repository contains no PDF, page image, raw page text, private path, or private Drive identifier.
- [ ] Commit the verification receipt.
- [ ] Push `agent/ibc-2018-closeout` and open a draft pull request against current `main`.
- [ ] Inspect GitHub Actions at the exact pushed head and fix any failures before reporting completion.
