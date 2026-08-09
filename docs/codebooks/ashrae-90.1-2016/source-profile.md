# ASHRAE 90.1-2016 source profile

Status: exact retained artifact characterized; document-AST implementation has not started.

## Exact retained artifact

- retained filename: `ashrae-90_1-2016.pdf`
- size: 3,475,675 bytes
- media type: `application/pdf`
- SHA-256: `275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162`
- PDF pages: 388
- PDF version: 1.4
- encryption: Standard security handler V1/R2, 40-bit RC4
- effective permissions: printing and text copying permitted; document changes and annotation changes restricted
- page size: 612 x 792 PDF points throughout the retained artifact
- storage: outside Git

The digest identifies the exact retained bytes. Filename, edition label, page count, or another nominally identical copy are not substitutes for artifact identity.

The retained bytes are readable with the normal PDF text/layout path; OCR is not required for the characterized source. Distributor/license footer text is embedded in the retained copy and is source-artifact evidence, not publication semantics.

## Publication identity and artifact-specific state

The retained publication self-identifies as:

- designation: `ANSI/ASHRAE/IES Standard 90.1-2016`
- edition form: I-P Edition
- title: *Energy Standard for Buildings Except Low-Rise Residential Buildings*
- supersedes: ANSI/ASHRAE/IES Standard 90.1-2013
- copyright year: 2016
- product code printed on the retained back cover: `86274`
- back-cover date code: `10/16`

The PDF metadata title agrees with the designation and I-P edition. Its creator is `FrameMaker 2015.2`, producer is `PDPreStamp v3.3`, and modification timestamp is 2016-10-31 UTC. Those metadata values describe the retained artifact; they do not independently establish a publication revision.

The retained source does not state an exact day-of-publication or a numbered printing. The `10/16` back-cover code supports October 2016 as the artifact's publication/production month, but this profile does not infer a more specific printing identity.

The retained copy also contains IHS Markit license stamping dated 2018-03-27. That distribution/access stamp is later than the publication content and must not be interpreted as a 2018 revision of Standard 90.1-2016.

## Included addenda and correction state

The title page states that the 2016 edition includes the ANSI/ASHRAE/IES addenda listed in Appendix H. Informative Appendix H then states that Standard 90.1-2016 incorporates all addenda to Standard 90.1-2013 and provides the individual addendum records and approval dates in Table H-1.

This is sufficient source evidence to characterize the retained publication as the 2016 edition incorporating the 90.1-2013 addenda enumerated by its own Appendix H. The table occupies printed pages 305-313 and contains 120 addendum identifiers, including a small set explicitly identified as originating as addenda to 90.1-2010.

The retained publication separately notes that approved addenda, errata, or interpretations for this standard may be available from ASHRAE. It does not identify a post-publication errata package or later 90.1-2016 addenda as incorporated into these exact bytes. Therefore:

- incorporated pre-publication addenda state: source-backed by Appendix H;
- later 90.1-2016 addenda: not represented merely because they may exist externally;
- post-publication errata/corrections: unresolved unless a specific correction is evidenced in the retained bytes or separately modeled correction evidence;
- no external correction sheet should silently rewrite this source artifact.

## Coordinates, pagination, and navigation

The retained PDF has no native page-label dictionary. Printed page labels must therefore be recovered from publication content rather than a PDF page-label oracle.

Observed mapping sufficient for parser work:

- PDF pages 1-4 are unnumbered title, committee, notices, and blank/front matter;
- PDF page 5 is the contents page;
- PDF page 6 is an unnumbered blank/licensing page;
- PDF page 7 is printed page 3;
- from printed page 3 through printed page 380, the stable mapping is `pdf_page = printed_page + 4`;
- printed page 305 / PDF page 309 begins Informative Appendix H;
- printed page 315 / PDF page 319 begins Reference Standard Reproduction Annex 1;
- printed page 380 / PDF page 384 is the last numbered annex page;
- PDF pages 385-388 are continuous-maintenance forms/policy/back-cover material without the numbered publication-page sequence.

The retained PDF exposes a substantial native outline: 720 bookmark entries. The outline covers major sections and deeply nested publication locators and is useful structural evidence, but bookmark presence does not replace source-layout verification.

The one-page contents table is reliable for top-level section and appendix starts, but it is intentionally much shallower than the native outline and the publication hierarchy.

## Text layer and reading order

A native selectable text layer is present across the retained PDF, including prose, tables, equations, appendices, and annex material. OCR is not required for ordinary extraction from this artifact.

Reading order is generally serviceable for prose, but raw text extraction is not a trustworthy structural parser by itself. Known complications include:

- repeated ASHRAE/IHS license footer material;
- multi-column and spanning-header tables;
- table continuation across pages;
- equations whose display arrangement matters;
- footnotes and notes positioned separately from the body they qualify;
- figures/maps whose meaning is not recoverable from text order alone;
- front/back matter that is not part of the numbered provisions.

