# ACI 318-19 structural measurement

Predecessor: `feature/aci-318-19-complete-document-ast`.

Owns:
- reproducible whole-document denominators for normative and commentary chapters, sections/subsections, equations, tables, figures, definitions, references, notes/footnotes, appendices, unsupported regions, and ambiguities;
- code/commentary correspondence counts without collapsing source roles;
- source-safe aggregate support reporting and deterministic measurement receipts;
- explicit distinction between detected, structurally reconstructed, resolved, and unsupported structures.

Does not own:
- parser repairs performed only to improve percentages;
- semantic correctness claims;
- publication-state reconciliation.

Completion:
- every support claim has a measured denominator and exact-source producer identity;
- repeated measurement runs are deterministic;
- unsupported classes are enumerated rather than hidden;
- public outputs remain non-reconstructive.

Successors: `feature/aci-318-19-reference-graph` plus parallel `feature/aci-318-19-publication-state-reconciliation`.
