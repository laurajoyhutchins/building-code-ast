# ASHRAE 62.1-2016 source profile

Status: exact retained source characterized for the source-profile gate; document-AST implementation has not started.

## Exact retained artifact

The retained private artifact is:

- filename: `ashrae-62_1-2016.pdf`
- SHA-256: `a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759`
- size: 1,193,586 bytes
- media type: `application/pdf`
- PDF version: 1.7
- PDF pages: 60
- page size: US Letter, 612 by 792 points
- encrypted: no
- tagged: no
- PDF forms: none
- PDF JavaScript: present
- optimized/linearized: no
- title metadata: `ANSI/ASHRAE Standard 62.1-2016`
- author metadata: `ASHRAE Special Publications`
- creator metadata: `FrameMaker 2015.2`
- producer metadata: `3-Heights(TM) PDF Producer 4.4.43.1 (http://www.pdf-tools.com)`
- PDF modification metadata: 2016-03-18
- PDF creation metadata: 2012-01-25; this predates the identified 2016 publication state and must not be treated as the publication date

The source bytes remain outside Git.

## Publication and included-addenda state

The retained artifact identifies itself as **ANSI/ASHRAE Standard 62.1-2016**, superseding ANSI/ASHRAE Standard 62.1-2013.

The foreword states that the 2016 edition combines Standard 62.1-2013 with fourteen approved and published addenda. Informative Appendix K identifies the exact incorporated set as:

`a, c, d, e, f, g, h, i, j, k, p, q, r, s`

This addenda set is therefore part of the publication state represented by these exact bytes. It must not be replaced with a current web addenda list or generalized to every artifact carrying the same 2016 edition label.

The final artifact page carries product code `86255` and the mark `3/16`. Record `3/16` as artifact-local printing/release evidence, not as a stronger publication-state claim than the source supports.

The artifact says approved addenda, errata, and interpretations may be obtained separately from ASHRAE. No embedded errata or correction sheet was identified during this characterization. That does **not** prove that no external errata existed for the edition. The retained artifact's correction/errata state therefore remains: exact base bytes characterized; no incorporated correction layer established by artifact evidence.

The copyright notice identifies © 2016 ASHRAE and all rights reserved. Treat the retained PDF as restricted/private source material. Public Git may retain hashes, compact factual metadata, locators, aggregate measurements, parser code, schemas, diagnostics, and source-safe observations, but not the PDF, bulk extracted text, reconstructive tables, figures, page images, or generated private ASTs reproducing protected expression.

## Page labels, bookmarks, and contents

The PDF catalog provides no semantic page-label mapping.

Observed printed-page numbering is stable across the standard body and appendices:

- PDF pages 1-3 are unnumbered front matter/title/committee/contents material;
- PDF page 4 carries printed page `2`;
- PDF pages 4-56 continue with a stable `printed page = PDF page - 2` mapping through printed page `54`;
- PDF pages 57-60 are unnumbered continuous-maintenance forms and back matter.

The artifact contains 23 outline/bookmark entries. They provide useful coarse navigation for the title, contents, foreword, Sections 1-9, and Appendices A-K, but do not provide subsection-level navigation.

The visual table of contents is stronger publication evidence than the PDF outline for printed-page mapping. It identifies the foreword, Sections 1-9, Normative Appendices A-B, and Informative Appendices C-K with printed page locators.

## Mandatory and informative source roles

The exact retained publication makes appendix role explicit:

- Normative Appendix A: Multiple-Zone Systems
- Normative Appendix B: Separation of Exhaust Outlets and Outdoor Air Intakes
- Informative Appendices C through K

The foreword is also explicitly informative and not part of the standard.

Appendix role must therefore be preserved per source structure. Do not infer a global rule that all appendices are normative or all appendices are informative.

## Text layer, reading order, and OCR

All 60 PDF pages expose embedded text; representative extraction from front matter, ordinary provisions, tables, equations, appendices, and back matter yields usable machine text. OCR is not required for ordinary ingestion of this exact artifact.

The source is untagged and uses multi-column and table-heavy layouts. Embedded text presence therefore does not establish perfect logical reading order. Representative extraction shows body text is generally recoverable, while tables, two-column pages, mathematical expressions, detached equation identifiers, and footnotes require geometry-aware reconstruction rather than blind linear text consumption.

OCR should remain disabled unless a later exact region demonstrates unusable embedded text.

## Publication-native structural grammar

