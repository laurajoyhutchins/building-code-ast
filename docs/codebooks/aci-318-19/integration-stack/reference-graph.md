# ACI 318-19 reference graph

Predecessor: `feature/aci-318-19-structural-measurement`.

Owns:
- deterministic resolution of normative-to-normative, commentary-to-normative, commentary-to-commentary, table, equation, figure, appendix, and external-standard references;
- exact source spans for every reference edge;
- unresolved and ambiguous target states;
- source-role-preserving target identity without copying target text.

Does not own:
- definition-use resolution;
- semantic applicability or exception meaning;
- external-source ingestion;
- project compliance.

Completion:
- supported internal references resolve to deterministic AST identities;
- commentary edges cannot be mistaken for normative authority;
- unresolved references remain explicit;
- whole-document private replay produces stable graph counts and diagnostics.

Successor: `feature/aci-318-19-definition-graph`.
