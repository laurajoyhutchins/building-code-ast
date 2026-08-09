# NDS 2018 non-prose structure

Status: implemented and exact-source measured.

Canonical roadmap: #219.

Predecessor: merged PR #106, NDS hierarchy.

## Owns

- native equation identifier recognition while preserving observed glyph/text evidence without mathematical interpretation;
- table caption identity, table-region ownership, repeated-locator continuation grouping, and table-associated note/footnote attachment;
- figure caption identity with explicit graphical-body availability/unsupported state;
- replacement of hierarchy-stage deferred non-prose placeholders only where stronger source evidence establishes a neutral equation, table, or figure structure;
- deterministic publication-native locators and exact PDF page/bbox provenance for every recognized non-prose node.

## Does not own

- executable equation mathematics, symbol binding, units, or engineering calculation semantics;
- table header/key/unit/lookup semantics;
- interpretation of figure graphics;
- reference resolution;
- whole-document structural completeness claims.

## TDD evidence

Initial converged RED head: `aec0474b7f90e1f5623003d71c1eca70fc1fceb5`.

At RED, the repository suite failed only because `building_code_ast.ingest.nds2018_nonprose` did not exist.

First GREEN implementation head: `a02da2acd664c8e2b430806ce9a9ab447f4f7026`.

Exact-source measurement then exposed two source-layout families not covered by that first GREEN:

1. native equation labels separated from a same-baseline left-side expression even when the expression block contains no private-use glyph;
2. short inline native equation blocks whose extracted text loses both an equals sign and private-use glyphs.

The first measured family was captured by RED head `1c7f6504a7f6cd459e5de45b697f028b4aa2790e` and fixed at GREEN head `3929227299b9aee93218646ceaf922473d0183ee`.

The second measured family was captured by RED head `2ba804ba537acc468f71d2f6b0068d7b19eac4b6`; CI ran 453 tests with exactly one error for the new missing short-inline equation node while LORE remained green. The bounded fix head is `63ab28a539aa94a9da22ef4b9b51670cf77ada18`, where CI, LORE, and Deciduous archaeology all pass. The short-inline fallback is capped at a 40-character pre-label text fragment; the exact retained artifact's measured unsupported family had a maximum of 33 characters, and a longer prose look-alike remains a negative test.

## Exact-source replay receipt

Retained artifact: `nds-2018.pdf`.

- size: 6,791,825 bytes;
- SHA-256: `581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4`;
- registered identity match: exact;
- physical page count: 206;
- physical page size: 612 × 783 PDF points.

A private whole-artifact structural survey recorded only non-reconstructive source-safe facts:

- 79 native equation-label observations;
- 50 label-only equation observations: 25 preceded by a private-use-glyph expression block and 25 paired to a short same-baseline expression block without that signal;
- 29 inline equation-label observations: 20 already carrying an equals/private-use signal and 9 in the bounded short-inline loss-of-signal family;
- 24 anchored table-caption observations;
- 39 anchored figure-caption observations;
- 3 adjacent repeated table-identity continuations: table 12A on PDF pages 106–107, table 12J on pages 118–119, and table 12P on pages 124–125.

Representative exact-source inspection also confirmed figure 12A on PDF page 87 and table 12A across PDF pages 106–107. No protected source prose, page image, reconstructive table content, or extracted corpus is committed.

These measurements validate the non-prose recognition families in this PR. They are not a whole-document Document AST replay, a structural-completeness claim, or semantic coverage.

## Completion boundary

Synthetic fixtures cover separated, same-baseline, inline, and bounded short-inline equation identifiers; figure captions with unavailable graphics; table footnotes; and repeated-locator continued tables. The shared Document AST validates after overlay without stale duplicate source ownership inside promoted regions. Unsupported table bodies and unavailable figure graphics remain explicit.

After this PR lands, the next NDS task should be opened freshly from then-current `main`: deterministic whole-document Document AST replay and structural measurement against the exact retained artifact. Do not resurrect the retired planning PR #108.
