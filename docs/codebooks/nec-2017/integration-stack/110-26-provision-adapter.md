# NEC 110.26 Provision AST adapter

Predecessor: `feature/nec-110-26-definition-reference-edges`.

Owns:
- projecting supported reviewed 110.26 clause shapes into the generic Provision AST;
- preserving modality, subject, applicability/conditions, actions/requirements, exceptions, table-derived values, units, definition/reference dependencies, and exact source provenance;
- explicit unsupported semantic nodes where the generic AST cannot honestly represent reviewed meaning;
- deterministic semantic identity without replacing the structural Document AST.

Does not own:
- a competing NEC-only semantic AST;
- project input evaluation or compliance decisions;
- promotion of unreviewed parser candidates;
- whole-NEC semantic coverage.

Completion:
- the reviewed 110.26 family can project to generic Provision AST without losing the evidence chain;
- unsupported or ambiguous structures remain explicit;
- Document AST and graph inputs remain immutable;
- public tests are synthetic and private replay verifies exact-source provenance.

Successor: `feature/nec-110-26-reviewed-vertical-slice`.
