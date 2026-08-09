# NEC 110.26 definition and reference edges

Predecessor: `feature/nec-110-26-applicability-exceptions`.
Sibling dependency: `feature/nec-2017-graph-reconciliation`.

Owns:
- binding the reviewed 110.26 semantic slice to the exact definition and reference graph edges it depends on;
- preserving resolved, unresolved, and ambiguous dependency states in semantic provenance;
- blocking accepted semantic promotion when a required dependency is unresolved or conflicting;
- human-readable traceability from semantic dependency to exact graph/source evidence.

Does not own:
- building the whole-edition graph;
- selecting unrelated definitions or references;
- treating a resolved citation as automatic semantic incorporation;
- project compliance evaluation.

Completion:
- every definition/reference dependency used by the reviewed 110.26 representation is an explicit provenance edge;
- unresolved required dependencies prevent false semantic certainty;
- graph identity remains separate from semantic interpretation;
- synthetic tests prove failure behavior without protected NEC expression.

Successor: `feature/nec-110-26-provision-adapter`.
