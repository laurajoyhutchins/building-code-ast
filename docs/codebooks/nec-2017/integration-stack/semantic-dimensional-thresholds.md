# NEC semantic coverage: dimensional thresholds

Predecessor: `feature/nec-semantic-review-queue`.

Owns:
- deliberate reviewed coverage for dimensional, clearance, spacing, height, depth, length, quantity, and threshold-style NEC requirements;
- reuse of the generic condition/action/unit vocabulary proven by the 110.26 slice;
- counterexamples that expose genuinely missing semantic primitives, with vocabulary changes kept publication-neutral where possible;
- coverage and parser/review disagreement reporting for this archetype.

Does not own:
- table-driven selection families except where already represented by shared lookup contracts;
- engineering calculations beyond direct threshold relationships;
- project compliance evaluation;
- article-specific semantic dialects.

Completion:
- representative dimensional rule shapes across multiple NEC articles are reviewed and measured;
- accepted output preserves units, qualifiers, conditions, exceptions, and provenance;
- unsupported variants remain explicit and queued;
- no protected NEC expression is committed.

Sibling successors: other semantic-archetype coverage lanes; all converge at semantic coverage closeout.
