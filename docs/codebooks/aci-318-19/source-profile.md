# ACI 318-19 source profile

Status: characterization started; document-AST implementation has not started.

## Verified artifact facts

- retained filename: `aci-318-2019.pdf`
- size: 10,010,981 bytes
- media type: `application/pdf`
- the source artifact is retained outside Git

These facts identify the retained file operationally but are not yet a complete `SourceRegisterEntry`.

## Exact-byte characterization still required

Before claiming durable ACI ingestion coverage, verify and record:

- SHA-256, page count, PDF version, and extraction restrictions;
- printed-page-label to PDF-page mapping, bookmarks, and table of contents;
- text-layer coverage and reading order;
- chapter, section, subsection, definition, reference, equation, table, figure, note, and appendix patterns;
- the exact normative-code versus commentary/explanatory boundary present in the retained artifact;
- chapter-level design and construction responsibility structures that should remain publication structure rather than inferred semantics;
- representative unsupported structures;
- edition/printing state, corrections, publication date, and rights classification.

## Document-AST gate

A descendant document-AST PR must preserve any normative/commentary distinction and establish deterministic structural locators and exact source coordinates before provision semantics are attempted.

No protected source prose, tables, figures, or page images belong in public Git.