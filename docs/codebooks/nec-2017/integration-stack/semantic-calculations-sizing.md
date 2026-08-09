# NEC semantic coverage: calculations and sizing

Predecessor: `feature/nec-semantic-review-queue`.

Owns:
- reviewed coverage for arithmetic relationships, sizing chains, adjustment/correction factors, units, referenced lookup values, minima/maxima, and intermediate derivations found across the NEC;
- publication-neutral calculation vocabulary only where reviewed cases require it;
- unresolved symbols, missing inputs, rounding/selection rules, and exact derivation provenance;
- separation between rule representation and any later project evaluation engine.

Does not own:
- inventing project inputs;
- executing a design or compliance solver as part of AST construction;
- table semantics already owned by the table-selection lane except as referenced inputs;
- domain-specific shortcuts that erase derivation provenance.

Completion:
- representative NEC calculation/sizing archetypes are reviewed and measurable;
- accepted outputs preserve units, operands, lookup dependencies, operations, and unresolved states;
- missing or ambiguous symbols block false certainty;
- generated semantics remain distinct from approved review.

Sibling successors: other semantic-archetype coverage lanes; all converge at semantic coverage closeout.
