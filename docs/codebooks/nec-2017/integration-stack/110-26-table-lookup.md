# NEC 110.26 table lookup

Predecessor: `feature/table-lookup-semantic-contract`.

Owns:
- projecting the reviewed 110.26(A)(1) condition-to-table-selection path into the generic lookup contract;
- preserving condition classification inputs, selected table branch/cell, dimensional units, and exact derivation provenance;
- fail-closed behavior for unsupported or ambiguous condition classification;
- tests proving that table-derived values cannot appear without the evidence chain that produced them.

Does not own:
- the remaining 110.26 applicability or exception tree;
- broad NEC table interpretation;
- project inputs or compliance evaluation;
- graph relationships outside those directly needed by this table path.

Completion:
- one reviewed 110.26 table-derived requirement round-trips through the generic lookup representation;
- source condition, classification, table selection, and resulting dimensional requirement remain separately traceable;
- ambiguity blocks reviewed semantic promotion;
- public fixtures remain synthetic and source-safe.

Successor: `feature/nec-110-26-applicability-exceptions`.
