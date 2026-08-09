# ASCE 7-22 source profile

Status: exact retained artifact characterized; document-AST implementation has not started.

## Exact retained artifact

- retained filename: `asce-7-2022.pdf`
- size: 55,404,349 bytes
- media type: `application/pdf`
- SHA-256: `522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0`
- PDF pages: 1,047
- PDF version: 1.6
- encryption: none
- storage: outside Git

The digest identifies the exact retained bytes. Filename, title, edition, page count, and a nominally identical ASCE 7-22 copy are not substitutes for artifact identity.

The retained bytes are readable by PyMuPDF and Poppler. The first PDF page is artifact-local third-party promotional material rather than ASCE publication content. PDF metadata identifies `Adobe Acrobat Pro 10.1.6(Foxit Advanced PDF Editor)` as creator and `iLovePDF` as producer. These observations describe this retained copy and must not be promoted into publication semantics.

## Publication identity and rights

The retained publication self-identifies as:

- designation: `ASCE/SEI 7-22`
- title: *Minimum Design Loads and Associated Criteria for Buildings and Other Structures*
- issuing body: American Society of Civil Engineers
- copyright year: 2022
- Library of Congress Control Number: `2021951104`
- ISBN soft cover: `978-0-7844-1578-8`
- ISBN PDF: `978-0-7844-8349-7`

The publication states that errata, addenda, supplements, and interpretations may exist or become available through ASCE. The exact retained bytes do not state a complete incorporated-corrections identity. Correction/addenda state therefore remains unresolved rather than being inferred from metadata timestamps or a current external ASCE service.

A printer key is present in the retained publication, but this profile does not infer an exact printing identity from that key without a source-backed interpretation contract. Publication date is established here only to the stated 2022 publication year; an exact day is not stated in the retained artifact.

Rights/access classification: copyrighted, license-restricted private source. Exact bytes, reconstructive prose, equations, tables, figures, maps, page images, and source-reconstructive generated AST corpora remain outside public Git.

## Coordinates and printed pages

The shared PDF layout coordinate model is applicable:

- PDF pages are one-based;
- bounding boxes use PDF points in `(x0, y0, x1, y1)` order;
- PDF page and printed page are distinct coordinate spaces;
- publication-native section, equation, table, figure, appendix, and commentary locators should drive durable structural identity where available.

Most publication pages are 612 x 792 PDF points. The artifact-local first page is 540 x 780 points and must not be treated as a publication page merely because it is PDF page 1.

The PDF contains a native page-label dictionary, but it is not a trustworthy printed-page oracle for these retained bytes. For example, the dictionary labels PDF page 5 as `v`, while the visible printed footer is `iii`; the inserted artifact-local page and unnumbered publication leaves shift the relationship.

Observed printed-page mapping sufficient for parser work:

- PDF page 1: artifact-local nonpublication material;
- PDF pages 2-4: unnumbered cover/title/copyright matter;
- PDF pages 5-62: visible roman-numbered front matter `iii` through `lx`;
- PDF pages 63-542: provisions printed pages `1` through `480`, with visible page 1 at PDF page 63;
- PDF page 541 is printed provision page `479` and PDF page 542 is an intentionally blank printed page `480`;
- PDF page 543 is commentary title matter at printed page `481` and PDF page 544 is intentionally blank printed page `482`;
- PDF pages 545-1037: commentary printed pages `483` through `975`;
- PDF page 1038 is intentionally blank;
- PDF pages 1039-1047: index pages `Index-1` through `Index-9`.

The index itself states that provisions appear on printed pages 1-479 and commentary on printed pages 483-975. Retain the intervening intentionally blank/title pages as source evidence rather than compressing pagination.

## Navigation, text layer, and reading order

The retained PDF exposes no outline/bookmark entries. Navigation must therefore be reconstructed from source content and layout rather than trusted to a bookmark tree.

A selectable native text layer is present on all 1,047 PDF pages; whole-document inspection found no text-empty page. Global OCR is not required for page coverage. OCR, if later needed for a bounded equation, map, figure, or glyph region, must be explicit and separately provenance-marked.

Native text extraction is useful but not semantically faithful by itself. Two-column prose, displayed mathematics, tables, figures, maps, captions, legends, page furniture, and commentary layouts require coordinate-aware reconstruction. Extracted character order must not be treated as publication reading order without region evidence.

Poppler reports font/CMap warnings on this artifact, including invalid font-weight and `begincidrange` warnings. Mathematical and special-glyph extraction therefore requires layout/glyph diagnostics rather than promotion of plausible-looking text directly into mathematical semantics.

## Publication grammar observed

The characterization is sufficient to begin a first structural parser descendant without claiming whole-document structural support.

