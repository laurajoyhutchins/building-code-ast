# Reference-Derived PDF Layout Analysis Design

Date: 2026-08-01
Status: Approved in conversation
Target: draft PR #15, `agent/ibc-2018-local-ingestion`
Reference implementation: `laurajoyhutchins/obsidian-pdf-extractor` draft PR #1

## Goal

Improve the bounded 2018 IBC ingestion pipeline by reimplementing selected layout-analysis ideas from the Obsidian PDF Extractor inside Building Code AST, without creating a package, runtime, source-tree, build, or repository dependency on the Obsidian plugin.

The resulting machinery remains native Python in `building-code-ast`, preserves the existing private-source and exact-provenance boundaries, and is reusable by other publication adapters when their PDF layouts justify it.

## Reference-only boundary

The Obsidian PDF Extractor is a design reference, not a dependency.

Building Code AST must not:

- import TypeScript, compiled JavaScript, packages, artifacts, or generated files from `obsidian-pdf-extractor`;
- add the Obsidian repository as a Git submodule, subtree, package source, vendored directory, or network dependency;
- execute Node, PDF.js, Obsidian APIs, or plugin code as part of ingestion;
- couple public contracts or file formats to Obsidian-specific models;
- require the reference repository to be present for tests, builds, local ingestion, or CI.

The port may reproduce general algorithms and test ideas after translating them into the existing Python models and PyMuPDF coordinate system. Public documentation should identify the reference implementation and the independent reimplementation boundary.

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

The current adapter is intentionally conservative, but several decisions are hard-coded to this PDF: fixed top and bottom cutoffs, a page midpoint for column assignment, capitalization-heavy heading inference, and table preservation without cell reconstruction.

## Selected reference ideas

The following ideas are useful and sufficiently independent of Obsidian to reimplement.

### Repeated-margin detection

Detect recurring header and footer structures across the selected page set rather than relying only on absolute y-coordinate cutoffs.

A normalized structural key should:

- case-fold text;
- collapse non-alphanumeric separators;
- replace numeric runs with a placeholder so page numbers do not prevent recurrence matching;
- preserve enough lexical shape to avoid deleting unrelated body lines.

Candidates are drawn only from configurable top and bottom page bands. A key becomes recurring when it appears on at least two pages and on a minimum fraction of the analyzed page set. Removal requires both positional membership in the appropriate margin band and membership in the corresponding recurring-key set.

Fixed safety cutoffs remain as a backstop for material outside the publication's ordinary content region.

### Body-font and heading evidence

Estimate body font size from cleaned lines using a text-length-weighted median of positive font-size observations. Lines shorter than ordinary prose should not dominate the estimate.

Derive a conservative heading threshold from the body font estimate. Font evidence supplements, but does not replace, IBC-specific heading and section patterns.

A heading classification may cite one or more evidence values:

- `chapter_anchor`;
- `part_anchor`;
- `section_anchor`;
- `numbered_provision`;
- `font_heading`;
- `all_caps_heading`.

Font-only headings must remain bounded by maximum text length and terminal-punctuation checks.

### Adaptive column analysis

Replace the page midpoint as the only column boundary with an evidence-based page profile.

For each page:

1. retain lines with usable geometry;
2. exclude full-width opening matter from the body-column sample;
3. calculate candidate horizontal gaps between source fragments or line starts;
4. accept a two-column split only when both sides contain sufficient lines, their vertical ranges overlap, and the separation is materially larger than normal intra-line or paragraph spacing;
5. otherwise use top-to-bottom order.

The inferred split remains a page-local analysis result. Publication adapters may override it for known exceptional pages, but the generic helper must not contain IBC chapter numbers or page ranges.

### Geometry-backed table rows

Use positioned fragments to identify rows containing multiple cell groups separated by substantial horizontal gaps.

A candidate row must:

- contain at least two nonempty cells;
- group fragments on a shared baseline within a font-scaled tolerance;
- separate cells at gaps materially larger than ordinary word spacing;
- reject rows whose largest gap is more consistent with independent page columns than table cells;
- preserve every source fragment used to construct each cell.

A table requires at least two consecutive compatible candidate rows. Column counts may vary; missing trailing cells are represented explicitly as empty cells rather than shifting later values left.

This first port reconstructs text cells only. It does not infer row spans, column spans, merged headers, semantic units, or regulatory meaning.

### Confidence and evidence

Layout and block classifications should expose confidence and evidence in private ingestion data without changing the public Document AST contract.

Add private analysis records for:

- recurring-margin detection;
- body-font estimate;
- page reading-order mode and inferred split;
- geometry-backed table rows;
- logical-block classification.

Confidence values are bounded floats from `0.0` to `1.0`. They are review aids, not probabilities and not legal reliability claims.

Evidence strings are stable machine-readable identifiers. Human-readable diagnostics remain separate.

### Coverage validation

Every retained visual line must be consumed exactly once by the logical-block projection, except lines explicitly removed as recurring margin furniture or publisher commentary.

Validation must fail closed for:

- a retained line omitted from all blocks;
- a retained line assigned to more than one block;
- a table cell referencing a fragment outside its parent row;
- a source-map entry whose normalized span or fragment provenance does not round-trip;
- a page-order profile that references a line from another page.

## Architecture

Add three focused generic modules under `src/building_code_ast/ingest/`.

### `layout_analysis.py`

