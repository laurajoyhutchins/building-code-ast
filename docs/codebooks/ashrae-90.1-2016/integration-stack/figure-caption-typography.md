# ASHRAE 90.1-2016 figure-caption typography replay

Canonical roadmap: issue #219.

This evidence follows the numeric-heading correction in #250. It records the exact-source distinction between automatic figure-caption observations and Annex 1 listing rows. It does not claim figure completeness, graphical semantics, or whole-document validity.

## Exact retained artifact

- SHA-256: `275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162`
- size: 3,475,675 bytes
- physical pages: 388
- native PDF outline entries: 720

The retained bytes were rehashed before this replay. No source prose, outline titles, page images, figure images, reconstructive tables, or generated private AST are committed.

## Corrected diagnosis

After #250 eliminated numeric locator collisions, the next deterministic collision was `figure:Annex1-2`, first observed on physical page 319 and repeated on physical page 382.

Exact page inspection showed that both observations are inside Reference Standard Reproduction Annex 1. The earlier possibility of a cross-publication identity collision was therefore rejected.

Physical page 319 is the Annex 1 opening/material-list page. Its three `Figure Annex1-*` rows are listing entries in regular 8.5-point Helvetica. Physical page 382 contains the actual `Annex1-2` figure caption in 8.5-point Helvetica-Bold.

Across the exact artifact before this correction, automatic `Figure ...` recognition produced:

- 15 candidate blocks;
- 12 candidate blocks in 8.5-point Helvetica-Bold, with 12 unique locators;
- 3 regular 8.5-point Helvetica listing rows, all on physical page 319;
- one duplicate locator, created by promoting the `Annex1-2` listing row alongside its real bold caption.

## Implemented recognition boundary

Automatic ASHRAE 90.1 figure promotion now requires all of the following:

1. no explicit non-prose structure hint owns the observation;
2. the normalized block begins with a publication figure locator;
3. the first visible PDF text span uses `Helvetica-Bold`;
4. the first visible span is in the observed 8.5-point caption family.

A `Figure ...` text block without visual font evidence remains prose.

An explicit source-backed `structure_hint="figure"` remains authoritative. It prefers the supplied native locator and may use the observed figure locator when the hint is explicit, without requiring the automatic-caption typography gate.

The whole-document measurement calls the same automatic figure recognizer, so measurement does not continue to count the superseded raw text pattern.

## Exact-source replay after correction

Replaying the final recognizer across all 8,897 content-region blocks yields:

- paragraphs: 8,454
- subsections: 372
- sections: 12
- tables: 39
- figures: 12
- appendices: 8
- equations: 0

The 12 automatically recognized figures have 12 unique locators. The current measured structural locator set has zero duplicate locators.

The numeric hierarchy established by #250 is unchanged: 384 unique numeric candidates with zero numeric duplicates.

`duplicate_locator_free` is deliberately a narrow measurement. It means only that no two currently recognized structural observations share the same locator. It does not establish that the complete private source can already be materialized into a valid generic Document AST, that all source structures are recognized, or that any figure semantics are understood.

## Remaining figure evidence gaps

The retained artifact contains additional actual Annex 1 figure captions whose rotated placement lies outside the current ASHRAE 90.1 body-content boundary. In particular, the actual `Annex1-1` and `Annex1-3` captions are not recovered by the current automatic content-region pass.

Those observations remain a separate geometry/content-boundary deficiency. This PR does not widen content bounds, infer rotated figure ownership, or claim a complete figure denominator.

## Scope boundary

This correction does not model Annex 1 mixed source-role semantics, recover rotated figures, add figure-image semantics, change table or equation recognition, add appendix-native sublocator grammar, or interpret energy requirements. It removes one proven false-positive family and leaves the remaining unsupported structures visible.
