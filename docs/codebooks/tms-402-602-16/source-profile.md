# TMS 402/602-16 source profile

Status: exact retained source characterized for the source-profile gate; document-AST implementation has not started.

## Exact retained artifact

The retained private artifact is:

- filename: `tms-402_602-2016.pdf`
- SHA-256: `947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d`
- size: 53,081,346 bytes
- media type: `application/pdf`
- PDF version: 1.6
- PDF pages: 430
- page size: US Letter, 612 by 792 points
- encrypted: no
- tagged: no
- PDF forms: none
- PDF JavaScript: none
- optimized/linearized: no
- creator metadata: `KM_C364e`
- producer metadata: `KONICA MINOLTA bizhub C364e`
- PDF creation/modification metadata: 2021-03-22

The source bytes remain outside Git. The 2021 PDF metadata describes this retained scan and is not the publication date of the standards.

## Publication state

The retained artifact identifies the standards as:

- `Building Code Requirements for Masonry Structures`, TMS 402-16;
- `Specification for Masonry Structures`, TMS 602-16.

The publication front matter identifies the standards as adopted by The Masonry Society on 2016-10-09, superseding the 2013 edition. This retained copy identifies itself as the second printing and says that it includes errata through 2018-10-22.

The artifact is copyrighted by The Masonry Society and contains explicit reproduction restrictions. Treat the retained source as restricted/private source material. Public Git may retain exact hashes, compact factual metadata, locators, aggregate measurements, parser code, and source-safe observations, but not the PDF, bulk extracted text, page images, reconstructive tables, figures, or commentary.

## Artifact-local duplicate prefix

The 430-page PDF is not a clean one-pass scan of the publication.

PDF pages 1-48 contain a partial leading copy of the beginning of the publication. That run includes front matter, the beginning of TMS 402, and reaches approximately printed page `C-30`. A coherent complete publication restarts at PDF page 49.

This duplicate prefix is part of the exact artifact identity and must not be silently discarded from provenance. It is not used as the canonical publication-component region below. Ingestion should retain a diagnostic or equivalent source observation that the prefix exists and should avoid emitting duplicate structural nodes from it.

The duplicate prefix is also evidence that artifact byte order alone is not a publication hierarchy.

## Canonical artifact-local regions

The following ranges use **1-based PDF page numbers in this exact 430-page artifact**:

| Artifact region | PDF pages | Publication role | Printed-page evidence |
|---|---:|---|---|
| duplicated partial prefix | 1-48 | noncanonical repeated source observations | restarts publication before a complete TMS 402 run |
| shared publication front matter | 49-56 | combined-publication front matter | no TMS component page namespace |
| TMS 402 component | 57-320 | TMS 402-16 plus its adjacent informational commentary and commentary references | `C-i` at PDF 57; `C-1` at PDF 67; `C-254` at PDF 320 |
| TMS 602 component | 321-413 | TMS 602-16 plus its adjacent informational commentary and commentary references | `S-i` at PDF 321; `S-1` at PDF 325; `S-89` at PDF 413 |
| separator | 414 | intentionally blank separator | no component locator |
| shared combined index | 415-430 | combined-publication index | `I-1` at PDF 415 through `I-16` at PDF 430 |

These regions distinguish physical artifact coordinates from logical publication ownership. TMS 602 is not a descendant of the final TMS 402 node merely because its pages follow TMS 402 in the PDF.

## Page labels, bookmarks, and contents

The PDF catalog provides no semantic page-label mapping. Printed labels must therefore be observed from page content rather than read from PDF page-label metadata.

The source uses independent printed-page namespaces:

- `C-*` for TMS 402 and its commentary material;
- `S-*` for TMS 602 and its commentary material;
- `I-*` for the shared index.

The artifact contains only two shallow numeric outline/bookmark entries, pointing to PDF pages 1 and 211. They do not provide useful publication-semantic navigation.

By contrast, the source contains independent visual tables of contents for TMS 402 and TMS 602 at PDF pages 57 and 321 respectively. Those contents, component headings, printed-page namespaces, and repeated component headers provide stronger boundary evidence than the PDF outline.

## Publication components and normative roles

One physical PDF contains two distinct standards. Preserve at least these logical identities:

```text
exact source artifact
  -> TMS 402-16 publication component
  -> TMS 602-16 publication component
```

The source describes TMS 402 as the building-code requirements document and TMS 602 as the construction specification required by the Code. Their roles are related but not interchangeable.

