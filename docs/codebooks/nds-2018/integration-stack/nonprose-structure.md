# NDS 2018 non-prose structure

Predecessor: `feature/nds-2018-hierarchy`.

Owns:
- structural recognition of displayed equations and publication-native equation identifiers;
- table boundaries, continuations, geometry, headers-as-structure, and table-associated notes/footnotes without semantic lookup meaning;
- figure boundaries, captions, publication-native locators, and references without graphical engineering interpretation;
- explicit unsupported diagnostics for mathematical glyph loss, ambiguous table geometry, and graphical content not represented by text extraction.

Does not own:
- mathematical expression semantics or executable formulas;
- table lookup semantics;
- engineering meaning inferred from figures;
- whole-document completeness claims.

Completion:
- representative equations, dense/continued tables, figures, and table footnotes become valid Document AST structure or explicit unsupported nodes;
- publication-native locators drive deterministic identity where present;
- private-use mathematical glyphs cannot silently normalize into reviewed mathematics;
- synthetic geometry fixtures and private exact-source replay cover representative hazards;
- generic Document AST validation remains authoritative.

Successor: `feature/nds-2018-complete-document-ast`.