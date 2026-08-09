# IBC 2018 definition graph

Predecessor: `feature/ibc-reference-graph` (PR #59)

Owns:
- stable IBC definition identities projected into the generic provenance graph;
- definition scope/context and definition-use relationships;
- duplicate, unresolved, ambiguous, and cyclic definition relationships;
- exact source-evidence retention and deterministic serialization.

Does not own:
- applicability semantics;
- table or calculation meaning;
- amendments, adoption, jurisdiction, or compliance conclusions;
- copied definition text at use sites.

Completion:
- synthetic fixtures cover shared, missing, ambiguous, and cyclic definition cases;
- the committed source-safe IBC definition inventory projects without losing evidence;
- graph behavior coordinates with issue #5 and Provision AST definition-use work in issue #3;
- unsupported cases remain explicit.

Successor: `feature/ibc-applicability-semantics`.
