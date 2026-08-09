# NDS 2018 layout evidence

Predecessor: merged PR #104 `feature/document-ast-equation-figure-appendix`.

Owns:
- deterministic positioned PDF evidence for the exact retained NDS artifact;
- page roles, printed/PDF-page mapping, block coordinates, and region-aware reading order;
- exclusion of recurring artifact-local watermark and page furniture without deleting source evidence silently;
- explicit handling of two-column, full-width, opener, equation, figure, and dense-table page geometry without promoting any of those regions to publication structure;
- diagnostics for malformed navigation targets and extraction anomalies that are visible at this stage.

Does not own:
- chapter, section, appendix, equation, table, or figure recognition;
- semantic interpretation;
- OCR unless exact-source evidence demonstrates a region-specific need;
- whole-document structural completeness claims.

Completion:
- the exact 206-page artifact is identity-gated before whole-document layout evidence is accepted;
- retained and removed regions preserve exact PDF page/bounding-box provenance;
- repeated analysis is deterministic and independent of caller block order;
- recurring artifact/page furniture is removed only through evidence-backed layout classification and remains inspectable with a reason;
- mixed full-width/two-column ordering has source-safe synthetic tests plus private exact-source replay.

Successor: `feature/nds-2018-hierarchy`.
