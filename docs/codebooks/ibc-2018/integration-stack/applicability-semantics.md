# IBC 2018 applicability semantics

Predecessor: `feature/ibc-definition-graph`.

Owns:
- generic Provision AST applicability and scope semantics needed by IBC;
- nested applicability, scope qualifiers, and exact source spans;
- parser inference/review status and explicit unsupported forms;
- bounded IBC fixtures proving the generic contract.

Does not own:
- exception semantics beyond applicability links;
- table lookup meaning;
- calculations, amendments, adoption, jurisdiction, or compliance conclusions.

Completion:
- schema semantics are documented and versioned under issue #3;
- synthetic fixtures cover nested applicability and unresolved scope;
- representative IBC structures project without source-span loss;
- unsupported syntax fails visibly rather than approximating.

Successor: `feature/ibc-exception-semantics`.
