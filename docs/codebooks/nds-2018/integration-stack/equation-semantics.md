# NDS 2018 equation semantics

Predecessor: `feature/nds-2018-definition-graph`.

Owns:
- a reviewed boundary from structural equation regions to faithful glyph/token representation and, where justified, mathematical expression structure;
- publication-native equation identity, symbol bindings, units, source evidence, and explicit unresolved symbols;
- separation of equation recognition, glyph representation, mathematical parse, symbol definition, and engineering semantic meaning;
- deterministic calculation semantics only for notation that can be represented faithfully and reviewed.

Does not own:
- silently translating private-use glyph extraction into executable mathematics;
- solving arbitrary wood-design problems;
- table lookup semantics except where an equation explicitly references a separately modeled table;
- figure-derived engineering relationships.

Completion:
- reviewed source-safe equation fixtures cover faithful parse, unresolved symbol, unsupported glyph/notation, and unit-bearing cases;
- mathematical representations trace to exact structural equation evidence;
- unsupported or partially supported notation remains explicit;
- repeated parsing is deterministic;
- no executable formula is emitted solely because an equation region was detected.

Successor: `feature/nds-2018-table-semantics`.