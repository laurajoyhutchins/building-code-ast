# PDF Layout Analysis Design

Date: 2026-08-01
Status: Approved in conversation
Target: draft PR #15, `agent/ibc-2018-local-ingestion`

## Goal

Improve the bounded 2018 IBC ingestion pipeline with a publication-neutral layout-analysis layer that reconstructs page structure from positioned PDF text and drawing geometry before applying IBC-specific classification.

The machinery remains native Python inside Building Code AST, preserves exact source provenance, keeps generated source-bearing output private, and can be reused by other publication adapters without importing IBC-specific rules.

## Existing baseline

Draft PR #15 already provides:

- positioned-glyph reconstruction from PyMuPDF `rawdict` output;
- physical-page and bounding-box source fragments;
- same-baseline fragment merging;
- fixed-margin filtering;
- opening-matter and midpoint-based two-column ordering;
- conservative logical-block coalescing;
- IBC-specific heading, provision, definition, note, list, and table-like classification;
- exact normalized source-map and Document AST span validation;
- explicit unsupported-table diagnostics;
- a bounded production slice for Chapters 1 through 3.

The next layer replaces hard-coded layout assumptions with explicit page analysis, confidence evidence, and coverage validation.

## Architecture

Add three focused generic modules under `src/building_code_ast/ingest/` and keep publication rules in `ibc2018.py`.

### `layout_analysis.py`

Owns publication-neutral page analysis:

- structural keys for recurring page furniture;
- recurring header and footer detection;
- cleaned-page production;
- body-font estimation;
- page-local reading-order profiles;
- adaptive column split inference;
- stable confidence and evidence records.

It consumes positioned visual lines and page dimensions. It returns immutable analysis values and contains no chapter numbers, page ranges, or IBC regular expressions.

### `table_geometry.py`

Owns table-like geometry:

- baseline grouping of positioned fragments;
- word-gap and cell-gap estimation;
- candidate row construction;
- compatible-row grouping;
- ordered cells with fragment provenance;
- deterministic table text projection.

It does not interpret table meaning, units, regulatory thresholds, or applicability.

### `layout_validation.py`

Owns structural and provenance invariants:

- every retained visual line is consumed exactly once;
- removed lines are explicitly classified as recurring furniture or excluded commentary;
- page-order profiles contain only lines from their page;
- table rows contain only their own fragments;
- table cells contain only fragments from their row;
- normalized spans and source fragments round-trip exactly.

It raises `ValueError` on invariant violations and has no optional third-party dependencies.

### `ibc2018.py`

Retains publication-specific behavior:

- bounded chapter metadata and fail-closed page ranges;
- chapter, part, section, provision, definition, note, list, and commentary rules;
- IBC-specific block classification;
- projection into ChapterSeed and Document AST;
- diagnostics for uncertain or unsupported IBC structures.

The adapter consumes generic layout results and maps them into private source-map records and public Document AST nodes.

## Data flow

```text
local PDF
  -> PyMuPDF positioned glyphs, font metadata, and drawing geometry
  -> source fragments
  -> visual-line reconstruction
  -> recurring-margin analysis and cleanup
  -> body-font and page reading-order profiles
  -> ordered visual lines
  -> geometry-backed table candidates
  -> publication-specific logical blocks
  -> normalized text + private source map + analysis evidence
  -> existing Document AST
  -> layout, provenance, and coverage validation
  -> private ChapterSeed JSON
```

## Core records

The generic layer should use immutable records with stable identifiers.

### Positioned fragment

```text
page number
bounding box
raw text
font name
font size
source block number
fragment identity
```

### Visual line

```text
page number
bounding box
normalized text
ordered source fragments
line identity
```

### Page analysis

```text
page number
reading-order mode: top_to_bottom | two_column
inferred split position or null
body font estimate or null
removed margin line identities
confidence
stable evidence identifiers
```

### Table candidate

```text
page number
ordered rows
ordered cells per row
source fragment identities
normalized text projection
confidence
evidence identifiers
```

### Logical block

```text
block identity
kind
normalized text
consumed visual-line identities
source fragments
confidence
evidence identifiers
```

Confidence values are bounded floats from `0.0` to `1.0`. They are review aids, not probabilities or legal-reliability claims.

## Recurring page furniture

Recurring headers and footers should be detected from text structure and position rather than removed solely by fixed y-coordinate cutoffs.

A structural key should:

- case-fold text;
- collapse non-alphanumeric separators;
- replace numeric runs with a placeholder so changing page numbers still match;
- preserve enough lexical shape to avoid deleting unrelated body text.

Candidates come only from configurable top and bottom page bands. A key becomes recurring when it appears on at least two pages and exceeds a minimum fraction of the analyzed page set.

Removal requires both:

1. the line is inside the corresponding margin band; and
2. its structural key is in the recurring set.

Fixed coordinate cutoffs remain as a safety backstop for content outside the publication's ordinary page region. Matching body text outside a margin band must never be removed.

