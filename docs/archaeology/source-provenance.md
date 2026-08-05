# Source and provenance model

## Authority ladder

1. **Authoritative publication or law:** the issued model code, standard, erratum, amendment, or other controlling source within its actual jurisdiction and effective period.
2. **Registered evidence artifact:** an exact byte identity with publication state, role, access scope, and rights status.
3. **Extracted source evidence:** page, region, coordinates, original span, printed locator, and parser diagnostics.
4. **Derived AST structure:** deterministic node identities, parent-child edges, table partitions, references, and selected semantic annotations.
5. **Generated projection:** JSON, reports, conformance receipts, and views that can be regenerated from the canonical graph or source-bound parser pipeline.
6. **Downstream interpretation:** jurisdiction, applicability, equipment lineage, comparison, or compliance reasoning owned outside the canonical source tree.

A lower layer cannot silently acquire the authority of a higher layer.

## Required provenance dimensions

- source family, title, edition, printing/correction state, and artifact identity;
- page or source region and exact extraction span;
- printed identifier and preserved source order;
- parser or adapter identifier and version;
- transformation or producer revision where available;
- diagnostics, confidence or review status, and unresolved ambiguity;
- evidence role: normative text, official correction, development history, jurisdictional law, guidance, interpretation, commentary, or secondary analysis;
- access and rights status independent of technical availability.

## Private-source boundary

The repository may describe that an exact private source was exercised and retain aggregate or non-reconstructive validation evidence. It must not commit source PDFs, private links, credentials, page images, source hashes that were intentionally withheld, or large verbatim excerpts. Text-bearing generated ASTs remain local unless publication rights are independently established.

## Derived versus authoritative

A deterministic AST can be reproducible and still be wrong. Expected changelogs can predict where text should differ and still not be issued text. A parser can locate a figure reference without understanding the figure. Provenance preserves these distinctions instead of polishing them into false certainty.
