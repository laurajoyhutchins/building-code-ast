# ASCE 7-22 table semantics

Scope-only reviewed table-meaning lane.

## Owns
- semantic row/column dimensions only after geometry is stable
- explicit units and display forms
- table-note/footnote applicability relationships
- reviewed lookup/interpolation contracts where source behavior is unambiguous
- diagnostics for semantic ambiguity and unsupported lookup behavior

## Does not own
- inferring meaning from alignment alone
- project-specific lookups or compliance conclusions

## Dependency
Requires `feature/asce-7-22-definition-reference-graph` where table terms/symbols require scoped resolution.

## Successor
`feature/asce-7-22-semantic-candidates`.
