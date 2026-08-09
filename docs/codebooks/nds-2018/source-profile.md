# NDS 2018 source profile

Status: exact retained artifact characterized; document-AST implementation has not started.

## Exact retained artifact

- retained filename: `nds-2018.pdf`
- size: 6,791,825 bytes
- media type: `application/pdf`
- SHA-256: `581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4`
- PDF pages: 206
- PDF version: 1.7
- encryption: none
- page geometry: 612 × 783 PDF points throughout the document
- storage: outside Git

The digest identifies the exact retained bytes. Filename, title, edition, and page count are not substitutes for artifact identity.

The file is parseable by PyMuPDF across all 206 pages. Poppler reports a damaged cross-reference entry and reconstructs the xref while opening the file. Characterization therefore uses the retained bytes as-is; a repaired or rewritten PDF would be a different artifact and require a new digest.

PDF metadata identifies `ToolBox 6.3.0` as creator and `A-PDF Watermark 4.7.6` as producer. A repeated third-party watermark is also present in page content. These are artifact-copy provenance, not NDS publication content. Metadata creation and modification dates are not used as publication dates.

## Publication identity and rights

The retained artifact self-identifies as:

- publication family: National Design Specification for Wood Construction
- designation: `ANSI/AWC NDS-2018`
- edition: 2018
- issuing body: American Wood Council
- approval date: 2017-11-16
- digital publication state: First Web Version, November 2017
- ISBN: `978-1-940383-42-2`

A printing identity is not stated in the retained artifact. The artifact identifies itself as a web version, so no print-run identity is inferred.

The source contains an updates-and-errata notice, but it does not identify which correction or errata set, if any, is incorporated in these exact bytes. Correction/addenda state therefore remains unresolved. The PDF modification timestamp does not establish a publication correction state.

Rights/access classification: copyrighted, license-restricted private source. Exact bytes, page images, reconstructive text, tables, figures, and generated source-reconstructive ASTs remain outside public Git.

No separate commentary layer was observed. Source roles are nevertheless not uniform: front matter and foreword, numbered chapters, non-mandatory appendices A-M, mandatory Appendix N, references, and trailing publisher matter must remain distinguishable.

## Coordinates and printed pages

The shared PDF layout coordinate model is applicable to the artifact:

- PDF pages are one-based;
- bounding boxes use PDF points in `(x0, y0, x1, y1)` order;
- every page is 612 × 783 points;
- the PDF contains no native page-label dictionary.

Observed printed-page mapping:

- PDF pages 1-3: unnumbered cover/update/title matter;
- PDF pages 4-12: printed front-matter labels `ii` through `x`;
- PDF pages 13-204: printed pages `1` through `192`, with `printed_page = pdf_page - 12`;
- PDF pages 205-206: unnumbered trailing matter.

Retain both PDF page and printed-page label as provenance. Where NDS supplies a publication-native chapter, section, appendix, table, figure, or equation locator, that locator should drive structural navigation and identity rather than incidental PDF pagination.

## Navigation, text layer, and reading order

The retained PDF exposes 105 outline entries across three bookmark levels. The outline covers front matter, all 16 numbered chapters, top-level chapter sections, appendices, and references. It is useful navigation evidence but not a complete structural oracle: the bookmark for `12.6 Multiple Fasteners` has no valid page target.

A selectable text layer is present on every PDF page; no page produced zero extracted words in whole-document inspection. OCR is therefore not required for page coverage at this stage. If a later parser demonstrates a region-specific OCR need, OCR use must remain explicit and separately provenance-marked.

Text extraction is not equivalent to faithful mathematical extraction. Equation-heavy pages contain private-use Unicode glyphs from the embedded font encoding. Equation recognition must therefore retain layout/glyph evidence and must not promote flattened extracted text directly into an executable mathematical representation.

The main body is predominantly two-column. Chapter and appendix openers, front matter, displayed equations, figures, and dense or continued tables use layouts that cannot safely be reduced to a single flat text order. NDS structural recognition should consume coordinate-aware page/block evidence and use region-aware reading order.

## Publication grammar observed

The characterization is sufficient to define the first structural parser boundary without claiming whole-document structural support.

- Numbered body: 16 chapters.
- Hierarchy: chapter and decimal section addresses, including nested forms through at least four numeric levels.
- Chapter openers: visually distinct opener pages summarize chapter-local structure before ordinary body pages.
- Appendices: A through N; A-M are identified as non-mandatory and N as mandatory. Appendix-local section addresses use letter-qualified locators such as `D.1`.
- Equations: displayed equations use publication-native identifiers, including body forms such as `(3.3-1)` and appendix forms such as `(D-1)`. Recognition, glyph representation, mathematical parsing, and engineering meaning remain separate concerns.
- Tables: both section-derived and alphanumeric table locators occur. Dense and continued tables, units, multi-level headers, and table footnotes require geometry-aware structural treatment. Rectangular extraction does not establish table semantics.
- Figures: publication-native figure locators and technical graphics occur. Figure boundary/caption/reference recognition does not establish graphical engineering meaning.
- Footnotes: table-associated footnotes and notes occur and must remain attached to the relevant structural region rather than flattened into adjacent prose.
- Definitions: definitions are distributed within subject chapters rather than confined to one global definition section. Both numbered definition entries and prose definition forms occur, so scope must be evidence-backed and context-sensitive.
- Cross-references: internal section references, table references, figure references, appendix references, bibliography/reference-list citations, and external standards designations are distinct reference families. Numeric-looking citations must not be assumed to be internal section targets.

No whole-document count of tables, figures, equations, definitions, footnotes, or cross-references is claimed by this profile. Those denominators belong to the structural-measurement descendant.

## Representative parser hazards

The first NDS Document AST work should explicitly preserve or diagnose at least these source conditions:

- damaged PDF xref data that readers repair while opening;
- a useful but imperfect bookmark tree, including one unresolved bookmark target;
- repeated artifact-local third-party watermark content that must not enter publication structure;
- two-column pages mixed with full-width and region-specific layouts;
- mathematical glyphs whose text extraction contains private-use Unicode characters;
- dense and multi-page/continued tables with footnotes;
- figures and technical graphics whose semantics are not represented by text extraction;
- distinct chapter/appendix opener layouts;
- source-role differences between normative chapters, non-mandatory appendices, mandatory Appendix N, front matter, references, and trailing matter.

Unsupported, uncertain, malformed, and ambiguous regions should remain visible diagnostics rather than being coerced into apparently supported structure.

## Source registration

This profile does not add an NDS-only source registry. The eventual NDS source registration should use the repository's existing source-registration contract to distinguish publication state, exact artifact digest, access/rights state, and the `DocumentSourceArtifact` identity consumed by Document AST.

The exact-byte digest is part of that evidence boundary. Unknown printing and correction state must remain explicit unknowns rather than being filled from another nominally identical NDS 2018 copy.

## Document-AST gate

Exact-source characterization is complete enough to begin a first source-backed NDS Document AST descendant after this profile is integrated.

That descendant should:

- bind to the exact retained artifact identity above;
- declare PDF/printed-page/coordinate spaces explicitly;
- derive deterministic structural identities from publication-native locators where available;
- use representative synthetic/source-safe fixtures plus private exact-source replay;
- pass generic Document AST validation;
- preserve unsupported structures as diagnostics;
- measure whole-document structure before making completeness claims.

The source profile does not add schemas, runtime models, parser adapters, extracted corpus material, or semantic interpretation.

No protected source prose, tables, figures, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-nds-2018-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-nds2018-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/nds-2018/source-profile.md`
- requires: `action.establish-nds2018-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.
