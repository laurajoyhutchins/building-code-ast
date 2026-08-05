# Root narratives

## Machine-legible code structure
> Build a deterministic source representation rather than a retrieval product.

**Current state:** Building Code AST is a staged compiler and evidence layer. It preserves source structure and selected semantic projections without claiming legal authority.

**Evolution:**
1. A bounded provision parser proved exact semantic spans were possible.
2. **PIVOT:** Search, RAG, summarization, and plain text could not supply stable hierarchy, provenance, or deterministic comparison.
3. The repository adopted a source-to-Document-AST-to-family-grammar architecture and left jurisdiction and compliance downstream.

**Evidence:** PRs #1, #7, #8; `README.md`; `docs/architecture.md`.
**Status:** active.

## Document AST and schema separation
> Preserve publication structure before interpreting modality or compliance meaning.

**Current state:** Document AST 0.1.0 and Provision AST 0.2.0 are separately versioned contracts.

**Evolution:**
1. The first semantic slice combined subject, modality, conditions, actions, exceptions, and spans.
2. **PIVOT:** Full-document ingestion required chapters, sections, definitions, lists, tables, notes, footnotes, and unsupported structures without semantic overreach.
3. A neutral Document AST gained deterministic identities and recursive span validation while meaning remained a later stage.

**Evidence:** PRs #1 and #8; `src/building_code_ast/document_model.py`; `schemas/document-ast.schema.json`.
**Status:** active.

## PDF layout interpretation
> Treat text, coordinates, fonts, and outlines as evidence from which reading order must be reconstructed.

**Current state:** Shared layout machinery records page blocks and geometry; family branches add more specialized analysis.

**Evolution:**
1. PDF extraction initially offered convenient text blocks.
2. **PIVOT:** Columns, headers, footers, continuation pages, wrapped lines, glyph streams, and tables made extraction order unreliable.
3. Parsers now preserve source maps and fail closed when visual structure cannot be safely recovered.

**Evidence:** PRs #13, #15, #17; `src/building_code_ast/ingest/pdf_layout.py`.
**Status:** active with unresolved layout classes.

## NEC 2017 ingestion
> Exercise the compiler against a real licensed code while keeping source expression private.

**Current state:** Main can ingest private 2017 NEC Articles 90, 100, and 110 into validated ArticleSeeds and downstream selected hierarchy and semantic outputs.

**Evolution:**
1. The supplied PDF established the first production source.
2. Article bookmarks, page transitions, two-column ordering, definition candidates, and table-like regions drove corrections.
3. Successful selected-fragment validation remained explicitly narrower than whole-edition support.

**Evidence:** PRs #13, #14, #16, merged through #22; NEC ingestion tests and how-to guides.
**Status:** active, edition-specific, selected regions only.

## NEC hierarchy and style evidence
> Recover printed NEC hierarchy without turning editorial guidance into source text.

**Current state:** The NEC hierarchy builder uses contextual Part, Section, title, marker, and list evidence. The style-manual profile is a parser prior. A private prior hierarchy is a local oracle, not a dependency.

**Evolution:**
1. Flat PDF blocks could not support stable clause locators.
2. **PIVOT:** Universal parenthetical-number parsing failed because identical syntax serves different roles.
3. NEC-specific grammar, ambiguity diagnostics, style profiles, and independent conformance comparison produced bounded confidence.

**Evidence:** PR #16 and merge PR #22; `nec_hierarchy.py`; `style_manual.py`; hierarchy integration tests.
**Status:** active for exercised 2017 material.

## Clause context and semantic modeling
> Keep printed ownership, logical grouping, and normative dependency distinguishable.

**Current state:** Selected NEC reviews preserve clauses, exceptions, notes, references, definition links, semantic tags, order, and exact spans.

**Evolution:**
1. Sentence-level modal parsing could identify requirements.
2. **PIVOT:** Continuations, ancestor-scoped exceptions, subordinate lists, definitions, and external references showed that printed hierarchy is not normative dependency.
3. Special structures and references became first-class evidence while compliance interpretation stayed out of scope.

**Evidence:** PR #14 and merge PR #22; `src/building_code_ast/nec/sections.py`; `references.py`.
**Status:** active for selected NEC sections.

## NEC edition comparison
> Separate observed source changes from extraction defects and process expectations.

**Current state:** The issued editions remain controlling; development records can only provide expected-change evidence.

**Evolution:**
1. Secondary summaries suggested a possible 2017-to-2020 changelog.
2. **PIVOT:** Summaries and development records could not establish exact issued text.
3. The branch designed independent edition parsers and expected-versus-observed reconciliation, but no authorized 2020 source was available.

**Evidence:** PR #19; ICC development-history boundary in PR #25.
**Status:** branch-only and unresolved.

## IBC 2018
> Test the architecture against ICC hierarchy and a more pathological PDF text layer.

**Current state:** IBC ingestion and layout analysis remain an open draft stack; the hierarchy parser is design-only.

**Evolution:**
1. Prior PDF-parser architecture offered useful ideas.
2. **PIVOT:** A private runtime dependency was rejected; machinery was reimplemented in the repository.
3. Glyph reconstruction, tables, figures, footnotes, definitions, decimal section parents, Parts, and appendices established the need for an IBC-specific grammar.

**Evidence:** PRs #15, #17, #18; private source audit results retained only as non-reconstructive claims.
**Status:** branch-only.

