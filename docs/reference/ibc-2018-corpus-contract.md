# 2018 IBC structural corpus contract

## Status and purpose

The 2018 International Building Code corpus is a versioned structural evidence baseline. It supports parser development, correction workflows, edition comparison, navigation, and later reviewed semantic work. It is not an authoritative legal interpretation, a compliance engine, or a substitute for the source publication and professional judgment.

The corpus is bound to one exact source artifact:

- publication: *2018 International Building Code*;
- publisher: International Code Council, Inc.;
- edition: 2018, First Printing, August 2017;
- local filename: `icc-2018.pdf`;
- SHA-256: `c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d`;
- byte count: 32,608,171;
- PDF page count: 761.

The supplied bytes are authoritative for this corpus build. The source manifest records PDF metadata, printed-page mapping, publication boundaries, private acquisition provenance, access restrictions, and a recurring non-ICC source-copy mark observed in the artifact. No substitute edition or copy was used.

## Representation boundary

The implementation preserves five layers.

1. **Source artifact.** Exact identity, publication state, rights state, file properties, page mapping, and parser version.
2. **Raw page evidence.** Private positioned lines, glyph fragments, bounding boxes, reading order, image regions, source maps, and extraction warnings.
3. **Detected structures.** Candidate tables, figures, layouts, equations, diagrams, definitions, exceptions, and references with a disposition independent of normalized records.
4. **Normalized corpus records.** Stable source-anchored records accepted under the current counting policy.
5. **Interpretations and projections.** Semantic classes, applicability, normative status, requirement meaning, and downstream projections, each independently reviewable.

```text
IBC PDF
→ raw page evidence
→ detected regions and references
→ normalized corpus records
→ reviewed semantic records
→ purpose-specific projections
```

A parser detection can be accepted, rejected, merged, split, corrected, superseded, or disputed without changing the source evidence. A normalized record does not become an IBC requirement merely because it serializes successfully.

## Existing architecture reused

The corpus reuses the repository's publication-neutral concepts where the evidence supports them:

- `AstSourceIdentity`, `PublicationIdentity`, `SourceRegisterEntry`, and `SourceRegister`;
- exact-byte SHA-256 guards and publication-state identity;
- document AST source spans and deterministic identities;
- positioned page fragments, reading-order analysis, repeated-furniture exclusion, and table geometry;
- stable JSON serialization, review states, diagnostics, and source anchors.

The source register remains the compact publication-neutral authority record. The richer IBC source manifest adds corpus-specific page mapping, metadata, publication sections, and acquisition observations.

## IBC-specific boundaries

The following remain IBC-specific until another code family supplies evidence for a shared abstraction:

- chapter and appendix page maps;
- IBC caption and continuation grammar;
- Chapter 35 agency, designation, title, and referenced-section rows;
- occupancy, construction type, height and area, fire-resistance, egress, accessibility, structural-load, and special-inspection classifications;
- appendix-prefixed structures and IBC-specific printed identifiers;
- source-derived exclusion of labels embedded inside IBC figures.

The implementation does not import NEC hierarchy rules. Shared layout primitives are reused, while IBC grammar and semantic categories remain isolated.

## Source and page mapping

PDF pages 1 through 3 contain the cover and copyright material. PDF pages 4 through 27 map to printed roman pages iii through xxvi. PDF page 28 maps to printed page 1, and PDF pages 28 through 759 use `printed_page = pdf_page - 27`. PDF pages 760 and 761 are unprinted trailing pages.

Publication boundaries are:

- chapters: PDF pages 28 through 669, printed pages 1 through 642;
- appendices A through N: PDF pages 670 through 713, printed pages 643 through 686;
- subject index: PDF pages 714 through 759, printed pages 687 through 732.

Every accepted record carries a PDF page anchor, printed-page value where applicable, chapter or appendix context, bounding box, evidence-line identity where available, and hash of the observed source text. Raw page text and images remain private.

## Counting policy 0.1.0

### Formally captioned tables

A logical table is counted once per published table identifier. Repeated captions marked as continued, repeated caption occurrences on later pages, and repeated page headers do not create additional logical tables. All caption occurrences remain anchors on the logical record.

Labels that visually say `TABLE` but are embedded inside a formally captioned figure are rejected as independent tables. Four labels for Table 2304.10.1 inside Figure 2308.6.7.2 are preserved as rejected detections.

Landscape-like or rotated content is a content geometry property. The source has no page-level rotations. Nonhorizontal glyph directions within table pages are retained in geometry fixtures rather than forcing the entire page into a rotated-page state.

