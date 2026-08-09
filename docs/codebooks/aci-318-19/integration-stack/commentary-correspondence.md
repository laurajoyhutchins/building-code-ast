# ACI 318-19 commentary correspondence

Predecessor: `feature/aci-318-19-table-semantics`.

Owns:
- source-backed Code/Commentary correspondence beyond same-page exact numeric matching;
- deterministic handling of omitted commentary, broader commentary sections, cross-page correspondence, and ambiguous relationships;
- a minimal explicit correspondence vocabulary justified by reviewed source evidence;
- commentary references as explanatory relationships rather than normative containment.

Does not own:
- turning commentary into governing code text;
- automatic correspondence from string similarity alone;
- speculative relationship types such as `explains` or `illustrates` without evidence;
- Provision AST semantics.

Completion:
- supported commentary relationships resolve deterministically to role-distinct normative identities;
- unresolved or one-to-many correspondence remains explicit;
- correspondence survives serialization and whole-document replay;
- commentary authority remains structurally non-normative.

Successor: `feature/aci-318-19-provision-semantics`.
