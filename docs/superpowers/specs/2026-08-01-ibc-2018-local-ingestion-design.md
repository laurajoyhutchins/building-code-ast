# IBC 2018 Local Ingestion Design

## Goal

Add a private, provenance-preserving structural ingestion adapter for a user-supplied 2018 International Building Code PDF, following the bounded NEC ingestion pattern without assuming the two PDFs share a text-layer layout.

## Source findings

The verified source is a 761-page PDF with no usable outline. Its text layer exposes positioned glyphs rather than normal words and lines. Ordinary `get_text("blocks")` extraction therefore inserts spaces between letters and cannot be reused unchanged from the NEC adapter.

The initial production slice is intentionally limited to Chapters 1 through 3 at verified physical PDF pages 28–39, 40–71, and 72–81. Unsupported chapter requests fail closed.

## Architecture

The adapter remains separate from the NEC-specific module and reuses the existing public Document AST contract.

- `ibc2018.py` owns glyph reconstruction, visual-line ordering, bounded page ranges, logical block formation, chapter seed construction, and exact provenance validation.
- `ingest_ibc_2018.py` owns local file hashing, output-directory safety, JSON emission, and the private-output warning.
- Generated text-bearing seeds remain outside public Git.
- PyMuPDF remains optional through an `ibc-pdf` extra. The base runtime remains dependency-free.

## Data flow

```text
local PDF
  -> selected physical pages
  -> positioned glyphs
  -> reconstructed visual lines
  -> opening matter and two-column reading order
  -> logical headings/provisions/definitions/notes/lists/tables
  -> normalized chapter text + fragment source map
  -> existing Document AST
  -> exact span and identity validation
  -> private ChapterSeed JSON
```

## Provenance

Each logical block retains one or more fragments containing the physical PDF page, bounding box, PDF block number, and reconstructed visual text. Source-map spans address the exact normalized chapter text. The source manifest binds all output to:

```text
artifact_id: icc:ibc
edition_id: 2018:pdf:sha256:<digest>
```

Absolute local paths are not serialized.

## Classification boundary

The adapter classifies publication structure only:

- chapter and section headings;
- numbered provisions;
- Chapter 2 definition entries;
- exceptions and notes;
- list items;
- ordinary paragraphs;
- unsupported table-like layout.

It does not infer applicability, modality, conditions, compliance, or legal meaning. Complex tables are preserved in reconstructed reading order with a warning instead of guessed cell semantics.

## Commentary boundary

Publisher user-note commentary between the chapter title and the first Part or Section is excluded from the code seed. Chapter titles and code body headings remain. This keeps the seed aligned with the regulatory text slice rather than mixing explanatory material into the same AST.

## Error handling

The adapter fails closed when:

- PyMuPDF is unavailable;
- the source file does not exist or cannot be opened;
- the PDF is too short to match verified page ranges;
- a requested chapter is unsupported or duplicated;
- the visible chapter or section anchors cannot be reconstructed;
- a source digest or size is malformed;
- any source-map or AST span fails exact validation.

`--force` deletes only known files produced by this generator.

## Testing

Synthetic tests cover glyph-to-word reconstruction, same-baseline split-word repair, commentary trimming, line-break hyphenation, definition classification, exact source-map round-tripping, unsupported chapter rejection, and safe overwrite behavior.

A private production smoke test runs Chapters 1–3 against the exact source PDF and validates every generated AST without publishing source text.
