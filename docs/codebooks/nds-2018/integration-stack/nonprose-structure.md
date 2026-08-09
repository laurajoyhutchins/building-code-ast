# NDS 2018 non-prose structure

Predecessor: merged PR #106 `feature/nds-2018-hierarchy`.

Owns:
- native equation identifier recognition while preserving observed glyph/text evidence without mathematical interpretation;
- table caption identity, table-region ownership, repeated-locator continuation grouping, and table-associated note/footnote attachment;
- figure caption identity with explicit graphical-body availability/unsupported state;
- replacement of hierarchy-stage deferred non-prose placeholders only where stronger source evidence establishes a neutral equation, table, or figure structure;
- deterministic publication-native locators and exact PDF page/bbox provenance for every recognized non-prose node.

Does not own:
- executable equation mathematics, symbol binding, units, or engineering calculation semantics;
- table header/key/unit/lookup semantics;
- interpretation of figure graphics;
- reference resolution;
- whole-document structural completeness claims.

Completion:
- source-safe synthetic fixtures cover separated and inline equation identifiers, figure captions with unavailable graphics, table footnotes, and a repeated-locator `(Cont.)` table spanning consecutive pages;
- the shared Document AST validates after non-prose overlay without duplicate source ownership inside recognized regions;
- ambiguous caption/reference look-alikes fail closed;
- private exact-source replay confirms representative native patterns before whole-document integration.

Successor: `feature/nds-2018-complete-document-ast`.
