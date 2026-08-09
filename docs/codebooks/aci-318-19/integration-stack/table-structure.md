# ACI 318-19 table structure

Predecessor: `feature/aci-318-19-equation-structure`.

Owns:
- table region detection, captions, continuation identity, and source-role preservation;
- cell geometry reconstruction, row/column boundaries, spanning headers, and table-associated notes/footnotes as structure;
- explicit unsupported diagnostics for ambiguous geometry or extraction loss;
- exact source coordinates and deterministic table identity.

Does not own:
- table lookup semantics;
- inferred engineering dimensions from geometry alone;
- interpolation behavior;
- project calculations.

Completion:
- representative normative and commentary tables become valid structural trees or explicit unsupported nodes;
- continuation and footnote attachment are deterministic from source evidence;
- commentary tables cannot silently become normative lookup data;
- private replay covers dense and continued table families.

Successor: `feature/aci-318-19-definition-reference-structure`.
