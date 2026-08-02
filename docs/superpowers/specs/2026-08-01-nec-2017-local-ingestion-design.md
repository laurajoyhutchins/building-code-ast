# NEC 2017 Local Ingestion Design

Date: 2026-08-01
Status: Approved in conversation and self-reviewed

## Context

The repository already has a provenance-preserving document AST but no adapter for publisher-formatted PDFs. The supplied 2017 NEC PDF has an embedded text layer, bookmarks, two-column pages, article boundaries that may share a page, definition entries, informational notes, exceptions, lists, and tables. The PDF and NEC-derived text must remain outside public Git.

## Decision

Add a local-only, coordinate-aware ingestion adapter that converts selected NEC articles into ArticleSeed JSON documents. Each seed contains a source manifest, a normalized article text, a block-level PDF source map, and the existing DocumentAst representation. Public Git contains only ingestion code, synthetic fixtures, tests, and operating documentation.

The first production seed covers Articles 90, 100, and 110. The parser is intentionally structural. It does not interpret compliance, resolve references, or normalize requirements into semantic provision ASTs.

## Source identity

The source manifest records:

- title `NFPA 70, National Electrical Code`;
- edition `2017`;
- exact SHA-256 of the local PDF;
- byte length and page count;
- extractor identifier and version;
- selected article number and bookmark title.

The document AST uses:

- `artifact_id`: `nfpa:70`;
- `edition_id`: `2017:pdf:sha256:<digest>`.

The full PDF path is never serialized.

## Components

### PDF layout adapter

`building_code_ast.ingest.pdf_layout` defines source-free layout dataclasses and an optional PyMuPDF adapter. Importing the package does not require PyMuPDF. The adapter fails with a clear installation message when the optional dependency is absent.

It extracts text blocks with page number and bounding box, removes recurring page headers and footers, and orders remaining blocks by page, left column, then right column. It normalizes line wrapping deterministically, including soft line-break hyphen repair, while retaining the original extracted block text in the source map.

### NEC article selector

`building_code_ast.ingest.nec2017` reads numeric article bookmarks, selects the page range from one article bookmark through the next, then trims by visible `ARTICLE <number>` anchors. This handles pages on which one article ends in the left column and the next begins in the right column.

### Structural node builder

Each retained normalized block becomes one document node. Classification is conservative:

- article, chapter, part, and standalone section headings -> `heading` or `section`;
- numbered section blocks -> `section`;
- parenthesized enumerations -> `list_item`;
- `Informational Note` -> `note`;
- `Exception` -> `note` with `kind=exception`;
- Article 100 term-definition blocks -> `definition_entry`;
- table-like or unclassified layout -> `unsupported` or `paragraph` with a diagnostic when structure is uncertain.

The AST does not split clauses inside a block unless an exact normalized subspan is available. Every node span addresses the generated normalized article text exactly.

### Article seed

An ArticleSeed serializes:

- `seed_version`;
- source manifest;
- article metadata;
- `source_map` entries mapping normalized spans to PDF page and bounding box;
- existing DocumentAst JSON;
- ingestion diagnostics and counts.

The source map is separate from the AST so PDF coordinates do not contaminate the public document contract.

### CLI

`scripts/ingest_nec_2017.py` accepts a local PDF, output directory, and comma-separated article numbers. It defaults to Articles 90, 100, and 110. It writes one manifest and one JSON file per article. It refuses to overwrite an existing nonempty output directory unless `--force` is supplied.

## Publication boundary

Generated files belong under `generated-private/` or another user-selected private directory. The CLI prints a warning before writing. No NEC text, page image, or generated seed is committed to the public repository.

## Error handling

The ingestion fails closed when:

- the source cannot be opened;
- no numeric article bookmarks exist;
- a requested article bookmark is missing;
- the visible article anchor cannot be found;
- no retained content remains after trimming;
- a generated AST fails provenance validation;
- the output directory would be overwritten without explicit permission.

Layout anomalies that preserve usable text become diagnostics rather than guessed structure.

## Testing

Synthetic tests cover:

- deterministic two-column reading order;
- line-break hyphen repair;
- same-page article boundary trimming;
- Article 100 definition classification;
- exact source spans and source-map coverage;
- stable artifact and edition identity;
- missing dependency and missing article failures;
- JSON serialization without local paths;
- CLI overwrite protection.

A local integration smoke test runs against the supplied PDF and verifies Articles 90, 100, and 110, but the PDF and generated outputs are not test fixtures or Git artifacts.

## Non-goals

This slice does not:

- redistribute NEC text;
- reconstruct complex tables into rows and cells;
- detect gray change shading or `N` margin markers semantically;
- resolve definitions or cross-references;
- parse the entire edition in CI;
- create compliance conclusions;
- feed arbitrary NEC prose directly into the provision parser.

## Acceptance criteria

- Public tests pass without PyMuPDF installed.
- Installing the optional `nec-pdf` extra enables the CLI.
- The supplied PDF produces validated private ArticleSeed files for 90, 100, and 110.
- Article 100 includes definition-entry nodes.
- Same-page article boundaries do not leak adjacent article text.
- Every AST and source-map normalized span round-trips to the generated source text.
- No source PDF, NEC text fixture, or generated ArticleSeed is added to Git.
