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

#222 encoded those two source shapes as RED tests and tightened only top-level appendix-section recognition: a top-level appendix locator requires heading-style uppercase title evidence. Deeper appendix subsection recognition remained deliberately unchanged.

After #222, the 60-page block-level projection contained 1,110 AST nodes, including 110 subsections, and passed generic validation. That validator pass did not establish structural completeness.

## Compound-block line/span evidence

Exact span-level inspection then found four PDF text blocks containing multiple real bold appendix locator-bearing heading lines:

- 4 compound blocks;
- 12 true bold locator-bearing headings;
- only 3 represented by the block-level adapter;
- therefore **9 missing headings** before finer-grained recovery;
- 1 of the 4 blocks begins with continuation prose before its first heading.

The earlier count of eight missing headings was an undercount because it assumed each compound block contributed one already-recognized heading. The prefix-prose block contributed none.

For all four exact blocks, normalized legacy block text equals normalized reconstruction from PyMuPDF visual-line/span text. This establishes a lossless source-evidence seam rather than permission to replace source text heuristically.

#223 adds optional publication-neutral `PdfLine` / `PdfSpan` evidence while preserving legacy `PdfBlock.text` and legacy serialization when no line evidence exists. The generic PDF layer records geometry and font observations only; it does not decide what constitutes a heading.

ASHRAE 62.1 is the first consumer. It splits only blocks with at least two bold appendix-heading candidates and only when line reconstruction is text-lossless. Prefix prose and between-heading body text remain explicit observations.

## Current exact whole-document replay

A fresh replay against the exact retained artifact with the #223 implementation produced:

- 1,164 extracted PDF block observations before publication-specific splitting;
- 1,110 retained block-level observations before splitting;
- normalized AST source text exactly equal to the normalized pre-split retained source text;
- 1,119 Document AST nodes;
- 21 `section` nodes;
- 119 `subsection` nodes;
- 917 `paragraph` nodes;
- 17 `table` nodes;
- 11 `table_heading` nodes;
- 24 `equation` nodes;
- 9 `figure` nodes;
- 1 `document` node;
- 6 `ashrae621-repeated-table-structure-deferred` diagnostics.

All nine headings missing from the measured four-block compound family are now represented. The resulting AST passes generic `validate_document_ast` validation across all 60 physical pages.

The six repeated-table diagnostics are unchanged, confirming that this structural correction did not silently promote deferred table semantics.

## Next measured counterexample

Whole-artifact bold-locator-line comparison after the compound-block recovery finds one remaining source-backed appendix heading identity not represented in the AST:

`A1.2.2`

Its source shape is different from the #223 compound family:

- one bold locator-bearing heading line in its PDF block;
- two prefix lines before that heading;
- 11 total visual lines in the block;
- line/span reconstruction is text-lossless.

Because there is only one heading candidate in that block, #223 intentionally does not split it. This is the next executable structural evidence gate rather than a reason to broaden the compound-block PR after its measured nine-heading target is satisfied.

## Support boundary after replay

The evidence establishes:

- exact retained artifact identity verified;
- deterministic exact-source replay across all 60 physical pages;
- generic Document AST validation passes on the current whole-document projection;
- optional shared line/span evidence preserves legacy PDF block text;
- all nine headings from the measured four-block compound family are recovered;
- prefix prose in the compound family is retained rather than swallowed;
- repeated table observations remain explicit without semantic overclaiming;
- remaining structural loss is explicitly measured rather than normalized away.

It does **not** establish:

- whole-document structural completeness;
- recovery of the measured single embedded `A1.2.2` heading;
- semantic multi-page table continuation;
- table body/header/cell reconstruction or lookup meaning;
- mathematical semantics;
- reference resolution;
- reviewed provision semantics;
- project applicability or compliance behavior.

## Next executable evidence

After #223 lands, investigate the single embedded-heading family represented by `A1.2.2`: a text-lossless block with prefix prose and one bold appendix heading candidate. Reuse the same shared line/span evidence, but encode the source-backed distinction from ordinary bold inline text before broadening the ASHRAE splitter. Do not infer that every single bold locator-like line is structural without a measured negative corpus.
