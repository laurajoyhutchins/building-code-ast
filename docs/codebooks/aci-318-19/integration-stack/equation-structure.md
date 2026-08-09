# ACI 318-19 equation structure

Predecessor: `feature/aci-318-19-cross-page-hierarchy`.

Owns:
- structural recognition of displayed equations and publication-native equation designations;
- normative versus commentary equation source roles;
- multiline equation regions, adjacent designation evidence, and exact source provenance;
- explicit unsupported diagnostics for glyph loss, ambiguous grouping, or graphical math regions.

Does not own:
- mathematical expression semantics;
- symbol binding or unit normalization;
- executable engineering formulas;
- project calculations.

Completion:
- representative normative and commentary equations become valid `equation` nodes or explicit unsupported structures;
- equation identities are deterministic and role-specific;
- repeated private replay preserves source spans and designations;
- no commentary equation is promoted to normative authority.

Successor: `feature/aci-318-19-table-structure`.
