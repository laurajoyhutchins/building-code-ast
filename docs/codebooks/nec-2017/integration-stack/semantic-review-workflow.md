# NEC semantic review workflow

Predecessor: `feature/nec-110-26-reviewed-vertical-slice`.

Owns:
- NEC participation in the generic issue #4 semantic annotation/review workflow;
- explicit generated, reviewed, accepted, rejected, ambiguous, and unsupported states;
- reviewer identity/date, deterministic regeneration/diffing, exact source-span checks, and local-only restricted-source handling;
- source-safe gold fixture metadata without committing protected NEC expression.

Does not own:
- automatically accepting parser output;
- new semantic vocabulary unrelated to reviewed counterexamples;
- requiring every NEC provision to be semantically accepted;
- project compliance evaluation.

Completion:
- a contributor can generate, review, reject, amend, and regenerate an NEC semantic case reproducibly;
- approved interpretation is distinct from parser candidate output;
- source-span and structural mismatches are measurable;
- restricted-source review artifacts remain private while public receipts stay non-reconstructive.

Successor: `feature/nec-semantic-review-queue`.
