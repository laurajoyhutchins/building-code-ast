# AISC Steel Construction Manual 15th Edition source profile

Status: source characterization has established the retained artifact's edition/printing identity and its major internal publication-role boundaries. Document-AST implementation has not started. Exact-byte and physical-PDF coordinate gates remain open, so this profile does not claim durable ingestion coverage and does not create a `SourceRegisterEntry`.

## Retained artifact identity

- publication key: `aisc-scm-15`
- retained filename: `scm-15.pdf`
- observed size: 221,820,282 bytes
- media type: `application/pdf`
- issuing body identified by the retained artifact: American Institute of Steel Construction (AISC)
- edition identified by the retained artifact: Fifteenth Edition
- copyright year shown by the retained artifact: 2017
- printing state identified by the retained artifact: Second Printing, June 2018
- source storage: private, outside Git

The retained source is operationally identifiable by its filename, byte size, connected storage object, and publication text. Its cryptographic identity is not yet complete: SHA-256 of the exact retained bytes has not been verified in this characterization run. A durable `SourceRegisterEntry` must wait for that digest and the remaining publication-state fields below.

The printing statement does not by itself establish a correction set, digital revision, or exact `published_on` value. Those fields remain unresolved rather than being inferred from the copyright year or printing month.

## Evidence and access boundary

Connected storage metadata confirms the retained filename, size, PDF media type, and private/non-shared storage state. Text extraction from that same retained object exposes the Manual's title/front matter, contents, preface, scope, numbered parts, and the Part 16 publication divider.

The current connected surface cannot provide the 221 MB raw object to this runtime for exact-byte inspection. It also does not expose PDF page metadata, bookmark structure, page-label metadata, geometry, or whether its readable text projection came exclusively from the embedded PDF text layer. Those properties therefore remain explicit local-verification gates rather than guessed facts.

The source carries an all-rights-reserved reproduction restriction. Treat the retained artifact as restricted private source material. Public Git may contain hashes, factual metadata, component identities, boundary locators, aggregate measurements, parser code, synthetic fixtures, and non-reconstructive observations, but not source prose, tables, page images, figures, design aids, or a generated corpus that reconstructs protected expression.

## Verified publication and content-role inventory

The artifact is not one homogeneous normative publication. The Manual's own front matter describes it as a handbook providing design guidance and aids, states that it is based on separately issued standards, and says that specifications, codes, and standards are printed in Part 16 for reference. Its scope separately describes specification requirements, design recommendations, design considerations, product/property information, member design, connection design, specifications/codes, and miscellaneous information.

The following is the minimum evidence-backed component inventory. It is a publication/content-role inventory, not a claim that every row is an independently issued publication.

| Component | Verified source role | Publication identity / state | Boundary evidence | Authority note |
|---|---|---|---|---|
| Manual front matter | editorial, organizational, explanatory, scope and reference context | AISC Steel Construction Manual, Fifteenth Edition, Second Printing June 2018 | precedes Part 1 | not a substitute for the provisions it describes |
| Manual Parts 1-15 | Manual handbook material containing product/property reference information, summarized specification requirements, design recommendations, design considerations, tables and design aids | same Manual state | numbered Part 1 through Part 15 divisions | mixed role; do not classify the whole region as normative text |
| Part 16 container | organizational wrapper for separately issued specifications/codes/standards | same Manual state | explicit `PART 16` / specifications-and-codes divider | the wrapper does not erase the identity of the publications it contains |
| AISC Specification for Structural Steel Buildings | independently issued specification reproduced in Part 16 | ANSI/AISC 360-16, dated July 7, 2016 | publication title page follows the Part 16 divider | normative specification within its own publication; legal applicability remains external/context-dependent |
| RCSC Specification for Structural Joints Using High-Strength Bolts | independently issued specification reproduced in Part 16 | 2014 edition, dated August 1, 2014 | separate publication title in the Part 16 sequence | preserve RCSC publication identity; do not fold its provisions into Manual prose |
| AISC Code of Standard Practice for Steel Buildings and Bridges | independently issued code/standard reproduced in Part 16 | 2016 publication, dated June 15, 2016 | separate publication title in the Part 16 sequence | preserve its own scope and authority context |
| Manual Part 17 | miscellaneous data and mathematical/reference information | same Manual state | numbered Part 17 division after Part 16 | reference/supporting role unless narrower source evidence establishes otherwise |
| General nomenclature and index | terminology/navigation/supporting matter | same Manual state | follows the numbered Manual parts | supporting matter, not an independent normative publication |

