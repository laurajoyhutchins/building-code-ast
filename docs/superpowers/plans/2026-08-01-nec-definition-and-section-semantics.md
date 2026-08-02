# NEC Definition and Section Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build source-safe, provenance-preserving Article 100 definition indexes and conservative Article 90/110 section reviews from private ArticleSeed JSON.

**Architecture:** Add an independent `building_code_ast.nec` package whose versioned models consume ArticleSeed mappings without changing the generic Provision AST. A private CLI produces text-bearing semantic files locally; public Git contains only code, schemas, docs, and synthetic tests.

**Tech Stack:** Python 3.12 standard library, dataclasses, enums, regular expressions, unittest, JSON, existing Document AST and SourceSpan types.

## Global Constraints

- Do not commit NEC source text, page images, or text-bearing generated output.
- Preserve exact source text and round-trippable spans.
- Do not emit compliance conclusions or perform table lookups.
- Keep the base runtime dependency-free.
- Keep the generic Provision AST unchanged.
- Fail closed on malformed ArticleSeed input or missing requested sections.

---

### Task 1: Versioned NEC semantic models and validation

**Files:**
- Create: `src/building_code_ast/nec/model.py`
- Create: `src/building_code_ast/nec/validation.py`
- Create: `src/building_code_ast/nec/__init__.py`
- Test: `tests/test_nec_semantic_models.py`

**Interfaces:**
- Produces `DefinitionIndex`, `DefinitionEntry`, `DefinitionFragment`, `DefinitionQualifier`, `CodeReference`, `SectionReview`, `ReviewedClause`, `ReviewedException`, `ReviewedNote`, `SourceNodeProjection`, `NecLanguageProfile`, deterministic identity helpers, and validation functions.

- [ ] Write failing tests for deterministic IDs, serialization, span round-tripping, ordered non-overlapping entries, and local section spans.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_nec_semantic_models -v` and confirm import failures.
- [ ] Implement immutable models and deterministic SHA-256 identities.
- [ ] Implement recursive validation for definition indexes and section reviews.
- [ ] Re-run the focused test and confirm it passes.
- [ ] Commit with `feat: add NEC semantic review contracts`.

### Task 2: Article 100 definition extraction

**Files:**
- Create: `src/building_code_ast/nec/definitions.py`
- Test: `tests/test_nec_definitions.py`

**Interfaces:**
- Consumes ArticleSeed-compatible mappings.
- Produces `build_definition_index(article_seed) -> DefinitionIndex`.

- [ ] Write synthetic tests for alternate terms, `as applied to` qualifiers, numeric scope qualifiers, continuation fragments, attached notes, panel markers, references, and malformed ArticleSeed input.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_nec_definitions -v` and confirm failures because the extractor is absent.
- [ ] Implement strict ArticleSeed shape checks and Article 100 enforcement.
- [ ] Group each definition entry with following non-heading nodes until the next definition or heading.
- [ ] Parse headings conservatively and preserve uncertain parentheticals as qualifiers.
- [ ] Extract body fragments, notes, panel markers, and references with exact spans.
- [ ] Validate the result before returning it.
- [ ] Re-run focused and model tests.
- [ ] Commit with `feat: structure NEC Article 100 definitions`.

### Task 3: Section selection and conservative clause review

**Files:**
- Create: `src/building_code_ast/nec/sections.py`
- Test: `tests/test_nec_sections.py`

**Interfaces:**
- Consumes ArticleSeed mappings and optional `DefinitionIndex`.
- Produces `build_section_review(...) -> SectionReview` and `derive_language_profile(...) -> NecLanguageProfile`.

- [ ] Write synthetic tests for section boundaries, modality precedence, leading conditions, exception separation, note separation, semantic tags, code references, and definition links.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_nec_sections -v` and confirm failures.
- [ ] Implement exact section-range selection through the next section or structural heading.
- [ ] Project source nodes into section-local spans.
- [ ] Split sentences conservatively while retaining ambiguous fragments with diagnostics.
- [ ] Parse modal phrases in fixed precedence and derive subject, predicate, and leading-condition spans.
- [ ] Extract exceptions, notes, references, semantic tags, and exact definition links.
- [ ] Derive and validate the Section 90.5 language profile.
- [ ] Re-run focused tests and all NEC semantic tests.
- [ ] Commit with `feat: review selected NEC section semantics`.

### Task 4: Private semantic-bundle CLI

**Files:**
- Create: `scripts/build_nec_2017_semantics.py`
- Test: `tests/test_nec_semantic_cli.py`

**Interfaces:**
- Reads `article-90.json`, `article-100.json`, and `article-110.json`.
- Writes `manifest.json`, `definitions-article-100.json`, `language-policy-90.5.json`, and one JSON file for each selected Article 110 section.

- [ ] Write tests for deterministic filenames, no absolute path disclosure, required source-identity agreement, and safe `--force` behavior.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_nec_semantic_cli -v` and confirm failures.
- [ ] Implement argument parsing, input loading, source-identity checks, validated generation, deterministic JSON, and safe output replacement.
- [ ] Re-run CLI and full semantic tests.
- [ ] Commit with `feat: add private NEC semantic seed generator`.

### Task 5: Schemas and documentation

**Files:**
- Create: `schemas/nec-definition-index.schema.json`
- Create: `schemas/nec-section-review.schema.json`
- Create: `docs/reference/nec-definition-index.md`
- Create: `docs/reference/nec-section-review.md`
- Create: `docs/how-to/build-nec-semantic-seed.md`
- Modify: `docs/README.md`
- Modify: `README.md`
- Test: `tests/test_nec_semantic_contracts.py`

**Interfaces:**
- Documents both public contracts and private operating procedure.

- [ ] Write tests that parse both schemas and assert version alignment with runtime constants.
- [ ] Run the focused test and confirm missing-schema failures.
- [ ] Add strict schemas with `additionalProperties: false`.
- [ ] Document contract fields, provenance, uncertainty, and the private-source boundary.
- [ ] Add concise repository and documentation-map links.
- [ ] Re-run contract and full tests.
- [ ] Commit with `docs: document NEC semantic seed contracts`.

### Task 6: Private production seed and publication

**Files:**
- Private output only: generated semantic JSON and ZIP outside the repository.

**Interfaces:**
- Uses the supplied ArticleSeed archive.
- Produces a private semantic bundle uploaded beside the source materials in Google Drive.

- [ ] Run the full local unit suite and compilation checks.
- [ ] Run the semantic generator against the private ArticleSeed files.
- [ ] Validate every generated definition and section review.
- [ ] Confirm every `definition_entry` source block is represented as a definition start or preserved continuation, and record the production count.
- [ ] Inspect selected section counts and diagnostics without publishing NEC text.
- [ ] Scan the Git diff for source leakage.
- [ ] Publish a stacked draft PR based on `agent/nec-2017-local-ingestion`.
- [ ] Verify GitHub Actions at the exact head.
- [ ] Upload the private semantic ZIP to Google Drive and verify metadata.