Both component regions place informational commentary adjacent to normative text. The publication front matter expressly distinguishes commentary from mandatory standard text. A parser must therefore preserve source role as well as publication component. Spatial adjacency is not sufficient evidence of normative equivalence.

The combined index is shared publication apparatus. It is not a child of either standard merely because it follows TMS 602 physically.

## Structural grammar

The two component documents do not have identical publication grammars.

TMS 402 uses Parts containing Chapters, then decimal sections and subsections. Its contents identify independently scoped notation and definitions within the TMS 402 hierarchy. The component also contains equations, tables, figures, appendices, component-specific commentary references, notes, and other structures that require explicit structural treatment.

TMS 602 uses Parts with decimal sections and subsections without the same Chapter layer shown by TMS 402. Its contents separately identify definitions and include specification-specific checklist material in addition to its commentary references. TMS 602 therefore needs its own publication-native root and grammar characterization rather than being forced through a TMS 402 chapter grammar.

Shared layout or numbering helpers may later be justified, but only after component identity is retained.

## Text layer, reading order, and OCR

Representative extraction from both components yields no usable embedded text layer. The artifact is image-based for practical ingestion purposes.

OCR is therefore required for machine text extraction from this retained artifact. OCR output must be explicitly provenance-marked and must not be represented as embedded source text.

Reading order is not a simple single stream. Representative TMS 402 and TMS 602 pages use parallel normative and commentary regions, with commentary visually distinguished from standard text. Headers, tabs, footers, scan marks, and personalized print-watermark material are not publication hierarchy.

A durable extractor must preserve page and region coordinates, distinguish normative and commentary roles, and avoid interleaving the parallel columns into one anonymous text sequence.

## Parsing stressors observed

Source-safe representative observations from the exact artifact include:

- parallel normative text and informational commentary on the same page;
- equations and displayed notation;
- tables with headers, footnotes, and continuations;
- figures and graphical material;
- intentionally blank pages used for publication layout;
- component-specific commentary reference sections;
- TMS 602 checklist structures;
- a shared cross-component index;
- the artifact-local duplicated prefix.

Detection of these structures is not a claim that their geometry, semantics, or engineering meaning has been parsed.

## Cross-document references

The source explicitly establishes a relationship between the two standards: TMS 602 is the specification required by TMS 402. The combined index also uses both `C-*` and `S-*` locators.

Later reference extraction must therefore distinguish same-component references from TMS 402 -> TMS 602 and TMS 602 -> TMS 402 relationships. A reference edge must retain source publication, source locator/span, target publication, target locator, edition scope, and resolution state.

Referenced prose must remain in its owning component rather than being copied into the referring node.

## Generic-contract question exposed by this source

The current generic source-register contract gives one source-register entry one publication identity and one primary evidence role. The current Document AST source identity similarly identifies an artifact and edition without an explicit publication-component field.

This exact artifact contains two publication components and also carries informational commentary adjacent to normative material. That mismatch is a genuine generic modeling question for the first structural descendant, not a reason to add a TMS-only registry and not a reason to broaden this source-profile PR into a schema change.

The next implementation should first determine the smallest generic way to preserve component identity and source role while keeping one exact physical artifact identity.

## What remains unresolved after characterization

This profile does not claim:

- a reviewed per-page printed-label map for every page in the 430-page artifact;
- a selected OCR engine or measured OCR accuracy;
- whole-component structure counts;
- complete cross-reference detection or resolution;
- table geometry or table semantics;
- mathematical interpretation of equations;
- reviewed semantics or executable masonry calculations;
- a final generic schema for multi-publication artifacts.

Those are descendant compiler tasks. The source-profile gate is satisfied by exact artifact identity, publication state, component boundaries, page systems, structural distinction, extraction constraints, representative stressors, rights handling, and explicit unresolved questions.

## Document-AST gate

A descendant Document AST must preserve all of the following simultaneously:

```text
exact artifact identity
+ explicit TMS 402 or TMS 602 ownership
+ publication-native hierarchy
+ explicit source coordinates
+ normative/commentary role distinction
+ deterministic component-scoped IDs
+ generic validation
+ visible unsupported structures
```

Do not flatten the combined PDF into one anonymous hierarchy. Do not parse the duplicate prefix into a second logical copy of TMS 402. Do not treat OCR output as exact embedded text. Do not promote commentary to normative text.

No protected source prose, tables, figures, or page images belong in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-tms-402-602-16-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-tms402-602-16-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/tms-402-602-16/source-profile.md`
- requires: `action.establish-tms402-602-16-publication-root`

This remains noncanonical handoff metadata until the profile work is integrated and exact merge evidence is available.
