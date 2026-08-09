# NEC 2017 complete Document AST

Predecessor: `feature/nec-2017-nonprose-structure`.

Owns:
- assembling the complete retained NEC 2017 publication into one deterministic validated Document AST;
- complete source-region accounting against the corpus contract;
- immutable source-artifact identity and exact source-span provenance;
- explicit unsupported and ambiguous structural states without silent omission;
- deterministic private whole-document replay and source-safe validation receipts.

Does not own:
- semantic Provision AST interpretation;
- definition/reference resolution;
- table lookup meaning;
- compliance or project evaluation.

Completion:
- every in-scope source region is owned by a Document AST node or an explicit unsupported/ambiguous record;
- whole-document serialization and IDs are deterministic;
- source spans and publication roles validate against the exact retained artifact;
- no private generated AST or protected source expression is committed.

Successor: `feature/nec-2017-structural-measurement`.