- Provisions: numbered Chapters 1 through 32; Chapter 25 is reserved for future provisions.
- Commentary: Chapters C1 through C32, explicitly identified as commentary and explicitly stated not to be part of the standard provisions. Commentary numbering contains intentional gaps where no commentary material exists.
- Provisions appendices: A through G, including reserved appendices and technical appendices.
- Commentary appendices: CA through CG, including reserved commentary appendices.
- Hierarchy: chapter, decimal section, and nested decimal subsection locators are visible throughout the provisions; commentary uses corresponding `C`-prefixed locators.
- Definitions: definitions occur in chapter-local definition sections and must remain scope-aware rather than being collapsed into one global dictionary.
- Symbols: chapter-local symbol lists occur and are distinct from prose definitions.
- Exceptions: explicit exception blocks occur beneath governing provisions and must remain attached to the structural provision they modify.
- References: internal section, chapter, equation, table, figure, appendix, commentary, and external-standard references are distinct reference families.
- Notes: notes occur in ordinary provisions and in table/figure/map contexts and require explicit ownership.

The front matter also states an important source-role distinction: Chapters 1-32 are the standard provisions and Chapters C1-C32 are commentary intended to help explain the provisions. Parser authority must preserve this role distinction instead of inferring normativity from modal verbs.

## Equations

Displayed equations are first-class ASCE source structures.

Observed conventions include publication-native identifiers such as `Equation 8.2-1` and metric counterparts such as `Equation 8.2-1.SI`. Equation references also occur inline in prose and symbol definitions.

Equation support must keep separate:

1. displayed-region detection;
2. identifier recognition;
3. multi-line grouping;
4. glyph/token reconstruction;
5. symbol resolution;
6. unit representation;
7. semantic interpretation;
8. executable calculation.

The retained source contains equation-heavy pages where text extraction fragments mathematical layout and special characters. Multi-line or geometrically fragmented expressions must remain one equation region when source geometry supports that grouping. Ambiguous grouping must emit an unsupported/ambiguous diagnostic rather than a manufactured formula.

## Tables

Tables carry normative engineering data and are not prose.

Observed source usage includes numbered table references such as `Table 4.3-1`, chapter-local tables, units in headers/cells, footnotes, and tables that interact with equations and applicability conditions. Geometry-aware table-region detection is therefore a separate capability from cell reconstruction and from semantic lookup modeling.

The first parser may preserve a table boundary and locator without reconstructing semantic cells. Continued tables, spanning headers, units, and footnotes must remain explicit or diagnosed. A rectangular extraction is not sufficient evidence of semantic row/column meaning.

## Figures, maps, and graphical material

Figures and maps occur as engineering source evidence, not decorative illustrations. The provisions include ordinary figure references and map-heavy hazard material. Appendix F contains wind hazard maps for long return periods and Appendix G contains tornado hazard maps for long return periods; corresponding commentary appendices CF and CG also exist.

Map meaning may be encoded in contours, shading, legends, labels, geographic boundaries, and scale. Initial AST ingestion must therefore preserve map/graphical regions, publication locators, parent provisions, source coordinates, references, and unsupported semantic status. OCR text is not a substitute for the map.

The retained publication also points users to ASCE digital hazard tools. Those services are not silently interchangeable with the selected publication artifact and must be modeled separately if later used.

## Representative parser hazards

The first ASCE Document AST work should explicitly preserve or diagnose at least these conditions:

- one artifact-local nonpublication page before the ASCE publication;
- a native page-label dictionary that does not match visible printed-page labels;
- no bookmark/outline tree;
- two-column reading order mixed with full-width regions;
- provisions and commentary sharing related numbering but different source roles;
- displayed equations with source-native identifiers and metric `.SI` variants;
- mathematical/special glyph extraction warnings;
- explicit exception ownership;
- tables with units and qualifying notes/footnotes;
- figures whose captions are not substitutes for graphical content;
- map-heavy hazard appendices whose semantics cannot be reduced to OCR text;
- intentionally blank pages that are part of printed pagination;
- reserved chapters/appendices and commentary numbering gaps;
- index locators that distinguish equation, figure, and table references.

Unsupported, uncertain, malformed, and ambiguous regions are useful compiler output and must not be coerced into apparently supported prose.

## Source registration

This profile does not create an ASCE-only registry. Exact source registration should use the repository's shared source-registration contract to bind publication identity, exact artifact digest, access/rights state, pagination observations, and the `DocumentSourceArtifact` consumed by Document AST work.

Unknown exact printing and incorporated-corrections state must remain explicit unknowns. A cleaner or more convenient ASCE 7-22 PDF would require a separate exact identity and an explicit adoption decision.

## Document-AST gate

Exact-source characterization is complete enough to begin the first source-backed ASCE 7-22 Document AST descendant after this profile is integrated.

That descendant should demonstrate a compact but meaningful cross-section containing:

- publication hierarchy;
- deterministic publication- and edition-specific structural IDs;
- explicit PDF/printed-page/bounding-box coordinate spaces;
- ordinary prose plus at least one non-prose source structure;
- equation representation or equation diagnostic;
- explicit graphical/table/figure unsupported handling where the chosen slice encounters it;
- generic Document AST validation;
- deterministic repeated-run behavior;
- private replay against the exact digest above.

The source profile does not add schemas, runtime models, parser adapters, extracted corpus material, semantic interpretation, executable engineering mathematics, or project evaluation.

No protected source prose, equations, tables, figures, maps, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-asce-7-22-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-asce7-22-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/asce-7-22/source-profile.md`
- requires: `action.establish-asce7-22-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.