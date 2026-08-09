# IBC 2018 definition graph

Predecessor: PR #59, merged as `0d52d92c0929d79ded4907ce9e4b8906d95806c9`.

Implemented boundary:
- stable publication-specific IBC definition graph identities;
- definition scope/context and exact source-safe evidence retention;
- explicit definition-use candidate relationships with resolved, unresolved, and ambiguous states;
- duplicate and unknown-candidate validation that fails closed;
- deterministic serialization and explicit cycles for resolved definition-to-definition uses;
- projection of the complete committed source-safe IBC definition inventory.

This PR intentionally does not own the generic cross-publication provenance-graph core. Generic promotion and common graph contracts remain separately scoped by PR #126. The IBC projection should be adaptable to that core rather than defining it by accident.

Does not own:
- lexical discovery of definition uses from restricted source prose;
- choosing a governing definition from ambiguous candidates;
- applicability semantics;
- table or calculation meaning;
- amendments, adoption, jurisdiction, or compliance conclusions;
- copied definition text at use sites.

Evidence:
- the committed IBC inventory projects one graph definition per source-safe definition record;
- source record identity, source section, scope, review state, source anchor, and definition-text hash survive projection;
- synthetic fixtures cover resolved, missing, ambiguous, cyclic, duplicate, and unknown-candidate cases;
- raw definition prose is not emitted by the graph;
- private-source replay is not required for this source-safe projection and was not performed.

Remaining gap:
- the committed corpus does not yet supply reviewed IBC definition-use bindings. The use-edge contract is exercised synthetically and must not be described as broad real-source use-site coverage.

Successor: PR #63 / `feature/ibc-applicability-semantics`.
