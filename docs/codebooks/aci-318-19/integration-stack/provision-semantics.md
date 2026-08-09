# ACI 318-19 provision semantics

Predecessor: `feature/aci-318-19-commentary-correspondence`.

Owns:
- ACI participation in the generic Provision AST for normative requirements, prohibitions, permissions, regulated subjects, actions, recursive conditions, alternatives, and exceptions;
- numeric comparisons, limits, ranges, quantities, and units with exact normative provenance;
- semantic links to already-structured equations, tables, definitions, and references;
- explicit parser-versus-reviewed state and unsupported semantic cases.

Does not own:
- an ACI-specific competing semantic AST;
- commentary as normative rule evidence;
- structural parsing already owned by Document AST stages;
- project design, analysis, responsibility assignment, or compliance conclusions.

Completion:
- reviewed representative normative provisions map into shared semantics where faithful;
- demonstrated generic gaps are extended minimally and source-independently;
- commentary may support review but cannot replace the normative evidence span;
- unsupported or ambiguous semantics remain explicit.

Successor: `feature/aci-318-19-semantic-review`.