Owns publication-neutral layout records and analysis:

- structural margin keys;
- recurring-margin detection;
- cleaned-page production;
- body-font estimation;
- page column-profile inference;
- stable confidence and evidence records.

It consumes positioned lines and returns immutable analysis values. It does not import IBC-specific code.

### `table_geometry.py`

Owns baseline grouping, cell-gap analysis, compatible-row grouping, and table candidate records.

It consumes positioned source fragments and page geometry. It does not classify regulatory meaning or emit Markdown.

### `layout_validation.py`

Owns exact line-consumption and nested-fragment validation for analyzed pages and logical blocks.

It raises `ValueError` on invariant violations and has no optional third-party dependencies.

### `ibc2018.py`

Retains publication-specific behavior:

- bounded chapter metadata and fail-closed page ranges;
- chapter, part, section, provision, definition, note, list, and commentary rules;
- projection into ChapterSeed and Document AST;
- diagnostics for uncertain or unsupported IBC structures.

The adapter calls the generic modules and maps generic evidence into private IBC source-map and diagnostic records.

## Data flow

```text
local IBC PDF
  -> PyMuPDF positioned glyphs and page geometry
  -> reconstructed source fragments and visual lines
  -> recurring-margin analysis and cleanup
  -> body-font and page-column profiles
  -> page reading order
  -> geometry-backed table-row candidates
  -> IBC-specific logical-block classification
  -> normalized text + private source map + analysis evidence
  -> existing Document AST
  -> layout, provenance, and coverage validation
  -> private ChapterSeed JSON
```

## Private data contract changes

The public Document AST remains unchanged.

Private ChapterSeed output may add:

- a top-level `layout_analysis` object containing extractor-wide and page-level evidence;
- `confidence` and `evidence` fields on source-map or logical-block projections;
- table records containing ordered rows, ordered cells, normalized text spans, and source fragments.

All added fields must be deterministic, JSON-serializable, source-safe, and independently versioned through the ChapterSeed version if the serialized shape changes.

No absolute path may be serialized.

## Table AST projection

When geometry supports a table confidently, project it into existing table-capable Document AST node types if those types are already available on the target branch.

The hierarchy is:

```text
table
  -> table_row
       -> table_cell
```

Each table, row, and cell must have an exact span in the normalized chapter text. Normalized table text should use a deterministic plain-text representation designed for exact span addressing, not Markdown rendering.

If the target Document AST cannot represent a required table node without changing its public contract, retain the table as an `unsupported` node with private row and cell evidence. Do not widen the public AST contract inside this port.

## Error handling

The pipeline fails closed when generic analysis produces internally inconsistent geometry or provenance.

Weak evidence does not automatically fail ingestion. Instead:

- no reliable recurring margin pattern means fixed coordinate filtering only;
- no reliable body-font estimate means pattern-based heading classification only;
- no reliable two-column split means top-to-bottom ordering;
- fewer than two compatible table rows means ordinary line/block processing;
- ambiguous table geometry remains preserved with an explicit diagnostic.

The adapter must never silently discard text because confidence is low.

## Testing

Public tests use only synthetic project-authored text and geometry.

Required test families:

1. recurring headers whose page numbers differ are removed only in the top margin;
2. identical body text is retained when it occurs outside the margin band;
3. text-length-weighted body-font estimation resists short oversized headings;
4. adaptive column ordering handles asymmetric column widths and rejects false splits;
5. geometry-backed cells preserve word spacing and do not confuse page-column gaps with table cells;
6. two compatible table rows form a table candidate, while one row does not;
7. confidence and evidence output is deterministic;
8. every retained line is consumed exactly once;
9. duplicate or missing line consumption fails validation;
10. existing IBC glyph reconstruction, commentary trimming, Chapter 2 definition classification, exact source-map round-tripping, unsupported-chapter rejection, and safe overwrite behavior remain green.

A private production comparison against the exact IBC source artifact should record, without printing source text:

- chapter source-map and fragment counts;
- recurring margin keys removed;
- inferred page-order modes;
- geometry-backed table, row, and cell counts;
- unsupported-table diagnostic count;
- Chapter 2 definition count;
- coverage-validation result;
- exact checksum, page count, and AST span validation.

The comparison is diagnostic, not a requirement to preserve the current counts. Count changes must be explained by improved segmentation rather than unreviewed text loss.

## Documentation

Update the IBC ingestion how-to and design notes to state:

- the layout machinery was independently reimplemented with the Obsidian PDF Extractor used only as a reference;
- no Obsidian or Node dependency exists;
- confidence and evidence are review aids;
- table reconstruction remains structural and does not interpret code requirements;
- generated text-bearing output remains private.

## Acceptance criteria

- No runtime, package, source-tree, build, or repository dependency on `obsidian-pdf-extractor` exists.
- Generic layout analysis contains no IBC chapter numbers, page ranges, or publication-specific regular expressions.
- Existing ChapterSeed and Document AST provenance invariants continue to pass.
- Recurring margin removal is position-gated and cannot delete matching body text.
- Adaptive reading order falls back safely when a two-column split is not supported.
- Geometry-backed table candidates preserve row, cell, and fragment provenance.
- Every retained line is consumed exactly once.
- Public tests pass without the private IBC PDF.
- The exact private IBC artifact completes bounded Chapters 1 through 3 validation without source leakage.