### Incidental layouts

The broad policy accepts an unlabeled region when at least three nearby rows contain three or more aligned fragments spanning a defensible horizontal range and do not overlap a formal table or figure region.

The strict policy additionally requires at least four rows and at least three recurring x-position columns. Ordinary two-column prose, contents pages, index columns, section-number alignment, running furniture, and enumerated prose are negative fixtures.

### Figures and diagrams

A logical figure is counted once per published figure identifier. Repeated and continued caption occurrences remain attached to one record. Subfigures do not become separate figures unless the publication gives them independent figure identifiers.

Uncaptioned raster technical-graphic candidates are inventoried separately. A private whole-document vector-path scan now supplies 705 source-backed geometry regions across 413 PDF pages. The public inventory stores bounded boxes, path counts, geometry fingerprints, and deterministic dispositions rather than reconstructive path data. It rejects 136 captioned-figure or out-of-scope regions and leaves 569 regions disputed: 247 tabular-or-background candidates and 322 unclassified vector candidates. None is promoted to a technical graphic without visual review.

### Equations and formulas

A displayed equation or formula block is counted once for a primary symbolic expression. Continuation lines, nearby variable definitions, applicability inequalities introduced by `where` or `for`, and normalized mathematical forms remain attachments, not additional equations.

Prose measurements, unit fragments, external-standard designations, table cells, figure labels, and descriptive variable definitions are excluded. The exact observed expression remains separate from `normalized_expression`, which is null until reviewed. Missing operators, superscripts, subscripts, and grouping are never repaired silently.

### Definitions

Chapter 2 definition entries are sourced from the independently validated positioned Chapter 2 seed. Scoped definition candidates outside Chapter 2 are retained separately with chapter or appendix scope. Terms are published with source anchors and hashes rather than full definition text.

### Exceptions

One record is counted per explicit `Exception:` or `Exceptions:` marker block. Numbered children remain nested evidence. Every exception retains a parent provision locator when resolvable. Detached parentage is an item-level discrepancy.

### Chapter 35 and external references

A Chapter 35 row, an individual observed designation with edition, a normalized document family, and a citation occurrence elsewhere in the IBC are different units.

The same family may have several rows, editions, aliases, or citation occurrences. Exact observed designations and editions are preserved. A named external document outside Chapter 35 is not assumed to be incorporated by reference. Citation purpose and normative effect remain unreviewed.

### Internal references

Raw citation strings and resolved targets are separate. Resolution states are `resolved`, `ambiguous`, `unresolved`, and `nonexistent`. A cross-reference is a relationship, not an independent requirement.

### Front matter, appendices, and index

Front matter contributes source identity and page mapping but not code-body structure counts unless a specific inventory says otherwise. Appendices are included with appendix context. Subject-index columns are excluded from code-body tables and incidental layouts.

## Current baseline counts

All counts are provisional corpus assertions under counting policy 0.1.0, not eternal truths.

- 215 logical formally captioned tables from 266 caption occurrences;
- 12 broad incidental layouts, of which 4 satisfy the strict policy;
- 56 logical formally captioned figures from 67 caption occurrences;
- 2 accepted uncaptioned raster technical-graphic candidates;
- 705 source-safe vector-path regions across 413 pages, including 569 disputed review candidates and 136 deterministic rejections;
- 90 displayed equation or formula blocks;
- 678 definitions, including 666 verified Chapter 2 entries and 12 scoped candidates;
- 769 explicit exception marker blocks containing 881 numbered child items;
- 555 Chapter 35 rows;
- 551 distinct observed designations with editions;
- 555 normalized external-document families;
- 1,458 external citation occurrences outside Chapter 35, including 581 newly linked by unique conservative aliases and 53 still unmatched;
- 4,615 internal cross-reference records: 3,844 resolved, 93 ambiguous, 254 unresolved, and 424 targets not present in the current target inventories;
- 27 representative semantic-pilot records, all structurally anchored and semantically unverified;
- 441 detection records, including accepted, merged, provisional, and rejected detections;
- 2,702 explicit attachment relationships for continuations, notes, footnotes, variable definitions, applicability lines, exception children, and parent provisions.

The coverage report contains counts by chapter and appendix.

## Table and figure semantics

Table semantic classifications are review aids. A table may have several candidate classes, an `unknown` class, or a disputed interpretation. Current lexical categories include occupancy classification, allowable height and area, construction type, fire resistance, fire separation distance, egress capacity, occupant load, travel distance, accessibility dimensions, structural load, material property, inspection, testing, and environmental criteria.