The Part 16 sequence establishes three independently meaningful internal publications. Their logical component starts are their own publication title pages; each component ends before the next independently titled publication, with the final Part 16 publication ending before Part 17. Exact PDF page indices and printed-page labels for those boundaries are not yet verified.

The Manual's preface also identifies Design Examples, the Shapes Database, and background/supporting literature as resources that supplement the Manual and are available separately. They are not inventoried as components of this retained PDF merely because the Manual references them.

## Manual role boundaries

The Manual's own scope provides a coarse role map that should be preserved before any finer parser grammar is selected:

- Part 1: dimensions and properties for structural products;
- Part 2: material/specification requirements and general design considerations;
- Parts 3-6: member design;
- Parts 7-15: connection design;
- Part 16: specifications and codes;
- Part 17: miscellaneous information.

This role map is intentionally coarser than a Document AST. It establishes where recognition grammars may change without pretending that every Manual part is an independent publication.

The Manual also states that available-strength tables are developed from geometric conditions and applicable limit states from the AISC Specification. That is an explicit relationship between Manual design/reference material and the separately reproduced specification. It is not evidence that a table and the controlling specification provision have the same source role.

## Normative boundary

Do not infer authority from physical proximity inside the PDF.

The retained artifact supports these distinctions:

- the AISC Specification, RCSC Specification, and AISC Code of Standard Practice retain separate publication identities inside Part 16;
- Manual Parts 1-15 combine handbook/reference material, summaries of specification requirements, recommendations, considerations, tables, and design aids;
- references to an external standard do not make that external publication part of this artifact;
- a Manual table or design aid derived from a specification relationship is not thereby the controlling normative provision;
- legal, contractual, or jurisdictional applicability of any embedded standard is outside this structural characterization.

Requirement-like words in Manual explanatory material therefore must not be promoted to controlling requirements without component and source-role context.

## Coordinate systems and boundary locators

The source exposes several publication-native coordinate systems that must remain component-scoped:

- Manual part numbers and headings for the Manual handbook layer;
- the AISC 360-16 specification's own hierarchy and identifiers;
- the RCSC specification's own hierarchy and identifiers;
- the AISC Code of Standard Practice's own hierarchy and identifiers;
- table, equation, note, figure, reference, and index coordinates where each component defines them.

The exact printed-page-label syntax, PDF-page-number mapping, and component PDF page ranges are not yet verified. Until they are, use publication-native component boundaries as structural evidence and do not manufacture page ranges.

A future locator must identify both the component coordinate space and the physical source coordinates. PDF page number alone is not a publication identity.

## Text and layout characterization

Readable text extraction is available from the retained object and preserves the broad reading sequence through the contents, front matter, preface, scope, Manual parts, and Part 16 divider. It is not exact enough to serve as a lossless source projection: the extracted text shows character substitutions, spacing errors, and degradation in dense tabular and mathematical regions.

Consequences:

- plain-text extraction is adequate for source reconnaissance and boundary discovery;
- it is not evidence of faithful table geometry, equation typography, symbol identity, subscripts/superscripts, or figure semantics;
- native text-layer coverage versus any provider-side OCR contribution is unresolved because extraction provenance is not exposed by the connected surface;
- project OCR is not justified globally from this evidence and must remain explicit, local, region-scoped, and provenance-bearing if later needed;
- geometry quality must be measured from the exact PDF bytes before table, equation, or figure claims are made.

