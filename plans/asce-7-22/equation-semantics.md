# ASCE 7-22 equation semantics

Scope-only mathematical representation lane.

## Owns
- deterministic token/glyph reconstruction where unambiguous
- superscript/subscript/group preservation
- symbol occurrences linked to scoped definitions
- explicit quantities and units with original display preserved
- reviewed executable-expression boundary and diagnostics

## Does not own
- project calculations
- compliance conclusions
- silently guessing ambiguous formulas

## Dependency
Requires `feature/asce-7-22-definition-reference-graph` for reviewed symbol resolution before executable status.

## Successor
`feature/asce-7-22-semantic-candidates`.
