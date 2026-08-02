# NFPA 13 (2019) Source-Linked AST Implementation Plan

**Goal:** Build and verify a deterministic local-only NFPA 13 (2019) compiler that emits a source-linked Document AST, target-domain-aware relationship graph, bounded lexical annotations, diagnostics, overlays, and a strict versioned bundle without publishing licensed source text.

**Architecture:** Keep the hierarchy extractor and PDF-layout engine as bounded low-level stages. Finalize their output through the repository’s existing Document AST contract and the NFPA-specific `nfpa13-ast-bundle/0.2.0` reader, schema, and producer manifest.

**Tech stack:** Python 3.12, standard library, optional PyMuPDF for local source processing, dependency-free `unittest` tests.

## Global constraints

- Preserve exact local source text and character spans.
- Do not commit the source PDF, clause bodies, table contents, figures, overlays, or generated bulk AST.
- Keep publication structure separate from lexical and later reviewed semantic projections.
- Fail closed on source identity, provenance, deterministic identity, contract, or target-domain inconsistencies.
- Represent unsupported and unresolved cases explicitly rather than guessing.

## Completed extraction foundation

- [x] Extract page-, column-, font-, and bounding-box-aware source lines.
- [x] Build and validate the numbered NFPA 13 hierarchy.
- [x] Compute ancestry-aware structural ranges, including sparse Annex A material.
- [x] Parse paragraphs, nested lists, definitions, notes, exceptions, tables, figures, and unsupported objects.
- [x] Preserve exact evidence spans and source ownership.
- [x] Emit deterministic serialization, diagnostics, overlays, and low-level validation.
- [x] Run the original full-source extraction twice with byte-identical raw output.

## Review remediation

### 1. Annex A relationship semantics

- [x] Emit `explains` only for explicit Annex A clauses.
- [x] Keep synthesized Annex A ancestors structural only.
- [x] Enforce one unique `explains` edge per explicit correspondence node.
- [x] Add reviewed cases for an implicit ancestor and an explicit explanatory clause.

### 2. Strict bundle contract

- [x] Add `nfpa13-ast-bundle/0.2.0` JSON Schema.
- [x] Add a strict reader with exact-key rejection.
- [x] Round-trip the nested `document_ast` through the existing `document_ast_from_dict` reader.
- [x] Add derived-statistics and source-evidence validation.
- [x] Export the bundle API from `building_code_ast`.

### 3. Reference target domains

- [x] Add `target_artifact_id` and `target_domain` to every relationship.
- [x] Preserve unresolved citations as `unspecified_document` without guessing NFPA 13 ownership.
- [x] Recognize NFPA, ASTM, ASME, AWWA, ANSI, ANSI/UL, IEEE, ISO, and UL publication families.
- [x] Add synthetic and full-source reviewed expectations for external publication families.

### 4. Reviewed accuracy gate

- [x] Add a non-reconstructive reviewed-case registry and schema.
- [x] Cover normative structure, annex structure, definitions, artifact filtering, table geometry, references, and external standards.
- [x] Add a local verifier that applies the reviewed expectations to the text-bearing bundle.
- [x] Keep lexical annotations explicitly `unreviewed` unless separately promoted.

### 5. Producer provenance

- [x] Add exact repository commit, engine and wrapper SHA-256, Python version, PyMuPDF version, source hash, and normalized options.
- [x] Require a full 40-character producer commit.
- [x] Remove generic semantic `confidence`; record method, parser revision, and review status instead.
- [x] Keep timestamps out of generated bundles so identical inputs and producer metadata serialize identically.

## Verification gates

- [x] Repository tests pass at the final exact head.
- [x] The complete owner-supplied PDF produces a strict `0.2.0` bundle.
- [x] Two strict complete-source runs are byte-identical.
- [x] All 16 reviewed golden cases pass against the strict complete-source bundle.
- [x] The corrected bundle contains 689 explicit Annex A `explains` edges, 755 identified external-standard relations, and 84 unresolved citations with no guessed target artifact.
- [x] The pull-request description records corrected aggregate counts, final output hash, exact head, and remaining interpretation boundaries.
- [ ] GitHub CI and LORE pass at the final exact head.

The hosted checks remain the final external gate because the licensed-source run is local-only.

## Publication boundary

Only project-authored code, tests, schemas, non-reconstructive reviewed expectations, documentation, and aggregate validation statistics belong in the public repository. The PDF, canonical source stream, full generated bundle, table contents, figure contents, and overlays remain local artifacts.
