# IBC 2018 table semantics contract

Predecessor: `feature/ibc-exception-semantics`.

Owns:
- generic semantic table contract needed by IBC;
- hierarchical headers, row/column keys, units, notes/footnotes, continuations, and applicability anchors;
- lookup coordinates and explicit ambiguous header/span relationships;
- synthetic public fixtures before broad IBC interpretation.

Does not own:
- converting all IBC tables;
- equation/calculation execution;
- compliance evaluation or engineering meaning inferred from geometry alone.

Completion:
- issue #3 table-lookup vocabulary is documented and schema-backed;
- synthetic fixtures cover merged headers, units, notes, continuations, and ambiguity;
- representative source-safe IBC cases exercise provenance round-trip;
- ambiguous relationships fail closed.

Successor: `feature/ibc-table-reviewed-slice`.
