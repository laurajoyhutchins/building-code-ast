# ASCE 7-22 semantic candidates

Scope-only generic Provision AST integration lane.

## Owns
- source-role-aware provision/applicability candidates
- conditions, exceptions, scoped modifiers and numeric thresholds
- generic quantities and units
- equation-backed and table-backed semantic candidate links without duplicating source content
- diagnostics where generic semantics cannot faithfully represent a reviewed ASCE case

## Required siblings
- `feature/asce-7-22-equation-semantics`
- `feature/asce-7-22-table-semantics`
- `feature/asce-7-22-graphics-reference-frontier`
- this branch already descends from `feature/asce-7-22-definition-reference-graph`

## Does not own
- project calculations
- site-specific hazard determination
- compliance conclusions

## Successor
`feature/asce-7-22-reviewed-vertical-slice`.
