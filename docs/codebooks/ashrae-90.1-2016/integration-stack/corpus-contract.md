# ASHRAE 90.1-2016 whole-publication structural measurement

Canonical roadmap: issue #219.

This gate measures the current ASHRAE 90.1-2016 observation adapter against the exact retained artifact. It does not add recognition behavior and does not claim structural, semantic, reviewed, or engineering completeness.

## Exact retained artifact

- private retained file: `ashrae-90_1-2016.pdf`
- size: 3,475,675 bytes
- SHA-256: `275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162`
- physical pages: 388
- native PDF outline entries: 720
- media type: `application/pdf`

The exact retained bytes were independently rehashed before this report was recorded. No protected source text, page image, reconstructive table, equation corpus, figure, or generated private AST is committed.

## Measurement contract

`src/building_code_ast/ashrae901_2016_corpus.py` reuses the current publication adapter's content bounds, source ordering, text normalization, and recognition predicates. It compares source-safe locator/page observations to the PDF's native outline only as a measurement oracle.

The outline is not parser input and is not promoted to canonical AST authority. A match to an outline locator is evidence about current recognition behavior, not proof that the recognized source block is structurally correct. A non-match is likewise a discrepancy to investigate, not permission to manufacture a node.

The measurement fails closed unless SHA-256, byte size, and 388-page identity all match the exact retained artifact.

## Exact-source whole-document replay

The current adapter's content-region filter retains 8,897 source blocks across the exact artifact.

Current block recognition classifies them as:

- paragraphs: 8,030
- subsections: 670
- sections: 135
- tables: 39
- figures: 15
- appendices: 8
- equations: 0

These counts describe current recognizer behavior. A recognized table or figure caption is not evidence that table cells, figure semantics, or engineering meaning are supported.

## Numeric hierarchy denominator

The native outline contains 456 unique numeric body locators.

Current numeric-heading recognition produces:

- numeric candidate occurrences: 805
- unique candidate locators: 486
- duplicate candidate occurrences beyond the first occurrence: 319
- unique candidate locators also present in the outline: 389
- outline locators with no current candidate: 67
- candidate locators absent from the outline: 97

Among the 389 overlapping unique locators:

- 370 have at least one observation on the exact outline page;
- 1 has no exact-page observation but has an observation within one physical page;
- 18 have observations only farther from the outline page.

These are source-safe locator/page comparisons. They are not reviewed correctness counts.

## Whole-document identity blocker

The first deterministic duplicate produced by current recognition is `section:1`:

- first recognized occurrence: physical PDF page 7;
- repeated recognized occurrence: physical PDF page 8;
- native outline anchor for the publication's Section 1: physical PDF page 9.

The generic Document AST requires globally unique locators. Current whole-document recognition therefore cannot produce a validatable ASHRAE 90.1-2016 Document AST without first correcting heading recognition. The measurement reports this explicitly as `duplicate_document_locator`; it does not discard or rename the conflicting observations.

Private source review of this counterexample class shows that the current top-level numeric-heading text pattern is not a safe discriminator for this publication. The successor must use source-backed typography/layout evidence rather than merely broadening or narrowing the numeric regex, and it must not use the PDF outline as runtime parser truth.

## Appendix hierarchy gap

The exact outline contains:

- 8 top-level appendix headings;
- 251 appendix-native sublocators.

The current adapter recognizes all 8 top-level appendix headings but has no grammar for appendix-native sublocators, so the current appendix-sublocator candidate count is 0.

This is a separate measured structural gap from the numeric-body duplicate-locator blocker. It should not be silently filled by treating appendix material as ordinary numbered body sections.

## TDD evidence

Initial RED head: `b1d234fe6ad74e6dbf6b47a085123fb7756c8239`.

Hosted CI ran 555 tests and failed exactly because `building_code_ast.ashrae901_2016_corpus` did not yet exist; every inherited test passed.

Initial implementation head: `f7699a64b6468fdc9b5ba051dba790a56cd9b108`.

That run exposed one synthetic-oracle mistake: the test classified an observation one page from its outline anchor as far-only. The measurement correctly classified it as a near-page match. The test was corrected rather than weakening the measurement.

Corrected GREEN head before this report: `2647f8daa6a4eda75beef3e8f5d7acf1c8ccc985`.

Fresh hosted checks on that head:

- CI: success
- LORE: success
- Deciduous archaeology: success

## Boundaries and next executable work

This PR owns measurement only. It does not change `ashrae901_2016.py`, alter Document AST identity, promote outline data into parser input, interpret energy requirements, reconstruct table semantics, or resolve appendix meaning.

The first executable successor justified by this replay is publication-specific numeric-heading disambiguation using exact-source layout/typography evidence. Its acceptance gate should reduce the measured duplicate/unexpected numeric candidates while recovering real outline-backed body locators, with whole-document validation rerun afterward.

Appendix-native sublocator recognition is a distinct later gate backed by the measured 251-to-0 gap.
