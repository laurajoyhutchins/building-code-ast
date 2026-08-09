# NFPA 13 (2019) calculation semantics

Predecessor: `feature/nfpa13-table-reviewed-slice` (PR #80)

Owns:
- the issue #3 calculation and table-lookup vocabulary exercised by reviewed NFPA 13 cases;
- symbolic inputs, units, referenced lookup values, operations, and unresolved symbols;
- exact derivation provenance from calculated semantic nodes back to source evidence;
- parser-versus-reviewed interpretation state for calculation candidates.

Does not own:
- a hydraulic or sprinkler-design solver;
- project-specific numeric inputs;
- engineering conclusions or compliance evaluation;
- figure-derived geometry or implicit diagram interpretation.

Completion:
- synthetic fixtures cover a bounded calculation with units, referenced lookup inputs, and an unresolved symbol;
- semantic calculations remain declarative rather than executable engineering authority;
- every accepted value has a provenance path to source or declared input evidence;
- unsupported calculation shapes remain explicit.

Successor: `feature/nfpa13-provision-adapter`.
