# NDS 2018 source profile

Status: characterization started; document-AST implementation has not started.

## Verified artifact facts

- retained filename: `nds-2018.pdf`
- size: 6,791,825 bytes
- media type: `application/pdf`
- the source artifact is retained outside Git

These facts identify the retained file operationally but are not yet a complete `SourceRegisterEntry`.

## Exact-byte characterization still required

Before claiming durable NDS ingestion coverage, verify and record:

- SHA-256 of the exact retained bytes;
- page count and PDF version;
- encryption or extraction restrictions, if any;
- printed-page-label to PDF-page mapping;
- bookmarks and table-of-contents quality;
- text-layer coverage and reading order;
- whether any pages require OCR;
- chapter, section, subsection, equation, table, figure, appendix, and footnote patterns;
- definition and cross-reference conventions;
- representative unsupported structures;
- edition, printing, correction/addenda state, publication date, and rights classification.

## Document-AST gate

A descendant document-AST PR should identify its exact source artifact and coordinate space, show representative structural fixtures, preserve unsupported structures as diagnostics, and avoid source-family completeness claims until the whole-document structure has been measured.

No protected source prose, tables, figures, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-nds-2018-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-nds2018-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/nds-2018/source-profile.md`
- requires: `action.establish-nds2018-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.
