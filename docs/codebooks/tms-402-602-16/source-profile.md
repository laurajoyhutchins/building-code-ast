# TMS 402/602-16 source profile

Status: characterization started; document-AST implementation has not started.

## Verified artifact facts

- retained filename: `tms-402_602-2016.pdf`
- size: 53,081,346 bytes
- media type: `application/pdf`
- the source artifact is retained outside Git

These facts identify the retained file operationally but are not yet a complete `SourceRegisterEntry`.

## Exact-byte characterization still required

Before claiming durable TMS ingestion coverage, verify and record:

- SHA-256, page count, PDF version, and extraction restrictions;
- printed-page-label to PDF-page mapping, bookmarks, and table of contents;
- the exact internal boundary and identity of TMS 402 versus TMS 602 material;
- text-layer coverage and reading order for each component;
- chapter, section, subsection, definition, reference, equation, table, figure, appendix, note, and footnote patterns;
- whether the two component documents require independent structural roots or publication-state identities;
- representative unsupported structures;
- edition/printing state, corrections/addenda, publication date, and rights classification.

## Document-AST gate

A descendant document-AST PR must preserve the TMS 402/TMS 602 distinction rather than flattening the combined PDF into one anonymous hierarchy. Cross-document references should remain explicit and edition-scoped.

No protected source prose, tables, figures, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-tms-402-602-16-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-tms402-602-16-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/tms-402-602-16/source-profile.md`
- requires: `action.establish-tms402-602-16-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.
