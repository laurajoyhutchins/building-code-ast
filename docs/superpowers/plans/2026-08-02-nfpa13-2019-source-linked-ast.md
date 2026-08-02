# NFPA 13 (2019) Source-Linked AST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build and verify a deterministic local-only NFPA 13 (2019) compiler that emits a source-linked document AST, reference graph, semantic annotations, diagnostics, overlays, and validation report.

**Architecture:** Keep the existing hierarchy extractor as the structural authority. Add one focused AST module for source stream, span construction, block parsing, references, semantics, validation, and serialization, plus a thin CLI. The public repository stores no licensed text or generated full-document output.

**Tech Stack:** Python 3.12, standard library, optional PyMuPDF for local extraction, dependency-free `unittest` synthetic tests.

## Global Constraints

- Preserve exact local source text and character spans; never silently normalize semantic evidence.
- Do not commit the source PDF, clause bodies, table contents, figures, overlays, or generated bulk AST.
- Keep document structure separate from semantic interpretation.
- Use deterministic node identity from artifact ID, edition ID, node type, and locator.
- Fail closed on structural or provenance inconsistencies.
- Emit diagnostics for unsupported or ambiguous language and layout.

---

### Task 1: Source stream and structural ranges

**Files:**
- Create: `tools/extract_nfpa13_2019_ast.py`
- Test: `tests/test_nfpa13_2019_ast.py`

**Interfaces:**
- Consumes: `extract_nfpa13_2019_hierarchy.extract(Path) -> dict[str, Any]`
- Produces: `build_source_stream(doc, first_page, last_page) -> SourceStream`; `compute_structural_ranges(hierarchy, stream) -> dict[str, StructuralRange]`

- [x] Write failing tests for two-column reading order, excluded headers/footers/revision markers, canonical offsets, and hierarchy-subtree structural range termination.
- [x] Run the focused tests and confirm expected failures due to missing interfaces.
- [x] Implement immutable source-line and structural-range dataclasses plus deterministic source-stream construction.
- [x] Run focused and existing hierarchy tests.
- [x] Commit the source-stream slice.

### Task 2: Direct-text ownership and block syntax

**Files:**
- Modify: `tools/extract_nfpa13_2019_ast.py`
- Modify: `tests/test_nfpa13_2019_ast.py`

**Interfaces:**
- Consumes: `SourceStream`, structural ranges
- Produces: `build_document_tree(...) -> dict[str, Any]`; `parse_direct_blocks(...) -> list[dict[str, Any]]`

- [x] Write failing tests for direct interval subtraction, paragraphs, nested numeric/alphabetic/Roman lists, attached list markers, notes, exceptions, definitions, and figure captions.
- [x] Run focused tests and confirm failures identify the missing parser behavior.
- [x] Implement direct-text interval ownership and deterministic block locators.
- [x] Implement block classification and nesting without semantic interpretation.
- [x] Run focused and full synthetic tests.
- [x] Commit the block-AST slice.

### Task 3: Tables, references, and semantic annotations

**Files:**
- Modify: `tools/extract_nfpa13_2019_ast.py`
- Modify: `tests/test_nfpa13_2019_ast.py`

**Interfaces:**
- Produces: `extract_tables(...)`; `extract_relations(...)`; `classify_semantics(...)`

- [x] Write failing tests for accepted captioned tables, rejected geometry-only detections, Annex A relations, internal clause/table/figure references, unresolved references, and all bounded semantic classes.
- [x] Run focused tests and confirm expected failures.
- [x] Implement conservative table extraction and source-backed table nodes.
- [x] Implement exact-evidence reference relations and deterministic Annex A `explains` edges.
- [x] Implement bounded semantic annotations with no compliance inference.
- [x] Run focused and full synthetic tests.
- [x] Commit the graph and semantic slice.

### Task 4: Validation, deterministic serialization, overlays, and CLI

**Files:**
- Modify: `tools/extract_nfpa13_2019_ast.py`
- Modify: `tests/test_nfpa13_2019_ast.py`
- Create: `docs/reference/nfpa13-local-ast-extractor.md`

**Interfaces:**
- Produces: `validate_bundle(bundle) -> dict[str, Any]`; `write_overlay_pages(...)`; command-line entry point

- [x] Write failing tests for invalid span containment, duplicate locators, broken references, leaf coverage gaps/overlap, revision-marker leakage, and deterministic JSON bytes.
- [x] Run focused tests and confirm each invariant can fail independently.
- [x] Implement validation and deterministic serialization.
- [x] Implement optional overlay rendering and Markdown report output.
- [x] Implement CLI arguments for PDF, hierarchy input/output, expected SHA-256, overlays, and report path.
- [x] Document local usage and the publication boundary.
- [x] Run all synthetic tests and compile checks.
- [x] Commit the validation and CLI slice.

### Task 5: Complete-source verification and publication

**Files:**
- Local only: generated AST bundle, report, overlays, deterministic comparison files
- Modify: pull request description

**Interfaces:**
- Consumes: owner-supplied `/mnt/data/nfpa-2019.pdf`
- Produces: local validated bundle and aggregate statistics; updated draft PR

- [x] Run the hierarchy extractor and AST extractor against the complete PDF with the expected source hash.
- [x] Run a second extraction and compare SHA-256 hashes for deterministic equality.
- [x] Inspect representative overlays for Chapters 1, 20, 21, Annex A, Annex C, and Annex F.
- [x] Run the complete unit-test and compile verification lanes fresh.
- [x] Review the diff against the design and corpus boundary.
- [x] Publish commits to `agent/nfpa13-2019-clause-hierarchy` and update draft PR #20 with exact verification evidence.

## Completion evidence

- Complete source range processed: PDF pages 21-513.
- Source SHA-256 matched the expected owner-supplied artifact.
- Full validation passed with no duplicate locators or IDs, invalid spans, missing anchors, unresolved claimed targets, uncovered source characters, multiply owned source characters, or revision-marker leaks.
- Two complete extractions were byte-identical at AST SHA-256 `b7aa0e569b29811e93f9ff0fd06cc86dd9607ba6d69e2f0490f095ac0e1186f1`.
- Representative overlays were inspected for Chapters 1, 20, and 21 and Annexes A, C, and F; source-owned regions exclude running headers and footers.
- The final bundle contains 39,566 document nodes, 223 accepted tables, 3,423 relations, 15,755 semantic annotations, and 569 evidence-linked diagnostics.
- Generated source text, table contents, overlays, and the full AST remain local-only.
