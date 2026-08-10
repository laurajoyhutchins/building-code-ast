# ASHRAE 90.1-2016 numeric-heading typography replay

Canonical roadmap: issue #219.

This evidence records the exact-source replay for the numeric-heading correction that follows the whole-document measurement in #249. It does not claim whole-document validity or semantic completeness.

## Exact retained artifact

- SHA-256: `275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162`
- size: 3,475,675 bytes
- physical pages: 388
- native PDF outline entries: 720

The retained bytes were rehashed before this replay. No source prose, outline titles, page images, reconstructive tables, figures, equations, or generated private AST are committed.

## Evidence that distinguishes body headings

The pre-fix measurement produced 805 numeric-heading candidate occurrences. Comparing exact page/locator observations to the native outline exposed a clean typography boundary in the retained artifact:

- all 370 pre-fix candidates that matched a numeric outline locator on the exact outline page began with 10-point `Helvetica-Bold` source text;
- none of the 435 pre-fix wrong-page or non-outline numeric candidates had that same first-span typography;
- the publication's top-level body section headings form a separate 11-point `Helvetica-Bold` family before the first appendix;
- two exact-page deep headings are locator-only 10-point bold blocks, so a title cannot be required or invented for every subsection heading.

The native PDF outline is used only to evaluate candidate behavior. Runtime recognition depends on source typography/layout and does not read the outline.

## Implemented recognition boundary

The ASHRAE 90.1 adapter now recognizes ordinary numeric body hierarchy only when all of these conditions hold:

1. the observation is before appendix material;
2. no explicit non-prose structure hint owns the observation;
3. the normalized block is a numeric publication-locator shape;
4. the first visible PDF text span uses `Helvetica-Bold`;
5. top-level headings use the observed 11-point family and contain source title text;
6. deeper headings use the observed 10-point family, while permitting a locator-only block with `label=None`.

Numeric-looking text without visual font evidence remains prose. Numeric-looking material after an appendix begins does not reset the body hierarchy.

## Exact-source replay after correction

Replaying the corrected recognizer across all 8,897 content-region blocks yields:

- paragraphs: 8,451
- subsections: 372
- sections: 12
- tables: 39
- figures: 15
- appendices: 8
- equations: 0

Numeric hierarchy after correction:

- candidate occurrences: 384
- unique candidate locators: 384
- duplicate numeric candidate occurrences: 0
- unique candidates also present in the native numeric outline: 383
- native numeric outline locators without a current candidate: 73
- candidate locators absent from the native numeric outline: 1
- exact-page matches among the 383 outline-backed candidates: 383
- near-page-only matches: 0
- far-only matches: 0

The one candidate absent from the native numeric outline is Section 12. The retained source profile independently establishes Section 12 as part of the publication body, so this is not treated as evidence of a false positive.

The 73 still-unmatched outline locators are not silently synthesized. They remain a later structural evidence gap.

## Next whole-document blocker

Removing numeric-heading collisions does not make the whole publication validatable. The next deterministic duplicate locator in current structural recognition is:

- locator: `figure:Annex1-2`
- first observed physical page: 319
- repeated observed physical page: 382

That collision is in the reproduced reference-annex region and remains visible. It is not suppressed, renamed, or resolved by this heading PR.

## Scope boundary

This correction does not add appendix-native sublocator grammar, model the reproduced-annex source-role boundary, resolve repeated figure identity, reconstruct tables/figures/equations, or interpret energy requirements. It only replaces the disproven text-only numeric-heading heuristic with exact-source typography evidence and keeps the next failure explicit.
