# ASHRAE 62.1-2016 Document AST replay evidence

Status: exact-source 60-page replay passes generic Document AST validation; structural completeness is not claimed.

## Exact retained artifact

The replay used the exact retained private artifact characterized by the source profile:

- filename: `ashrae-62_1-2016.pdf`
- SHA-256: `a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759`
- size: 1,193,586 bytes
- physical pages: 60

The bytes were hashed before replay. No source prose, page image, reconstructive table, extracted corpus, or generated private AST is committed here.

## Bounded foundation corrections

Private inspection of the exact artifact exposed source-backed defects in the first synthetic-only implementation:

1. The shared `PublicationIdentity` contract has no separate `addenda_set` field. The exact incorporated addenda identity and unresolved correction-layer state are preserved together in the supported publication-state field rather than widening the shared model without a demonstrated generic requirement.
2. Real appendix source structure occurs outside the generic 65-to-730 point body band. The ASHRAE 62.1 adapter uses source-specific retained bounds sufficient to include the observed appendix headings and lower-page source structures.
3. Appendix-native hierarchy uses locators such as `A1` and deeper descendants. The adapter preserves those locators beneath their owning appendix.
4. Parenthesized numeric endings occur in ordinary source blocks and are not sufficient evidence of an equation. Unhinted equation recognition requires equation-like syntax plus a publication-native trailing identifier.
5. Top-level Section recognition is restricted to the publication's Sections 1 through 9 and source-heading evidence, reducing promotion of numbered non-heading material.

These defects were first encoded as failing tests at RED head `d1dfddab7df401c7d61c3524c05f32d32eac3d27`. The bounded-foundation implementation landed through #181.

## Bounded exact-source replay

Representative exact-source slices passed generic `validate_document_ast` validation:

| Exact PDF slice | Result | Nodes | Source-safe type counts |
| --- | --- | ---: | --- |
| page 26 | pass | 15 | document 1; section 1; subsection 4; paragraph 6; equation 2; figure 1 |
| pages 13-14 | pass | 31 | document 1; section 1; subsection 8; paragraph 14; equation 7 |
| pages 29-30 | pass | 46 | document 1; section 1; subsection 5; paragraph 32; table 3; equation 3; figure 1 |

The slices exercise mandatory body hierarchy, normative appendix roles, appendix-native hierarchy, equations, tables, figures, and printed-page provenance. These are structural claims only.

## Repeated native table observations

The first 60-page replay failed closed on:

`duplicate document locator: table:6.2.2.1`

Whole-artifact source-safe observation found 28 table-caption blocks representing 17 native table identifiers. Six identifiers repeat, accounting for 17 observations across those repeated groups:

- four repeated groups occupy adjacent physical pages;
- two repeated groups contain more than one observation on the same physical page;
- 11 observations are additional occurrences beyond the six primary native identifiers.

#220 landed a publication-neutral occurrence classifier that distinguishes single, adjacent-page, same-page-duplicate, and discontiguous-page observation shapes without asserting semantic continuation. The ASHRAE adapter preserves one native `table:<locator>` plus explicit page-scoped `TABLE_HEADING` occurrences and emits a deferred-structure diagnostic.

With that change, exact replay advanced past all repeated table-locator collisions and failed closed on:

`duplicate document locator: section:C1`

## Appendix heading disambiguation

Exact-source coordinate and font inspection established that the second `C1` candidate was not a competing heading. A displayed mathematical layout was flattened by block-level text normalization into locator-like leading text, which the permissive appendix-section regex promoted to structural hierarchy.

The same recognition rule also promoted a numbered Appendix J bibliography entry as a top-level appendix section.

#222 encodes those two source shapes as RED tests and tightens only top-level appendix-section recognition: a top-level appendix locator requires heading-style uppercase title evidence. Deeper appendix subsection recognition is deliberately unchanged because its remaining failure family is different.

The correction does not special-case `C1`, weaken locator uniqueness, or assign equation or bibliography semantics.

## Current exact whole-document replay

A fresh replay against the exact 60-page artifact after the heading correction produced:

- 1,164 retained PDF block observations supplied to the adapter;
- 1,110 Document AST nodes;
- 21 `section` nodes;
- 110 `subsection` nodes;
- 917 `paragraph` nodes;
- 17 `table` nodes;
- 11 `table_heading` nodes;
- 24 `equation` nodes;
- 9 `figure` nodes;
- 1 `document` node;
- 6 `ashrae621-repeated-table-structure-deferred` diagnostics.

The resulting AST passes generic `validate_document_ast` validation across all 60 physical pages.

This validator pass is not a structural-completeness claim.

## Measured remaining compound-block gap

Exact span-level inspection finds four PDF text blocks containing more than one bold appendix locator span. Across those four blocks there are 12 bold structural locator spans, so eight locator-bearing headings occur beyond each block's first heading and are not independently represented by the current block-level adapter.

This is now the next measured structural gap. It is separate from the resolved top-level `C1` false-positive family and should not be hidden merely because the current whole-document AST satisfies generic invariants.

## Support boundary after replay

The evidence establishes:

- exact retained artifact identity verified;
- deterministic exact-source replay across all 60 physical pages;
- generic Document AST validation passes on the current whole-document projection;
- publication-native appendix role and hierarchy are preserved where block-level recognition supports them;
- repeated table observations remain explicit without duplicate locators or semantic overclaiming;
- top-level appendix headings are disambiguated from the measured displayed-math and bibliography false-positive shapes;
- remaining structural loss is explicitly measured rather than normalized away.

It does **not** establish:

- whole-document structural completeness;
- complete compound-block heading segmentation;
- semantic multi-page table continuation;
- table body/header/cell reconstruction or lookup meaning;
- mathematical semantics;
- reference resolution;
- reviewed provision semantics;
- project applicability or compliance behavior.

## Next executable evidence

The next ASHRAE 62.1 structural gate is compound-block heading segmentation: four exact-source blocks contain 12 bold locator spans with eight headings beyond the first currently unrepresented. Inspect existing shared visual-line, glyph, font, and structural-metadata infrastructure before adding publication-specific splitting. Prefer a shared layout correction only if cross-publication evidence supports the abstraction.
