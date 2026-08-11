# ASCE/SEI 7-22 whole-document replay measurement

Status: measured against the exact retained licensed artifact; current whole-document Document AST replay does not validate.

## Exact coordinate

The measurement used `asce-7-2022.pdf` at SHA-256 `522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0`, 55,404,349 bytes and 1,047 PDF pages. The source bytes remain outside Git.

Two independent measurement passes over the same retained bytes produced the same source-safe core measurement. Canonical JSON of that core measurement, excluding the self-describing `determinism` object, has SHA-256 `cab3a2463cfdb20546b05d2000ad81976c0b7a208c33928464fdc31371a1bf18`.

## Result

The current ASCE adapter is deterministic on the measured observations, but whole-document replay reaches the generic Document AST uniqueness gate with duplicate publication locators. This is a structural coverage failure, not evidence that the source is malformed.

The retained document yielded 18,063 body text blocks on 1,035 pages under the adapter's existing body-region bounds. Current recognizers observed 41 chapter, 1,550 section, 417 equation, 85 table, and 155 figure occurrences. Those observations include locator collisions in every recognized family: 8 chapter, 59 section, 12 equation, 14 table, and 34 figure locators collide.

The measurement also exposes source families that the current numeric-only hierarchy grammar does not model: 32 commentary chapter candidates, 859 commentary section candidates, 43 appendix heading candidates, and 919 appendix/commentary-appendix section candidates. These counts are evidence categories only; they do not claim successful parse, semantic interpretation, review, or executable engineering capability.

## Proven boundary

A whole-document parser cannot safely promote every text block matching a locator-shaped regex into a publication node. The collisions show that references and other source contexts can resemble declarations. Commentary and appendix hierarchy also require source-role-aware locators rather than normalization into ordinary paragraphs.

The next implementation correction should therefore be bounded to declaration-context and source-role discrimination before expanding semantic interpretation. It should preserve unclassified commentary, appendix, graphical, and ambiguous regions explicitly until stronger source evidence supports promotion.

No protected prose, equations, tables, figures, maps, page images, or reconstructive AST corpus is retained here. The committed measurement contains only exact artifact identity, aggregate counts, deterministic measurement identity, and failure-family evidence.
