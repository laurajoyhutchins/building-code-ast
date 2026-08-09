# ACI 318-19 table semantics

Predecessor: `feature/aci-318-19-equation-semantics`.

Owns:
- ACI participation in the shared table-semantic contract;
- reviewed header, dimension, unit, note/footnote, applicability, and lookup provenance for selected difficult normative table families;
- explicit source-role preservation for commentary tables;
- ambiguity handling for spans, implied dimensions, limits, interpolation, and special cases.

Does not own:
- semantics inferred from rectangular extraction alone;
- automatic interpolation without explicit reviewed rules;
- commentary tables as normative lookup data;
- project calculations.

Completion:
- selected difficult table families have reviewed semantic dimensions with exact cell/header/note provenance;
- lookup semantics are separate from structural reconstruction;
- ambiguous applicability remains explicit;
- shared generic table models are extended only for demonstrated source-independent gaps.

Successor: `feature/aci-318-19-commentary-correspondence`.
