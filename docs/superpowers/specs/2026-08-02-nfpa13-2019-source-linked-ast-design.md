# NFPA 13 (2019) Source-Linked AST Design

## Objective

Convert the owner-supplied NFPA 13 (2019) PDF into a deterministic, source-linked local representation without publishing licensed source text or claiming compliance interpretation.

## Authority boundaries

- `extract_nfpa13_2019_hierarchy.py` owns chapter, annex, and numbered-clause identity.
- `extract_nfpa13_2019_ast.py` is the low-level PDF and layout engine.
- the existing Document AST `0.1.0` model, strict reader, validator, and JSON Schema remain authoritative for the nested `document_ast` value.
- `nfpa13_bundle.py` owns the NFPA-specific local envelope and graph projections.
- `build_nfpa13_2019_bundle.py` is the canonical CLI.

The PDF, source stream, table contents, figures, overlays, and generated full-document bundle remain local.

## Pipeline

1. **Source stream:** normalize page and two-column reading order while retaining exact canonical offsets and physical provenance.
2. **Document AST:** compute structural ranges from the validated hierarchy and assign every retained non-whitespace character to one source-owning leaf.
3. **Syntax:** preserve paragraphs, lists, definitions, notes, exceptions, conservative table geometry, figures, and unsupported objects.
4. **Reference graph:** emit exact-evidence relationships with an explicit target domain.
5. **Lexical annotations:** emit bounded syntax-derived classifications with parser revision and review status.
6. **Contract finalization:** validate the Document AST through the existing strict reader, attach producer provenance, enforce the NFPA bundle schema, and serialize deterministically.

## Relationship semantics

### Annex A

Only explicit Annex A clauses emit `explains` relationships. An implicit node exists solely to preserve hierarchy when the publication omits an intermediate numbered heading. It does not claim explanatory content and therefore cannot emit `explains`.

The validator requires a one-to-one relationship between explicit Annex A correspondence nodes and `explains` edges.

### Target domains

Every relationship carries:

- `target_locator`
- `target_artifact_id`, nullable
- `target_domain`: `internal`, `external_standard`, or `unspecified_document`
- `resolved`
- exact source evidence when text-backed

An unresolved `Section`, `Table`, or `Figure` citation does not establish which publication owns the target. Such a relation remains unresolved with `target_domain=unspecified_document` and no guessed artifact ID.

Recognized publication families include NFPA, ASTM, ASME, AWWA, ANSI, ANSI/UL, IEEE, ISO, and UL. Their identifiers are stable external targets even though the referenced publication contents are not loaded.

## Semantic annotation boundary

Annotations are projections over source-owning leaf text. They contain:

- lexical type
- source locator
- exact evidence span
- `method=lexical-deterministic`
- parser content hash as `parser_revision`
- `review_status=unreviewed|reviewed|rejected`

The contract deliberately omits a generic confidence field. Repeatability is provenance, not evidence that a semantic classification is correct.

## Producer provenance

Each bundle records:

- repository and exact 40-character commit SHA
- low-level engine path and SHA-256
- canonical wrapper path and SHA-256
- Python and PyMuPDF versions
- normalized command options
- source PDF SHA-256

No timestamps enter the generated bundle, preserving deterministic output for the same source, code, environment metadata, and options.

## Strict contract

The canonical envelope is `nfpa13-ast-bundle/0.2.0`. It is governed by:

- `schemas/nfpa13-ast-bundle.schema.json`
- `building_code_ast.nfpa13_bundle.read_nfpa13_bundle`
- the existing `document_ast_from_dict` reader for the nested Document AST
- exact-key rejection for relations, semantic annotations, and producer metadata
- derived-statistics checks
- deterministic Annex A correspondence checks

Unknown fields and malformed target-domain claims fail closed.

## Reviewed source cases

The public review registry stores only non-reconstructive expectations. It includes representative normative clauses, deep annex headings, a definition entry, revision-marker filtering, table geometry shape, internal and unresolved references, external-standard families, and the explicit-versus-implicit Annex A distinction.

The local verifier applies those expectations to the complete text-bearing bundle. This produces a small human-reviewed accuracy gate in addition to structural validity. It does not claim statistical accuracy for every table or annotation in the publication.

## Remaining uncertainty

- table geometry is not reviewed semantic column meaning;
- figure and diagram semantics are not interpreted;
- lexical annotations remain unreviewed unless separately promoted;
- unresolved target-domain references remain visible rather than guessed;
- the complete licensed-source run is local and cannot execute in public CI.

These are explicit product boundaries, not silent success states.