The main standard uses numbered top-level Sections 1 through 9, decimal subsections, and deeper decimal nesting where required. Section designations, not page numbers or extraction order, should provide durable publication locators.

Observed structural families include:

- numbered sections and nested subsections;
- a dedicated definitions section plus notation/symbol definitions adjacent to calculations;
- requirements, permissions, exceptions, and informative notes;
- internal section, table, figure, equation, and appendix references;
- external standard references;
- tables with multi-row headers, units, category rows, notes, and footnotes;
- numbered and unnumbered equations/calculation expressions;
- figures and diagrams;
- normative and informative appendices;
- form-like documentation material in Informative Appendix H;
- continuous-maintenance forms and publication back matter outside the numbered standard content.

Source-specific recognition should preserve these structures without treating headers, footers, page numbers, or PDF block order as hierarchy.

## Procedure and method boundaries

Section 6 explicitly establishes distinct ventilation-design procedure contexts rather than one undifferentiated requirement stream. At minimum, the retained source identifies:

- 6.2 Ventilation Rate Procedure;
- 6.3 Indoor Air Quality (IAQ) Procedure;
- 6.4 Natural Ventilation Procedure.

These are publication-structure facts. The Document AST should preserve their boundaries and source conditions without deciding which procedure applies to a particular project.

## Tables and calculation structures

Tables are central source structures and must not be flattened into prose. Representative stressors include multi-page tables, category rows, units, footnotes, continuation headers, and source notes that qualify values.

Calculation structures are also explicit. The source contains publication-addressable equations, including appendix-scoped identifiers, as well as equations embedded in procedure text and informative calculation appendices. Mathematical extraction must preserve expression identity, symbols, nearby definitions, units, and source coordinates. A text fragment that resembles a formula is not sufficient evidence for executable mathematical semantics.

Informative Appendix E contains calculation material related to the IAQ Procedure. Its informative role must remain distinct from normative requirements even where it explains or supports calculations.

## Definitions, references, exceptions, notes, and figures

Definitions are concentrated in Section 3, but symbol definitions and locally scoped terminology also occur near equations, tables, and appendices. Later resolution must therefore be scope-aware rather than a single global string dictionary.

References should remain typed graph relationships distinguishing at least internal sections, definitions, tables, equations, figures, appendices, external standards, and unresolved citations.

Exceptions are structurally attached modifiers. Their ownership must be established from hierarchy and layout rather than nearest-text distance alone.

Informative notes and table footnotes are source-significant and may qualify interpretation without becoming normative requirements.

Figures and diagrams remain explicit source structures or diagnostics. Captions are not substitutes for graphical content, and no airflow/system semantics should be inferred from linework without reviewed support.

## Representative unsupported or high-risk structures

This source profile does not claim complete structural support for:

- spanning and multi-level table headers;
- multi-page table continuations;
- detached table notes and footnotes;
- mathematical typography containing fractions, radicals, subscripts, superscripts, or detached identifiers;
- figure/diagram internal semantics;
- form-like layouts in Informative Appendix H;
- exact symbol-scope resolution;
- complete internal/external reference resolution;
- semantic interpretation of ventilation rates, occupancy categories, or calculation results.

These cases should produce explicit unsupported or partial-support diagnostics until measured otherwise.

## What remains unresolved after characterization

The source-profile gate does not establish:

- an external errata/correction inventory for the 2016 edition;
- a stronger publication date than the artifact-local 2016 identity and `3/16` release/printing evidence;
- whole-document structural counts;
- table geometry or table semantics;
- reviewed mathematical semantics;
- reviewed provision semantics;
- project applicability or compliance behavior.

Those are descendant tasks. Exact bytes, included-addenda identity, source roles, page mapping, extraction behavior, procedure boundaries, structural families, and rights handling are now sufficiently characterized to begin Document AST work.

## Document-AST gate

A descendant Document AST must preserve all of the following simultaneously:

```text
exact artifact identity
+ exact incorporated addenda set
+ explicit unresolved correction layer
+ publication-native hierarchy
+ normative/informative source role
+ procedure/method boundaries
+ explicit source coordinate spaces
+ deterministic source-backed IDs
+ explicit tables and calculation structures
+ generic validation
+ visible unsupported structures
```

No protected source prose, reconstructive tables, figures, page images, or generated private corpus belongs in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-ashrae-62.1-2016-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-ashrae62-1-2016-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/ashrae-62.1-2016/source-profile.md`
- requires: `action.establish-ashrae62-1-2016-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.
