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

These defects were first encoded as failing tests at RED head `d1dfddab7df401c7d61c3524c05f32d32eac3d27`. The corrected implementation is head `974e23f640061fb29cfea9ec2e167443f5a08fa4`.

## Bounded exact-source replay

The corrected implementation was replayed directly against selected regions of the exact artifact using the repository PDF block extractor, the ASHRAE 62.1 observation adapter, and the generic Document AST validator.

Source-safe aggregate results:

| Exact PDF slice | Result | Nodes | Source-safe type counts |
| --- | --- | ---: | --- |
| page 26 | pass | 15 | document 1; section 1; subsection 4; paragraph 6; equation 2; figure 1 |
| pages 13-14 | pass | 31 | document 1; section 1; subsection 8; paragraph 14; equation 7 |
| pages 29-30 | pass | 46 | document 1; section 1; subsection 5; paragraph 32; table 3; equation 3; figure 1 |

Each bounded replay passed generic `validate_document_ast` validation. The page-26 replay exercised normative Appendix A source role, appendix-native hierarchy, equations, a figure, and printed-page provenance. The pages-29-30 replay exercised normative Appendix B hierarchy, tables, equations, a figure, and printed-page provenance. These are structural claims only.

## Whole-document stress result

A 60-page replay was also attempted as a stress measurement. It intentionally failed closed on a repeated native table locator:

`duplicate document locator: table:6.2.2.1`

This is not treated as a parser success or silently normalized away. The exact source contains repeated table-caption observations associated with multi-page continuation structure. The current bounded foundation does not yet model continuation occurrences without colliding deterministic locators.

Additional whole-artifact source-safe observation found repeated table-caption identities beyond this first failing case, so fixing one literal locator would not constitute whole-document support.

The replay also showed compound PDF text blocks in which multiple nested subsection headings share one extraction block. The current adapter can preserve a meaningful bounded hierarchy, but whole-document structural completeness requires measured handling of those compound blocks rather than claiming one-heading-per-block behavior.

## Support boundary after replay

This evidence establishes the completion gate for the bounded Document AST foundation:

- exact retained artifact identity verified;
- real-source structural slices replayed deterministically;
- generic validation passed on representative mandatory body and normative appendix slices;
- publication-native appendix hierarchy and non-prose identity exercised;
- source-role and coordinate provenance retained;
- unsupported whole-document behavior remains visible.

It does **not** establish:

- whole-document structural completeness;
- complete multi-page table continuation support;
- complete compound-block heading segmentation;
- table cell or lookup semantics;
- mathematical semantics;
- reference resolution;
- reviewed provision semantics;
- project applicability or compliance behavior.

## Next executable evidence

The next ASHRAE 62.1 implementation should be selected from the measured whole-document failures. Before adding publication-specific continuation logic, inspect and reuse existing shared table-continuation / layout infrastructure where it can preserve the same exact-source evidence. Compound-block heading segmentation should likewise be treated as a shared layout problem when cross-publication evidence supports that abstraction.
