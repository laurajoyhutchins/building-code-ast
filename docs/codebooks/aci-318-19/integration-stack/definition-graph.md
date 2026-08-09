# ACI 318-19 definition graph

Predecessor: `feature/aci-318-19-reference-graph`.

Owns:
- context- and source-role-aware definition identity and definition-use resolution;
- centralized, chapter-local, section-local, notation, equation-adjacent, and commentary terminology where exact-source evidence supports those scopes;
- explicit unresolved and ambiguous definition uses;
- prevention of normative term resolution to commentary prose merely by textual similarity.

Does not own:
- semantic applicability or exception parsing;
- equation execution;
- project-specific terminology or responsibility assignment.

Completion:
- supported definition uses resolve deterministically within explicit scope;
- symbol and prose-term scopes remain distinguishable where required;
- commentary definitions remain explanatory evidence unless the source designates otherwise;
- private replay produces stable resolution and ambiguity measurements.

Successor: `feature/aci-318-19-equation-semantics`.
