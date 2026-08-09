# NEC-proven table lookup semantic contract

Predecessor: `feature/nec-110-26-reviewed-table`.

Owns:
- the smallest publication-neutral semantic contract justified by the reviewed 110.26 table case;
- explicit lookup inputs/classifications, selected branch/cell, units, qualifications, and derivation provenance;
- unresolved or ambiguous lookup states and exact evidence links;
- deterministic serialization and source-safe synthetic fixtures.

Does not own:
- automatic semantic interpretation of arbitrary tables;
- a numeric solver or project evaluation engine;
- NEC-specific condition classification beyond adapter inputs;
- retrofitting unrelated table families without reviewed evidence.

Completion:
- a reviewed table-derived requirement can preserve the full path from source condition through classification and selected table result;
- lookup provenance cannot be replaced by a naked numeric threshold;
- unsupported table semantics remain explicit;
- the contract has source-independent meaning proven by at least the NEC case that motivated it.

Successor: `feature/nec-110-26-table-lookup`.
