# ACI 318-19 source profile

Status: exact retained artifact characterized sufficiently to begin source-role-aware Document AST work; document-AST implementation has not started.

## Exact retained artifact

- retained filename: `aci-318-2019.pdf`
- size: 10,010,981 bytes
- media type: `application/pdf`
- SHA-256: `7b6b572e9e6532e0da1678080f63cb6b7a233f96caf2fc5a45350a056e18c53c`
- PDF pages: 628
- PDF version: 1.6
- page size: A4, 595.22 x 842 PDF points
- encryption: none
- PDF tagging: none
- JavaScript: none
- embedded attachments: none observed
- storage: outside Git

The digest identifies the exact retained bytes. Another file with the same title, edition, or nominal ACI designation is not interchangeable with this artifact.

PDF metadata identifies Adobe InDesign 14.0 with Foxit Advanced PDF Editor in the creator field and 3-Heights PDF Producer 4.4.43.1 in the producer field. The PDF metadata timestamps are 2019-05-24 for creation and 2019-06-21 for modification. These are artifact observations, not publication-state semantics.

The retained PDF is unencrypted and ordinary text extraction is permitted. No global OCR prerequisite was found.

## Publication identity, printing, corrections, and rights

The retained publication self-identifies as the Inch-Pound Units edition containing coordinated ACI 318-19 code requirements and ACI 318R-19 commentary.

Source-backed publication facts include:

- designation: `ACI 318-19` with coordinated `ACI 318R-19` commentary;
- issuing body: American Concrete Institute;
- adoption date stated in the publication: 2019-05-03;
- publication month stated in the publication: June 2019;
- printing stated in the publication: first printing, June 2019;
- copyright year: 2019;
- ISBN: `978-1-64195-056-5`;
- DOI: `10.14359/51716937`.

The retained publication directs users to ACI for errata, but the exact bytes do not establish a complete incorporated-corrections identity. Treat this artifact as a verified first-printing source whose correction/errata state remains unresolved. Do not silently apply current web errata or infer incorporated corrections from PDF modification timestamps.

Rights/access classification: copyrighted, restricted private source retained outside Git. Exact bytes, reconstructive prose, commentary, equations, tables, figures, page images, and source-reconstructive generated AST corpora remain outside public Git.

A future `SourceRegisterEntry` should use the shared source-registration contract rather than inventing an ACI-specific registry. The artifact digest, edition, first-printing evidence, unresolved correction state, access scope, and rights state must remain explicit.

## PDF pages and printed-page coordinates

PDF ordinal page number and visible printed page number are distinct coordinates.

The PDF native page-label metadata is not a printed-page oracle: it exposes ordinary PDF ordinals rather than the visible publication page labels. Printed-page identity therefore has to be observed from page content.

Observed mapping across the numbered publication body is a constant offset of two pages:

- PDF page 5 -> printed page 3;
- PDF page 6 -> printed page 4;
- PDF page 11 -> printed page 9;
- PDF page 53 -> printed page 51;
- PDF page 624 -> printed page 622;
- PDF page 625 -> printed page 623.

Thus the verified numbered body represented by those checkpoints uses `printed_page = pdf_page - 2`. PDF pages 626-628 are post-body promotional/blank/back-cover material and are not part of that numbered sequence. Retain those pages as artifact evidence rather than compressing the PDF coordinate space.

Document AST nodes should use publication-native structural locators as durable identity where available and retain PDF page, printed page, bounding box, text span, and extraction block as provenance.

## Navigation and table of contents

The PDF contains 247 outline/bookmark destinations. The outline includes front matter, chapters, and many top-level numbered sections. It is useful navigation evidence but is not a complete subsection/provision oracle.

The publication table of contents identifies Parts, chapters, and top-level section entries. It is useful for hierarchy cross-checking but should not replace page/layout evidence for lower-level structural recognition.

Bookmarks and table-of-contents entries are therefore corroborating structural evidence, not authoritative substitutes for the source page.

## Text layer, reading order, and OCR

A native selectable text layer is present across essentially the entire publication. Whole-document text extraction found nonempty native text on 626 of 628 PDF pages; PDF pages 2 and 627 are text-empty and behave as blank/separator leaves rather than evidence of scanned prose.

Global OCR is not required for coverage and should not be added preemptively. If a later equation, figure, table, or isolated glyph region demonstrates a real OCR need, OCR must remain local, explicit, and provenance-marked.