## Structures that will stress parsing

The retained source already establishes several high-value structural stresses without requiring protected content in Git:

- very dense dimensional/property tables in the Manual reference material;
- available-strength tables whose values depend on specification-defined limit states;
- explicit design aids, including additions called out by the Manual's preface;
- mathematical equations and symbolic notation in design material;
- cross-references from Manual design material to AISC and RCSC provisions;
- three separate publication grammars embedded inside Part 16;
- nomenclature and index structures that should not be mistaken for ordinary body hierarchy.

Figure/diagram geometry has not yet been characterized. Do not infer connection geometry, section orientation, load path, dimensions, or boundary conditions from extracted labels alone.

## Source-register implications

The current source-register contract requires exact SHA-256 and one primary evidence role. This physical artifact contains multiple internal source roles, including independently issued specification/code material and Manual handbook/reference material.

This PR does not change the generic source-register schema. It also does not force the entire physical PDF into `normative_text` merely because Part 16 contains normative specifications. Exact artifact registration and component-role mapping should be completed with the component-specific descendant work once the exact-byte gate is satisfied.

## Exact-byte and physical-PDF gates still open

Before a component parser can claim exact-source verification, complete and record:

- SHA-256 of the exact retained PDF bytes;
- PDF page count and PDF version;
- encryption, permissions, and extraction restrictions reported by the PDF itself;
- printed-page-label to PDF-page mapping;
- exact physical PDF ranges for the major component boundaries;
- bookmark presence, hierarchy, and quality;
- table-of-contents alignment with physical boundaries;
- embedded text-layer coverage and extraction provenance across prose, tables, equations, figures, and index regions;
- extraction-order quality outside the readable reconnaissance samples;
- geometry quality across representative prose, table, equation, and figure regions;
- any region-scoped OCR requirement;
- correction/errata state and digital revision, if any, beyond the verified Second Printing statement;
- exact publication-date fields needed by the source-register contract;
- access/license provenance needed for a final rights classification.

These are pre-ingestion and exact-source-verification gates. Their unresolved status does not justify collapsing the already verified publication/component boundaries.

## Document-AST gate

No descendant should parse all 221 MB into one AISC tree.

After this profile lands, choose one coherent component whose exact physical range can be verified. The independently identified Part 16 publications are eligible candidates because they have explicit publication identities and independent grammars, but this source-profile PR does not select or implement the first parser.

A first component-specific Document-AST descendant must name the component, preserve its source role, use deterministic component-aware IDs, declare its coordinate space, validate against generic Document AST contracts, retain unsupported structures visibly, and report component-level support rather than claiming support for the entire Manual.

## Public/private verification split

Public verification may use synthetic fixtures, factual component/boundary metadata, hashes, diagnostics, and aggregate measurements. Exact-source replay, geometry measurement, table/equation inspection, and any protected source-derived corpus remain private.

No protected source prose, tables, figures, page images, commentary, or reconstructive extracted corpus belongs in public Git.

## Knowledge bootstrap

LORE source-profile bootstrap starts from `.lore/tasks/bootstrap-aisc-scm-15-source-profile.yaml`.

Deciduous handoff metadata:

- semantic ID: `action.characterize-aisc-scm15-source`
- node type: `action`
- arc: `parser-families`
- lifecycle while branch-only: `proposed`
- current architecture: `false`
- evidence path: `docs/codebooks/aisc-scm-15/source-profile.md`
- requires: `action.establish-aisc-scm15-publication-root`

PR #58 currently owns accepted LORE materialization for the already merged publication-root forest. This source-profile branch remains outside accepted LORE history until durable integration evidence exists. No canonical Deciduous patch or generated archaeology projection is edited here.
