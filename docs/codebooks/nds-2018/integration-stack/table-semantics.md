# NDS 2018 table semantics

Predecessor: `feature/nds-2018-equation-semantics`.

Owns:
- NDS participation in the shared table-semantic contract if that contract has landed, or the smallest source-independent contract extension NDS proves necessary;
- reviewed header relationships, row/column keys, units, continuations, notes/footnotes, applicability anchors, and lookup provenance for selected NDS table families;
- explicit ambiguous header/span and lookup states;
- separation of structural geometry from reviewed semantic dimensions and engineering meaning.

Does not own:
- an NDS-only competing table model;
- converting every NDS table before reviewed evidence exists;
- inferring semantics solely from rectangular extraction;
- project compliance or arbitrary calculation execution.

Completion:
- at least one difficult NDS table family has reviewed semantic coverage over exact structural evidence;
- units, headers, continuations, and footnotes round-trip through the chosen contract;
- ambiguous relationships fail closed;
- table lookups preserve exact source and selection provenance;
- measured structural table coverage remains distinct from reviewed semantic table coverage.

Successor: `feature/nds-2018-semantic-review`.