Native text extraction is not semantically faithful by itself. The code and commentary commonly occupy parallel columns, so line-oriented extraction can place normative code text and commentary text on the same extracted line. Some embedded-font glyphs also decode imperfectly in ordinary text extraction.

Consequently:

- extraction sequence is not publication reading order;
- geometry-aware region segmentation is required before source-role assignment;
- mathematical and special-symbol text requires glyph/layout diagnostics;
- plausible-looking extracted text must not be promoted directly into engineering semantics.

## Normative code and commentary boundary

The retained artifact establishes an explicit source-role boundary suitable for deterministic structural parsing.

The publication introduction describes ACI 318-19 Code and ACI 318R-19 Commentary as separate but coordinated material. Ordinary body pages visibly present a `CODE` column and a `COMMENTARY` column side by side. The code column uses ordinary numeric provision locators, while corresponding commentary locators use an `R` prefix, for example the commentary counterpart to a numeric code locator is visibly distinguished by the prefixed role-specific locator.

This supports the compiler-level distinction:

```text
source role: normative code
source role: commentary
```

The distinction must be established from layout and publication markers, not inferred from modal verbs, prose tone, or extraction order.

A robust first recognizer should combine at least:

- page-region geometry;
- visible role headers where present;
- role-specific locator forms;
- publication hierarchy context.

No one signal should silently override conflicting evidence. A region that cannot be assigned confidently to code or commentary must remain ambiguous/unsupported.

Commentary is explanatory evidence, not governing code text. It must not become a child prose continuation of a normative provision merely because the two regions are adjacent on the page.

## Code/commentary correspondence

The `R`-prefixed commentary locator convention provides strong source evidence for many correspondences, and the parallel layout often places related code and commentary material beside each other.

That is not sufficient to justify a universal string-similarity join. The source visibly permits code provisions with no same-row commentary text, and commentary may span material differently from the code column.

Initial correspondence should therefore be represented as a source-backed relationship only when publication evidence supports the pairing. Preserve unresolved correspondence when commentary is absent, broader, narrower, continued, or otherwise ambiguous.

Normative and commentary nodes that share an analogous numeric designation must still have distinct deterministic IDs because source role is part of identity.

## Publication hierarchy

The retained artifact uses a publication-native hierarchy built from Parts, numbered chapters, decimal sections, and nested decimal provisions/subprovisions. The outline and table of contents provide chapter/top-level-section corroboration; page content supplies the lower-level hierarchy.

Representative body pages show nested numeric code locators such as chapter-level sections and deeper decimal provision locators, with corresponding commentary using the same numeric stem under an `R`-prefixed role-specific locator when commentary exists.

Chapter-level organization around design, construction, inspection, documentation, member types, analysis, and other responsibility-related subjects is publication structure. It must not be converted into project-specific professional or contractual responsibility assignments by the compiler.

## Definitions, notation, and terminology

Chapter 2 separates notation from terminology. That is an important structural distinction for later semantic work:

- mathematical symbols and notation require explicit scope;
- prose terminology requires definition identity and context;
- commentary explanations must not silently replace normative definitions.

Do not build a single glyph-to-meaning or term-to-definition dictionary before scope is established. Symbol definitions may be local to an equation, section, chapter, or source role.

## References

The source contains distinct reference phenomena that should remain separate in Document AST relationships:

- normative code -> normative code provision;
- normative code -> equation;
- normative code -> table;
- normative code -> figure or other source structure;
- commentary -> normative code;
- commentary -> commentary;
- either source role -> external standard;
- unresolved reference.

Chapter 3 provides referenced-standard structure, while internal references also occur throughout numbered provisions and commentary. References should preserve their exact source span, originating source role, target identity when resolved, and unresolved state when not resolved.

## Equations

Displayed equations are first-class ACI source structures. The retained source contains equations with publication-native parenthetical designations, including letter-suffixed equation identifiers, and commentary may discuss or contain mathematical material alongside normative equations.

Equation handling must keep separate:

1. equation region;
2. equation designation;
3. mathematical expression reconstruction;
4. symbol tokens and definitions;
5. units;
6. applicability/context;
7. source role;
8. engineering semantics;
9. executable calculation.

The first Document AST descendant only needs honest equation-region/designation structure and exact provenance. Imperfect glyph extraction or ambiguous multi-line grouping should produce diagnostics rather than a manufactured executable formula.

