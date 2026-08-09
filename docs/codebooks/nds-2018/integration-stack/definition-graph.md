# NDS 2018 definition graph

Predecessor: `feature/nds-2018-reference-graph`.

Owns:
- deterministic identity for distributed NDS definition entries;
- evidence-backed definition scope and context rather than global term matching;
- definition-use edges with resolved, unresolved, ambiguous, and cyclic states as applicable;
- preserving source definition evidence separately from use sites without copying definition prose into downstream nodes;
- coordination with the shared semantic definition-use vocabulary when that contract exists.

Does not own:
- assuming every matching term resolves globally;
- semantic applicability or exception evaluation;
- equation symbol definitions unless they are explicitly within the equation-semantics contract;
- project-specific engineering interpretation.

Completion:
- distributed and chapter-local definition scope is represented explicitly;
- ambiguous and unresolved uses fail closed;
- graph IDs and serialization are deterministic;
- source-safe synthetic cases cover local/global conflict, unresolved use, and ambiguous use;
- private exact-source replay measures resolved versus unresolved definition-use coverage.

Successor: `feature/nds-2018-equation-semantics`.