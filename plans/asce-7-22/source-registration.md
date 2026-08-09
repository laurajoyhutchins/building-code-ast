# ASCE 7-22 source registration

Scope-only stub for exact retained-artifact registration after merged PR #87.

## Owns

- bind ASCE/SEI 7-22 to the shared publication-neutral source register
- exact SHA-256 `522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0`
- retained filename, media type, size, page count, edition/publication identity, rights/access state
- explicit preservation of unresolved printing/correction state
- stable `DocumentSourceArtifact` identity derived from the registered source

## Does not own

- parser changes
- source extraction or search
- whole-document AST generation
- equation/table/figure/map semantics
- protected source payloads

## Successor

`feature/asce-7-22-whole-document-inventory`.