A commentary equation or derivation remains commentary even when it resembles or discusses a normative equation.

## Tables and table notes

Numbered tables occur throughout the retained source and may sit in the normative code column while commentary discusses the same subject in the parallel column. Table extraction must therefore preserve source role before any lookup semantics are inferred.

Keep separate:

```text
table region
  -> cell geometry
  -> headers and spanning cells
  -> units and notes/footnotes
  -> reviewed semantic dimensions
  -> optional lookup behavior
```

A rectangular text extraction is not evidence that header hierarchy, spanning cells, units, or footnote ownership has been reconstructed correctly. Continued tables and source-role boundaries should remain explicit or diagnosed.

## Figures and graphical material

The retained source contains commentary figures with role-specific `R` locators and graphical material that cannot be reduced safely to nearby caption text. A figure must preserve its source role, publication locator, parent context, source region, and references.

Graphical semantics such as arrows, labels, dimensions, linework, or illustrated behavior are not inferred from caption text alone. Commentary figures remain commentary evidence rather than normative requirements.

## Appendices and index

The retained artifact contains lettered appendices after the numbered chapters. Appendix pages continue the coordinated code/commentary presentation, including role-specific commentary locators such as `RA...` where corresponding commentary exists.

Appendix status must remain source-backed. Do not infer normativity or informativeness merely from appendix placement.

The publication concludes with an index extending through visible printed page 623, followed by artifact pages outside the numbered body. Index entries are useful cross-check evidence but are not structural nodes merely because they mention a locator.

## Representative parser hazards and unsupported structures

The first ACI Document AST work should explicitly preserve or diagnose at least these conditions:

- mixed normative/commentary pages with parallel columns;
- raw text lines that coalesce material from both source roles;
- code provisions that have no adjacent commentary text;
- commentary correspondence that is broader, continued, or otherwise nontrivial;
- equations with multi-line mathematical layout and imperfect special-glyph extraction;
- tables with spanning headers, units, notes, footnotes, or continuation behavior;
- graphical figures whose engineering meaning is not present in text order;
- role-specific appendix locators;
- page furniture and index material that resemble structural references;
- unnumbered and post-body artifact pages;
- any offset block whose role cannot be established from publication evidence.

Unsupported and ambiguous regions are useful compiler output. They must not be flattened into prose or assigned a source role merely to reduce diagnostics.

## Source registration boundary

These characterization facts are enough to bind future private verification to the exact artifact digest, but this profile does not create a public reconstructive source register or corpus.

The shared source-register schema separately models exact artifact identity, publication state, evidence role, access scope, and rights status. Because this single retained PDF contains both normative code and commentary, later registration/ingestion must not let one file-level evidence-role label erase the node-level source-role distinction required by the Document AST. Resolve that modeling boundary in the smallest shared contract justified by the first structural implementation rather than creating an ACI-only competing registry.

Correction state remains explicitly unresolved. A cleaner, corrected, or later-distributed ACI 318-19 PDF would require a separate exact artifact identity and an explicit adoption decision.

## Document-AST gate

Exact-source characterization is complete enough to begin the first source-backed ACI 318-19 Document AST descendant after this profile is integrated.

That descendant should demonstrate a compact but meaningful slice containing:

- publication-native chapter/section/provision hierarchy;
- explicit normative-code and commentary source roles;
- distinct source-role-aware deterministic IDs;
- exact PDF page, printed page, bounding-box, and text-span provenance;
- a source-backed code/commentary correspondence relationship;
- at least one non-prose structure such as an equation or table;
- explicit unsupported/ambiguous handling;
- generic Document AST validation;
- deterministic repeated-run behavior;
- private replay against SHA-256 `7b6b572e9e6532e0da1678080f63cb6b7a233f96caf2fc5a45350a056e18c53c`.

Do not begin Provision AST semantics until those structural relationships are trustworthy.

This profile does not add schemas, runtime models, parser adapters, extracted corpus material, semantic interpretation, executable reinforced-concrete calculations, project responsibility assignments, or compliance conclusions.

No protected source prose, commentary, equations, tables, figures, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-aci-318-19-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-aci318-19-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/aci-318-19/source-profile.md`
- requires: `action.establish-aci318-19-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available. Do not hand-edit generated Deciduous projections.