## Parser-family architecture
> Reuse contracts and evidence machinery without universalizing numbering or editorial rules.

**Current state:** Shared source identity, spans, diagnostics, table primitives, and adapter contracts coexist with separately versioned family grammars and edition profiles.

**Evolution:**
1. NEC work suggested common hierarchy machinery might be broad.
2. **PIVOT:** IBC and NFPA 13 showed incompatible numbering, annex, table, and reference behavior.
3. The reuse boundary moved downward to neutral primitives and upward to linked semantic graphs, leaving parsing family-specific.

**Evidence:** PRs #16, #18, #20, #23-#25.
**Status:** active.

## NFPA 13 2019
> Determine whether the architecture could represent a large NFPA standard beyond the NEC.

**Current state:** A draft branch contains a deterministic source-linked extractor and hierarchy bundle, but main does not support NFPA 13.

**Evolution:**
1. The exact local source was profiled from Chapters 1-31 and Annexes A-E and I.
2. **PIVOT:** Synthesized annex ancestry was separated from explicit explanatory correspondence, and external-standard references gained target domains.
3. Tables are preserved conservatively; figure and diagram semantics remain unsupported.

**Evidence:** PR #20.
**Status:** branch-only pending independent verification.

## UL White Book and related corpora
> Keep listing and certification evidence connected to code without pretending it is code hierarchy.

**Current state:** Electrical Equipment Lineage owns UL White Book compilation, CCNs, Product iQ observations, and equipment lineage. Building Code AST may eventually link citations into that corpus.

**Evolution:**
1. UL material was considered as additional machine-legible technical content.
2. **PIVOT:** Listings, categories, certifications, products, holders, and dated observations require a different model than prescriptive code clauses.
3. A linked-corpus or ontology boundary is favored, but interchange identities remain open research.

**Evidence:** `laurajoyhutchins/electrical-equipment-lineage` current README and compiler contract.
**Status:** ownership active; cross-corpus model unresolved.

## Provenance and trust
> Preserve exact evidence and uncertainty while maintaining source licensing boundaries.

**Current state:** Source identities distinguish evidence role, publication state, access, rights, and exact bytes; AST nodes and diagnostics retain spans and source context.

**Evolution:**
1. Exact sentence spans were required from the first provision parser.
2. Real PDFs added pages, geometry, parser versions, source maps, review state, and restricted-source boundaries.
3. Evidence adapters now fail closed when role, media type, bytes, ordering, or action chains do not match their contracts.

**Evidence:** PRs #1, #7, #8, #13, #20, #23, #27-#30.
**Status:** active.

## Validation strategy
> Treat support as a claim to prove per source, edition, region, and construct.

**Current state:** Validation combines recursive invariants, deterministic synthetic fixtures, exact-source private replay, known-good references, human review, official-corpus tests, and exact-head CI.

**Evolution:**
1. Synthetic tests established reproducible contracts.
2. **PIVOT:** Source fragments and official corpora exposed defects invisible in synthetic data.
3. Support claims now follow merged tree state, tests, generated outputs, and reviewed source evidence rather than PR prose.

**Evidence:** PRs #16, #17, #20, #27, #29, #30; 157 current unit tests.
**Status:** active.

## Downstream boundaries
> Keep the AST useful by refusing to own every adjacent domain.

**Current state:** Building Code Map owns jurisdiction and adoption; Electrical Equipment Lineage owns product and listing evidence; Building Code AST owns source structure and source-derived parser evidence.

**Evolution:**
1. The project was motivated by downstream code applicability and analysis.
2. **PIVOT:** A source tree could not itself establish which code applies, whether equipment is listed, or whether a project complies.
3. Amendments are represented as evidence-backed patches while applicability, consolidation, and reasoning remain downstream.

**Evidence:** current READMEs and PR #26.
**Status:** active.

## Repository governance and current limits
> Maintain accepted current knowledge separately from causal historical explanation.

**Current state:** LORE owns accepted repository knowledge and generated documentation. Deciduous owns this non-authoritative causal graph.

**Evolution:**
1. An early attempt recreated LORE-style machinery locally.
2. **PIVOT:** PR #11 replaced the facsimile with LORE's shipped skill, trust root, transaction, and projections.
3. This backfill adds stable causal history while keeping branch-only parser experiments and unresolved evidence explicitly qualified.

**Evidence:** PR #11; `lore.yaml`; `.lore/`; upstream Deciduous archaeology conventions.
**Status:** active.

## Section-first code addressing
> Use the code publication's own hierarchy as the durable coordinate system.

**Current state:** Draft PR #33 implements and verifies section-first addressing. Sections, subsections, tables, figures, exceptions, definitions, and equations are primary navigation coordinates. PDF pages remain secondary provenance.

**Evolution:**
1. Page coordinates were retained to reproduce source evidence and debug extraction.
2. **PIVOT:** Engineers navigate and cite code by sections and subsections, while pagination varies across editions, printings, and source files.
3. The section-addressing contract now forbids page-derived fallback identities and bases ordering and edition comparison on structural code addresses and explicit renumbering relationships.

**Evidence:** Draft PR #33 at `3740ea3435ed7c2092ddb07001325d4b8ce3ba77`; `docs/reference/section-addressing.md` on `agent/ibc-2018-closeout`.
**Status:** branch-only pending merge of PR #33.
