# NEC 2017 semantic coverage closeout

Primary predecessor: `feature/nec-semantic-dimensional-thresholds`.
Required sibling coverage branches before implementation/landing:
- `feature/nec-semantic-table-selection`;
- `feature/nec-semantic-calculations-sizing`;
- `feature/nec-semantic-equipment-wiring-classification`;
- `feature/nec-semantic-permissions-alternatives-edge-cases`.
Required measured dependencies: `feature/nec-2017-structural-measurement` and `feature/nec-2017-graph-reconciliation`.

Owns:
- integrating the semantic-archetype coverage lanes and all bounded review packs generated from the NEC review queue;
- whole-publication semantic support/review measurement with exact denominators;
- requiring every in-scope normative structural node to reach a terminal state: accepted, rejected, ambiguous, or explicitly unsupported;
- documenting remaining unsupported semantic families without recasting them as successful parses.

Does not own:
- adding new semantic feature families merely to improve closeout percentages;
- treating deterministic generated output as human-reviewed;
- project compliance evaluation;
- suppressing unsupported or ambiguous terminal states.

Completion:
- no in-scope normative node remains only generated or review-pending;
- accepted semantic nodes validate against the generic Provision AST and complete provenance graph;
- rejected/ambiguous/unsupported states are measurable and source-linked;
- whole-edition semantic claims are precisely calibrated to the terminal review inventory.

Successor: `feature/nec-2017-provenance-export`.
