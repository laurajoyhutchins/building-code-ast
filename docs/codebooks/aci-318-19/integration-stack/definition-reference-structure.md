# ACI 318-19 definition and reference structure

Predecessor: `feature/aci-318-19-table-structure`.

Owns:
- structural recognition of prose definitions, notation definitions, internal references, and external-standard citations;
- source-role-aware definition and reference identity;
- exact source spans for reference mentions and unresolved targets;
- explicit separation between structural mention detection and semantic resolution.

Does not own:
- global definition resolution;
- semantic dependency interpretation;
- external-source import;
- Provision AST meaning.

Completion:
- representative definition and reference forms are structurally identified with exact provenance;
- normative terms cannot resolve structurally to commentary text merely by wording similarity;
- unresolved and ambiguous references remain explicit;
- private replay measures supported and unsupported reference forms.

Successor: `feature/aci-318-19-notes-figures-appendices`.