## Body-font and heading evidence

Estimate body font from cleaned visual lines using a text-length-weighted median of positive font-size observations. Short oversized headings must not dominate the estimate.

Derive a conservative heading threshold from the body-font estimate. Font evidence supplements publication patterns rather than replacing them.

A heading classification may cite evidence such as:

- `chapter_anchor`;
- `part_anchor`;
- `section_anchor`;
- `numbered_provision`;
- `font_heading`;
- `all_caps_heading`.

Font-only headings remain bounded by maximum length, punctuation checks, and surrounding layout context.

## Adaptive reading order

Column detection is page-local and evidence-based.

For each page:

1. retain lines with usable geometry;
2. identify likely full-width opening matter;
3. analyze horizontal line starts, fragment gaps, and occupied ranges;
4. propose a split only when both sides have enough lines;
5. require overlapping vertical ranges between the two sides;
6. reject splits whose separation resembles ordinary paragraph indentation or table-cell spacing;
7. otherwise fall back to top-to-bottom order.

A reliable two-column profile reads full-width opening matter first, then the left column, then the right column. Pages without sufficient evidence remain top-to-bottom.

## Geometry-backed tables

Table detection begins at the fragment level rather than from whitespace in reconstructed prose.

A candidate row must:

- group fragments on a shared baseline within a font-scaled tolerance;
- contain at least two nonempty cell groups;
- separate cells using gaps materially larger than ordinary word spacing;
- reject gaps that are more consistent with independent page columns;
- preserve every source fragment used by each cell.

A table requires at least two consecutive compatible rows. Column counts may vary. Missing trailing cells are represented explicitly as empty cells so later values never shift left.

The first implementation reconstructs text cells only. It does not infer merged headers, row spans, column spans, units, threshold semantics, or regulatory meaning.

## Table AST projection

When geometry supports a table confidently, project it into existing table-capable Document AST node types when available:

```text
table
  -> table_row
       -> table_cell
```

Each table, row, and cell must have an exact span in the normalized chapter text. Table text uses a deterministic plain-text representation designed for span addressing, not Markdown rendering.

When the public AST cannot express the structure without a contract change, retain the source as an `unsupported` node and attach private row and cell evidence. Do not widen the public AST contract in this work.

## Private output changes

The public Document AST remains unchanged.

Private ChapterSeed output may add:

- a top-level `layout_analysis` object;
- page reading-order profiles;
- recurring-margin evidence;
- confidence and evidence fields on source-map or logical-block projections;
- table candidates with ordered rows, ordered cells, normalized spans, and source fragments;
- coverage-validation results.

Serialized additions must be deterministic, JSON-compatible, source-safe, and versioned with the private seed shape. Absolute local paths are never serialized.

## Failure behavior

The pipeline fails closed for internally inconsistent geometry or provenance.

Weak evidence does not automatically fail ingestion:

- no recurring pattern means fixed coordinate filtering only;
- no reliable font estimate means pattern-based headings only;
- no reliable column split means top-to-bottom ordering;
- fewer than two compatible table rows means ordinary block processing;
- ambiguous table geometry remains visible with a diagnostic.

Low confidence must never silently discard source text.

## Testing

Public tests use synthetic project-authored text and geometry.

Required test families:

1. recurring headers with changing page numbers are removed only in the top margin;
2. identical text remains when it appears in the body;
3. body-font estimation resists short oversized headings;
4. adaptive columns handle asymmetric widths;
5. false column splits fall back to top-to-bottom order;
6. geometry-backed cells preserve ordinary word spacing;
7. page-column gaps are not mistaken for table cells;
8. two compatible rows form a table candidate and one row does not;
9. confidence and evidence output is deterministic;
10. every retained line is consumed exactly once;
11. duplicate or missing line consumption fails validation;
12. existing glyph reconstruction, commentary trimming, Chapter 2 definition classification, exact source-map round-tripping, unsupported-chapter rejection, and safe overwrite behavior remain green.

A private production comparison against the exact IBC artifact should record without printing source text:

- source-map and fragment counts by chapter;
- recurring furniture removed;
- page reading-order modes;
- table, row, and cell counts;
- unsupported-table diagnostic count;
- Chapter 2 definition count;
- coverage-validation result;
- exact checksum, page count, and AST span validation.

Count changes are acceptable only when explained by improved segmentation rather than unreviewed text loss.

## Acceptance criteria

- Generic layout analysis contains no IBC chapter numbers, page ranges, or publication-specific regular expressions.
- Existing ChapterSeed and Document AST provenance invariants continue to pass.
- Recurring margin removal is position-gated and cannot delete matching body text.
- Adaptive reading order falls back safely when a two-column split is unsupported.
- Geometry-backed table candidates preserve row, cell, and fragment provenance.
- Every retained visual line is consumed exactly once.
- Low-confidence analysis never silently discards text.
- Public tests pass without the private IBC PDF.
- The exact private IBC artifact completes bounded Chapters 1 through 3 validation without source leakage.
