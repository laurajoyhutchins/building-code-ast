# ASHRAE 62.1-2016 Document AST replay evidence

Status: bounded exact-source foundation replay complete; whole-document structural support is not claimed.

## Exact retained artifact

The replay used the exact retained private artifact characterized by the source profile:

- filename: `ashrae-62_1-2016.pdf`
- SHA-256: `a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759`
- size: 1,193,586 bytes
- physical pages: 60

The bytes were hashed before replay. No source prose, page image, reconstructive table, extracted corpus, or generated private AST is committed here.

## Evidence-driven corrections

Private inspection of the exact artifact exposed source-backed defects in the first synthetic-only implementation:

1. The shared `PublicationIdentity` contract has no separate `addenda_set` field. The exact incorporated addenda identity and unresolved correction-layer state are therefore preserved together in the supported publication-state field rather than widening the shared model without a demonstrated generic requirement.
2. Real appendix source structure occurs outside the generic 65-to-730 point body band. The ASHRAE 62.1 adapter now uses source-specific retained bounds sufficient to include the observed appendix headings and lower-page source structures.
3. Appendix-native hierarchy uses locators such as `A1` and deeper descendants. The adapter now preserves those locators beneath their owning appendix.
4. Parenthesized numeric endings occur in ordinary source blocks and are not sufficient evidence of an equation. Unhinted equation recognition now requires equation-like syntax plus a publication-native trailing identifier.
5. Top-level Section recognition is restricted to the publication's Sections 1 through 9 and source-heading evidence, reducing promotion of numbered non-heading material.

These defects were first encoded as failing tests at RED head `d1dfddab7df401c7d61c3524c05f32d32eac3d27`. The corrected bounded-foundation implementation is head `974e23f640061fb29cfea9ec2e167443f5a08fa4` and landed through #181.

## Bounded exact-source replay

The corrected implementation was replayed directly against selected regions of the exact artifact using the repository PDF block extractor, the ASHRAE 62.1 observation adapter, and the generic Document AST validator.

Source-safe aggregate results:

| Exact PDF slice | Result | Nodes | Source-safe type counts |
| --- | --- | ---: | --- |
| page 26 | pass | 15 | document 1; section 1; subsection 4; paragraph 6; equation 2; figure 1 |
| pages 13-14 | pass | 31 | document 1; section 1; subsection 8; paragraph 14; equation 7 |
| pages 29-30 | pass | 46 | document 1; section 1; subsection 5; paragraph 32; table 3; equation 3; figure 1 |

Each bounded replay passed generic `validate_document_ast` validation. The page-26 replay exercised normative Appendix A source role, appendix-native hierarchy, equations, a figure, and printed-page provenance. The pages-29-30 replay exercised normative Appendix B hierarchy, tables, equations, a figure, and printed-page provenance. These are structural claims only.

## Initial whole-document stress result

The first 60-page replay intentionally failed closed on a repeated native table locator:

`duplicate document locator: table:6.2.2.1`

This was not treated as a parser success or silently normalized away. Whole-artifact source-safe observation found 28 table-caption blocks representing 17 native table identifiers. Six identifiers repeat, accounting for 17 observations across those repeated groups:

- four repeated groups occupy adjacent physical pages;
- two repeated groups contain more than one observation on the same physical page;
- 11 observations are therefore additional occurrences beyond the six primary native identifiers.

The same-page cases matter: repeated native identity alone is not sufficient evidence that every repeated extraction block is a semantic continuation.

## Shared repeated-locator replay progression

PR #220 introduces a publication-neutral occurrence classifier that groups observations by native locator and deterministic source order while keeping these source shapes distinct:

- single occurrence;
- adjacent-page repetition;
- same-page duplicate observation;
- discontiguous-page repetition.

The ASHRAE adapter uses this classification only to preserve identity without collision. The first occurrence retains the native `table:<locator>` identity. Additional observations remain explicit page-scoped `TABLE_HEADING` nodes with the same native locator recorded as metadata. The adapter emits a deferred-structure diagnostic and does not claim table-body, lookup, or continuation semantics from repetition alone.

Replaying the exact 60-page artifact with that implementation advances past every repeated table-locator collision. The next fail-closed validator result is:

`duplicate document locator: section:C1`

Private coordinate review shows two `C1` heading candidates on the same physical page with different geometry and text-layer shape. That is now the next independent structural ambiguity. It must be resolved from heading/layout evidence rather than by weakening global locator uniqueness.

This progression is the intended whole-document measurement behavior: fix one proven structural family, rerun, and expose the next real counterexample.

## Additional measured boundary

The replay also shows compound PDF text blocks in which multiple nested subsection headings can share one extraction block. The current adapter can preserve meaningful bounded hierarchy, but whole-document structural completeness requires measured handling of those compound blocks rather than claiming one-heading-per-block behavior.

## Support boundary after replay

The evidence establishes:

- exact retained artifact identity verified;
- real-source structural slices replay deterministically;
- generic validation passes on representative mandatory body and normative appendix slices;
- publication-native appendix hierarchy and non-prose identity are exercised;
- source-role and coordinate provenance are retained;
- repeated table observations can be preserved without duplicate AST locators or semantic overclaiming;
- unsupported whole-document behavior remains visible.

It does **not** establish:

- whole-document structural completeness;
- semantic multi-page table continuation;
- table body/header/cell reconstruction;
- complete compound-block heading segmentation;
- resolution of the duplicate `C1` heading candidate family;
- table lookup semantics;
- mathematical semantics;
- reference resolution;
- reviewed provision semantics;
- project applicability or compliance behavior.

## Next executable evidence

After the repeated-table occurrence work lands, the next ASHRAE structural gate is the measured duplicate `C1` / compound-heading family. Inspect its geometry and neighboring heading evidence and prefer a shared heading-segmentation rule only if cross-publication evidence supports one. Do not weaken locator uniqueness or add publication semantics merely to make the whole-document run green.
