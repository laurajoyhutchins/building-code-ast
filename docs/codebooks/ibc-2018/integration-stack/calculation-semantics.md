# IBC 2018 calculation semantics

Predecessor: `feature/ibc-table-reviewed-slice`.

Owns:
- generic Provision AST calculation and table-lookup semantics required by IBC;
- variable/input/output identities, units, source equation identity, applicability, and unresolved symbols;
- bounded reviewed IBC equation/table cases.

Does not own:
- an engineering solver;
- broad interpretation of all IBC equations;
- project-specific compliance conclusions.

Completion:
- issue #3 calculation/table-lookup vocabulary is schema-backed;
- synthetic fixtures cover formulas, table lookups, units, and unresolved symbols;
- representative IBC cases preserve exact evidence and review state;
- unsupported mathematical syntax remains explicit.

Successor: `feature/ibc-external-reference-graph`.
