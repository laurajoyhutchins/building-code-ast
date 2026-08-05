# NEC 2020 Expected Changelog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-safe, deterministic dataset pipeline that converts NFPA development records into expected 2017-to-2020 NEC changes and reconciles them with an independent observed AST diff.

**Architecture:** Introduce one focused NEC change-history module containing immutable contracts, reference resolution, procedural projection, and reconciliation. Add a local JSON CLI, JSON Schema, synthetic fixtures, and source-boundary documentation. The public repository stores only project-authored summaries and source locators; text-bearing NFPA and NEC artifacts remain private.

**Tech Stack:** Python 3.12 standard library, immutable dataclasses, `unittest`, JSON and JSON Schema documents, existing NEC hierarchy locator helpers, GitHub Actions.

## Global Constraints

- The issued 2020 NEC is the controlling text; development records create expectations only.
- The 2020 parser must remain independent from the expected-change dataset.
- Public Git must not contain NEC prose, development-record quotations, PDFs, page images, authenticated exports, or private source hashes.
- Runtime dependencies remain empty.
- Unresolved references and same-stage procedural conflicts fail closed.
- Output ordering must be deterministic.

---

### Task 1: Pin contracts with failing model tests

**Files:**
- Create: `tests/test_nec_change_history.py`
- Create: `src/building_code_ast/nec/change_history.py`

**Interfaces:**
- Produces: `SourceManifestEntry`, `SourceLocator`, `DevelopmentRecord`, `ExpectedChange`, `ObservedChange`, `Reconciliation` and their enums.

- [ ] Write tests that require valid 64-character lowercase SHA-256 digests, bounded confidence values, stable `to_dict()` projections, and immutable tuples.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_nec_change_history -v` and confirm the module import fails.
- [ ] Implement the minimal enums and dataclasses with validation.
- [ ] Rerun the focused test and confirm it passes.
- [ ] Commit the red/green cycle.

### Task 2: Resolve exact and ranged NEC references

**Files:**
- Modify: `tests/test_nec_change_history.py`
- Modify: `src/building_code_ast/nec/change_history.py`

**Interfaces:**
- Consumes: `canonical_nec_locator()` from `building_code_ast.ingest.nec_hierarchy`.
- Produces: `resolve_nec_reference(raw_reference, known_locators) -> ResolvedReference`.

- [ ] Add failing tests for exact locators, `Section` prefixes, numeric ranges, alphabetic ranges, missing range members, and unsupported prose-relative references.
- [ ] Verify the new tests fail because the resolver is absent.
- [ ] Implement exact and sibling-range resolution without nearest-neighbor fallback.
- [ ] Verify focused and repository-wide tests pass.
- [ ] Commit the resolver.

### Task 3: Project expected changes using procedural precedence

**Files:**
- Modify: `tests/test_nec_change_history.py`
- Modify: `src/building_code_ast/nec/change_history.py`

**Interfaces:**
- Produces: `project_expected_changes(records, known_locators) -> tuple[ExpectedChange, ...]`.

- [ ] Add failing tests showing a Second Revision overrides a First Revision, a Council action overrides a Second Revision, a return-to-prior-edition action creates a negative expectation, unresolved references lower confidence, and conflicting records at the controlling stage raise `ValueError`.
- [ ] Verify failures are caused by missing projection behavior.
- [ ] Implement stage ranking, disposition classification, deterministic grouping, support-record ordering, reference resolution, and derived confidence.
- [ ] Verify focused and full tests pass.
- [ ] Commit the projector.

### Task 4: Reconcile expected and observed changes

**Files:**
- Modify: `tests/test_nec_change_history.py`
- Modify: `src/building_code_ast/nec/change_history.py`

**Interfaces:**
- Produces: `reconcile_changes(expectations, observed_changes) -> tuple[Reconciliation, ...]`.

- [ ] Add failing tests for confirmed positive expectations, confirmed negative expectations, expected-but-not-observed changes, contradictions, classification mismatches, and unmatched observed changes.
- [ ] Verify the failures.
- [ ] Implement overlap matching by source and target locators while preserving ambiguous classifications.
- [ ] Verify all tests pass.
- [ ] Commit reconciliation.

### Task 5: Add source-safe JSON bundle and CLI

**Files:**
- Create: `scripts/build_nec_2020_expected_changelog.py`
- Create: `tests/test_nec_change_history_cli.py`
- Create: `schemas/nec-change-history.schema.json`

**Interfaces:**
- Consumes: one private JSON bundle containing known 2017 locators, source manifests, development records, and optional observed changes.
- Produces: deterministic expected changes, optional reconciliation records, diagnostics, and strict exit status.

- [ ] Add failing CLI tests for valid output, unresolved-reference strict failure, conflict rejection, and absence of source prose or absolute paths.
- [ ] Implement strict bundle parsing and output writing with a trailing newline.
- [ ] Add a source-free schema covering the public output contract.
- [ ] Verify schema JSON parses, focused tests pass, and the full suite remains green.
- [ ] Commit the CLI and schema.

### Task 6: Document the private acquisition workflow

**Files:**
- Create: `docs/how-to/build-nec-2020-expected-changelog.md`
- Create: `docs/reference/nec-change-history.md`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `src/building_code_ast/nec/__init__.py`

**Interfaces:**
- Documents the private source manifest, development-record normalization, expected projection, and later reconciliation against 2020 ArticleSeeds.

- [ ] Document source authority, acquisition and hashing, supported development stages, reference limitations, CLI usage, strict-mode interpretation, and publication boundaries.
- [ ] Export the public contracts and functions from the NEC package.
- [ ] Scan the diff for copied NEC language, development-record quotations, source hashes, absolute paths, and unsupported finality claims.
- [ ] Run full unit tests, Python compilation, schema parsing, and `git diff --check` through GitHub Actions.
- [ ] Open a stacked draft PR targeting `agent/nec-hierarchy-oracle-parser` and record exact-head verification.