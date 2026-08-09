# ASHRAE 90.1-2016 source profile

Status: characterization started; document-AST implementation has not started.

## Verified artifact facts

- retained filename: `ashrae-90_1-2016.pdf`
- size: 3,475,675 bytes
- media type: `application/pdf`
- the source artifact is retained outside Git

These facts identify the retained file operationally but are not yet a complete `SourceRegisterEntry`.

## Exact-byte characterization still required

Before claiming durable ASHRAE 90.1 ingestion coverage, verify and record:

- SHA-256, page count, PDF version, and extraction restrictions;
- printed-page-label to PDF-page mapping, bookmarks, and table of contents;
- exact edition, printing, digital revision, errata, and included-addenda state;
- text-layer coverage and reading order;
- section, subsection, definition, reference, exception, equation, table, figure, appendix, note, and footnote patterns;
- mandatory versus informative appendix boundaries;
- representative unsupported structures;
- publication date and rights classification.

## Document-AST gate

A descendant document-AST PR should preserve mandatory/informative publication distinctions, establish deterministic locators and exact source coordinates, and keep table/equation structure explicit before provision semantics are attempted.

No protected source prose, tables, figures, or page images belong in public Git.