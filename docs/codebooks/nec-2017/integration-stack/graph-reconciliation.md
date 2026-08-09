# NEC 2017 graph reconciliation

Predecessor: `feature/nec-2017-reference-graph`.

Owns:
- whole-publication reconciliation between structural locators, definition identities, internal references, external designations, and Annex A relationships;
- diagnostics for duplicate, conflicting, missing, ambiguous, and cyclic relationships;
- deterministic graph integrity and coverage reporting tied to the structural measurement denominator;
- the graph boundary consumed by reviewed NEC semantic projections.

Does not own:
- deciding semantic applicability merely because an edge resolves;
- importing external source text;
- rewriting the base Document AST;
- project compliance or jurisdiction selection.

Completion:
- graph coverage reconciles against the complete measured NEC structural inventory;
- unresolved and conflicting relationships remain explicit blockers where semantics depend on them;
- deterministic serialization and traversal pass whole-edition private replay;
- a human-readable trace can follow supported semantic dependencies back to exact source evidence.

Successor: consumed as a sibling dependency by the NEC 110.26 Provision AST path and later semantic coverage lanes.