Figure categories are based on chapter and constrained caption evidence. They include fire-resistance assembly, means-of-egress configuration, accessibility clearance, structural configuration, administrative map, building geometry, and unknown. No image meaning is asserted beyond the evidence and recorded confidence.

## Semantic pilot

The pilot selects structurally diverse records from Chapters 3, 5, 6, 7, 10, 11, 16, 17, and 35. It prefers one table, one figure, and one equation per chapter when those types exist, then fills the slice with additional records. It also includes one definition-scope and one exception-attachment case.

The pilot proves serialization and relationship boundaries. It does not exhaustively normalize every table or infer compliance rules. `ibc-2018-semantic-review-packet.csv` and `.md` provide a source-safe sign-off packet; review remains human-gated.

## Chapter 35 cross-checks

`ibc-2018-reference-crosschecks.json` reports:

- Chapter 35 families not lexically detected elsewhere;
- citation occurrences without a Chapter 35 family match;
- alias or duplicate family candidates;
- designation or edition mismatch candidates;
- rows with unresolved organization or title evidence.

External reconciliation accepts exact aliases, issuing-organization aliases such as `ASCE` to `ASCE/SEI`, paired inch-pound/metric designations, and cross-agency aliases only when the Chapter 35 designation itself explicitly declares the cited agency. Every accepted alias must map to one family. Fuzzy, title-based, and semantic matching are prohibited. A remaining unmatched occurrence is a review signal, not proof that the standard is absent or unused.

## Validation and correction workflow

The builder produces item-level discrepancies for duplicate identities, source-hash mismatch, page-count mismatch, split continuations, caption detachment, exception detachment, and malformed page ranges. Coverage totals are derived from the item records after validation.

Every expected count and item supports `provisional`, `verified`, `corrected`, `superseded`, `disputed`, or `rejected`. Corrections preserve the prior assertion and reason. They do not rewrite evidence to make a test pass. The review queue is deterministically sorted into P0 through P3 bands and synchronized from the current inventories; priority never changes evidentiary status.

The initial correction history records:

1. 266 table caption occurrences consolidated into 215 logical tables;
2. four embedded `TABLE 2304.10.1` labels rejected as independent tables;
3. an earlier 1,294 exception-line count superseded by 769 explicit marker blocks after numbered children were attached to their parent blocks.

## Geometry fixtures

`fixtures/ibc2018/geometry-fixtures.json` contains non-reconstructive positive, negative, and disputed source-derived fixtures. Positive fixtures cover ruled and borderless tables, continuation tables, merged headers, nonhorizontal table content, appendix tables, Chapter 35 rows, formulas, captioned figures, uncaptioned raster graphics, and nested exceptions. Negative fixtures cover page columns, contents pages, index columns, running furniture, source-copy marks, textual references, enumerated prose, and section-number alignment.

The fixture file contains coordinates, stable record IDs, source hashes, and reviewer rationale. It contains no page image or source passage.

## Copyright and private evidence

The PDF, full page text, page images, glyph dumps, private ChapterSeed files, and reconstructive output remain outside Git. Public corpus files contain project-authored schemas, identifiers, hashes, coordinates, constrained captions, counts, and structural relationships.

The source register uses `private_local` access and `uncertain_restricted` rights. Source access does not grant redistribution rights. Exact bytes, size, page count, and artifact-derived publication identity are verified. Equivalence to an independently obtained official copy remains unverified. Any future comparison copy must receive a separate source-artifact record rather than silently replacing the processed artifact.

## Adding another IBC edition

1. Register the exact artifact and publication state without copying the source into Git.
2. Compute hash, size, metadata, page count, publication boundaries, and printed-page mapping.
3. Run raw positioned extraction into a private evidence directory.
4. Reconcile chapter, appendix, and index boundaries independently for that edition.
5. Run the generic detection stages without reusing 2018 counts as truth.
6. add edition-specific caption, Chapter 35, and hierarchy rules only when source evidence requires them;
7. generate a separate corpus manifest and correction history;
8. compare normalized records by identifier and evidence, not by page offset alone.

## Later edition comparison

Edition comparison should relate independent edition corpora. It must distinguish unchanged identifiers, moved structures, changed captions, split or merged records, changed referenced-standard editions, and extraction differences. A parser mismatch is not automatically a code change, and a development-history expectation is not proof of issued text.
