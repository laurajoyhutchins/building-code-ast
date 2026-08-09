# NDS 2018 layout evidence

Predecessor: `feature/document-ast-equation-figure-appendix`.

Owns:
- deterministic positioned PDF evidence for the exact retained NDS artifact;
- page roles, printed/PDF-page mapping, block/glyph coordinates, and region-aware reading order;
- exclusion of recurring artifact-local watermark and page furniture without deleting source evidence silently;
- explicit handling of two-column, full-width, opener, equation, figure, and dense-table regions;
- diagnostics for damaged-xref/opening behavior and extraction anomalies.

Does not own:
- publication hierarchy inference;
- equation, table, or figure semantics;
- OCR unless exact-source evidence demonstrates a region-specific need;
- semantic provision parsing.

Completion:
- representative and pathological pages round-trip to exact source coordinates;
- repeated extraction is deterministic;
- watermark/furniture exclusions are provenance-marked and cannot become publication nodes;
- mixed reading-order layouts have source-safe synthetic tests plus private exact-source replay;
- no whole-document structural completeness claim is made yet.

Successor: `feature/nds-2018-hierarchy`.