Layout coordinates and publication hierarchy must remain available when converting these observations into Document AST nodes.

## Publication grammar

The retained source uses publication-native numbered sections and nested subsections as the primary provision hierarchy. The native outline confirms deep numeric nesting rather than a flat page-oriented organization.

Representative structural forms include:

- numbered sections and subsections;
- centralized prose definitions in Section 3.2 and abbreviations/acronyms in Section 3.3;
- lettered and numbered lists nested beneath provisions;
- explicitly labeled exceptions associated with requirements;
- internal section, table, appendix, figure, and equation references;
- external standards collected principally in Section 12 and informative references in Appendix E;
- explicitly identified tables with titles, spanning headers, units, footnotes, and continuation pages;
- display and inline equations, including source-displayed unit-system variants and symbol context;
- explicitly identified figures and graphical climate material;
- notes and informative notes that must not be flattened into requirements;
- publication-defined normative and informative appendices;
- a reference-standard reproduction annex with its own unusual source-role boundary.

Structural locators such as `6.5.1`, table identifiers, appendix locators, and equation/figure identifiers should drive durable node identity. PDF page and geometry remain provenance coordinates.

## Mandatory and informative boundaries

The contents and appendix title matter explicitly classify the retained appendices:

- Normative Appendix A
- Informative Appendix B, retained for future use
- Normative Appendix C
- Informative Appendix D, retained for future use
- Informative Appendix E
- Informative Appendix F
- Normative Appendix G
- Informative Appendix H

This is source-backed evidence that `appendix` alone does not imply normative status.

Reference Standard Reproduction Annex 1 requires an additional distinction. Its title matter says the annex contains normative material reproduced from an existing ASHRAE standard cited by Standard 90.1, while also stating that the annex itself is not part of Standard 90.1 and that its inclusion is informative. A future source-role model must preserve both facts rather than coercing the annex into simply `normative` or simply `informative` without context.

The foreword is explicitly informative and not part of the standard. Notes and other informative material must likewise retain publication-defined role evidence rather than inheriting authority solely from proximity to mandatory provisions.

## Tables, equations, figures, and footnotes

Tables must remain explicit structures. The retained source includes ordinary tables, complex multi-level headers, footnotes, and tables that continue across page boundaries. Table identity should use the publication locator and preserve source region, parent provision, continuation evidence, and footnote relationships.

Equation support should begin with region/grouping and source display preservation. Extracted glyphs alone are not sufficient evidence for executable calculations. Preserve equation identifiers where present, expression spans, associated symbols/definitions, units, and surrounding applicability context separately.

Figures and graphical material remain explicit structures or diagnostics. Annex 1 includes maps and other reference-standard graphics whose structural presence is evident even when semantic interpretation is not yet supported.

Table and prose footnotes can materially qualify nearby content. They must not be discarded as page furniture merely because they occur near repeated footer material.

## Representative unsupported or ambiguous structures

Early Document AST work should expect explicit diagnostics for at least:

- spanning and multi-row table headers;
- multi-page table continuation and repeated headers;
- table footnote attachment to table/row/column/cell scopes;
- equation line grouping and symbol association;
- figure/map regions without semantic interpretation;
- notes whose publication role differs from surrounding mandatory text;
- exception ownership when typography and hierarchy disagree;
- Reference Standard Reproduction Annex 1's mixed container/source-role semantics;
- repeated distributor/license footer text that must be classified as artifact-local furniture;
- any cross-reference whose target cannot be resolved from publication-native locators.

Unsupported cases are valid compiler output and should remain measurable.

## Rights and access classification

Rights/access classification: copyrighted, license-restricted private source.

The retained source includes explicit license language restricting reproduction/networking. Do not commit the PDF, page images, reconstructive source prose, complete tables, equations, figures, private hierarchy oracles, or generated private AST corpora that reproduce protected expression.

Public Git may retain the exact hash, compact metadata, publication-state facts, publication-native locators, source-role facts, aggregate measurements, parser code, schemas, synthetic fixtures, and non-reconstructive diagnostics.

## Document-AST gate

A descendant document-AST PR should establish and test:

1. exact artifact and publication-state identity;
2. explicit normative/informative/other source-role evidence;
3. publication-native structural locators;
4. PDF-page, printed-page, text-span, and geometry coordinate provenance;
5. deterministic publication-state-aware IDs;
6. section/subsection/list/exception hierarchy;
7. explicit tables, equations, figures, notes, and references;
8. generic Document AST validation;
9. unsupported/ambiguous structure diagnostics;
10. synthetic public fixtures plus private exact-source replay.

Broad energy-rule semantics remain out of scope until those structural facts are trustworthy.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-ashrae-90.1-2016-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-ashrae90-1-2016-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/ashrae-90.1-2016/source-profile.md`
- requires: `action.establish-ashrae90-1-2016-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.