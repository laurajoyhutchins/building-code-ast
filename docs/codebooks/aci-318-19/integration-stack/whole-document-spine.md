# ACI 318-19 whole-document spine

Predecessor: `aci-318-19/document-ast-source-roles` / PR #93.

Owns:
- assembling all retained ACI 318-19 PDF pages into one deterministic Document AST;
- publication-wide chapter, section, subsection, normative, commentary, and publication-structure identity;
- exact PDF-page and printed-page provenance across the whole artifact;
- cross-page continuation without creating duplicate publication-native identities;
- generic Document AST validation and deterministic serialization for the complete structural spine.

Does not own:
- page-furniture cleanup beyond what is required to assemble the spine;
- equation, table, figure, definition, or reference semantics;
- Provision AST interpretation;
- project design or compliance evaluation.

Completion:
- the exact retained artifact can be represented as one deterministic publication tree;
- normative and commentary identities remain distinct across page boundaries;
- repeated private runs produce stable structural identities and serialization;
- unsupported or ambiguous regions remain explicit rather than being flattened;
- no protected generated AST is committed.

Successor: `feature/aci-318-19-region-classification`.
