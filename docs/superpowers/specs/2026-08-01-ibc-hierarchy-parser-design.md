# IBC hierarchy parser design

**Status:** Concept approved; awaiting written-spec review

## Problem

The bounded 2018 IBC ingestion pipeline now reconstructs positioned glyphs into source-backed lines, logical blocks, ruled tables, source maps, and a validated Document AST. Its chapter projection is still structurally flat: each classified block is appended directly beneath the Chapter node.

That flat projection preserves source text but loses the publication hierarchy required for reliable section ownership, nested provision traversal, list and exception attachment, table placement, cross-reference indexing, and later semantic compilation.

The IBC has a different grammar from the NEC. The NEC hierarchy is article-oriented and uses alternating parenthesized subdivision markers. The IBC is chapter-oriented and is primarily governed by decimal section numbers, with additional parts, appendices, exceptions, numbered conditions, tables, figures, and editorial structures. The implementation should reuse the proven hierarchy-building concepts from the NEC work without importing NEC-specific rules or creating a runtime dependency between the two parsers.

## Goals

1. Infer the IBC publication hierarchy from classified ChapterSeed blocks and source order.
2. Produce canonical locators for chapters, parts, sections, subsections, nested enumerations, exceptions, tables, figures, definitions, notes, and retained unsupported structures.
3. Nest structural and nonstructural nodes under their nearest valid owner.
4. Expand structural-node spans so each parent covers its complete descendant range.
5. Preserve every source-backed block exactly once, even when classification or ownership is uncertain.
6. Reconcile parsed hierarchy against an independently extracted table-of-contents outline when one is available.
7. Emit deterministic diagnostics for missing, duplicate, impossible, out-of-order, and ambiguously owned structures.
8. Keep the public repository source-free and keep private IBC text-bearing artifacts out of Git.
9. Keep the generic Document AST contract publication-neutral.

## Non-goals

- Interpreting code requirements, applicability, exceptions, or compliance outcomes.
- Resolving adopted amendments or jurisdiction-specific changes.
- Making the NEC parser a dependency of the IBC parser.
- Treating the table of contents as authoritative enough to repair body output silently.
- Inferring semantic row spans, column spans, units, applicability, or regulatory meaning from table geometry.
- Parsing all IBC chapters in this slice; the existing bounded Chapters 1 through 3 production range remains the initial verification corpus.
- Publishing proprietary IBC source text, generated ChapterSeed files, page images, or private conformance artifacts.

## Approaches considered

### 1. Generic marker-stack parser shared directly with NEC

A single configurable hierarchy engine would accept marker grammars for both publications.

This maximizes code reuse, but it would force decimal IBC sections and alternating NEC clause markers through one abstraction before their invariants are fully understood. The likely result is a generic engine with publication-specific conditionals hidden inside it.

### 2. IBC-specific hierarchy builder using shared low-level utilities

The IBC receives its own structural recognizer and hierarchy builder. It may reuse neutral helpers for span expansion, tree traversal, diagnostic construction, and conformance reporting, but not NEC grammar or NEC node assumptions.

This keeps the grammar explicit, makes failures easier to reason about, and leaves room to extract a genuinely shared framework later from two proven implementations.

**Recommended approach.**

### 3. Table-of-contents-driven reconstruction

The parser would build the expected tree from the table of contents, then place body blocks into that structure.

This gives strong completeness checks but is unsafe as the production parser because contents pages omit many subordinate structures and can differ from body typography. It is suitable as a non-mutating oracle, not as the primary hierarchy source.

## Architecture

### Production path

`IbcLayoutDocument` and `ChapterLayout` remain the source of page geometry, line order, logical blocks, table candidates, and source fragments. The projection layer continues to build normalized chapter text and source-map entries.

Before the Chapter node is finalized, classified block records are passed to a new IBC hierarchy builder. The builder consumes source-ordered records and maintains structural state for:

- Chapter;
- optional Part;
- decimal Section and Subsection levels;
- structural enumerations owned by a provision;
- Exception and numbered exception entries;
- definition entries in Chapter 2;
- tables and figures announced by numbered captions;
- notes and unsupported structures.

The builder derives ancestry primarily from canonical IBC designations rather than typography alone.

### Recognition

The recognizer should distinguish at least these forms:

- `CHAPTER <number>`;
- `PART <number or Roman numeral>`;
- `SECTION <designation>`;
- decimal provisions such as `1004.1`, `1004.1.1`, or appendix-prefixed equivalents such as `A101.2`;
- optional bracketed committee or adoption designations preceding a provision;
- `Exception:` and `Exceptions:` followed by numbered entries;
- numbered and parenthesized subordinate lists;
- `TABLE <designation>`;
- `FIGURE <designation>`;
- appendix chapter and section designations;
- Chapter 2 definition entries;
- notes, footnotes, and retained unsupported structures.

Recognition must not promote an arbitrary decimal, dimension, date, standard number, or list marker to a section without structural evidence.

### Canonical locators

Canonical structural locators should be publication-specific but deterministic:

- `ibc:2018/chapter:10`;
- `ibc:2018/chapter:10/section:1004`;
- `ibc:2018/chapter:10/section:1004.1`;
- `ibc:2018/chapter:10/section:1004.1/exception:1`;
- `ibc:2018/chapter:10/table:1004.5`;
- `ibc:2018/appendix:A/section:A101.2`.

The locator format should encode printed identity and ownership, not physical block number. Existing block locators remain available through attributes for traceability.

Structural attributes should include, where applicable:

- `ibc_designation`;
- `ibc_parent`;
- `ibc_depth`;
- `structural_role`;
- `source_block_locator`;
- `pdf_pages`;
- any preserved committee or adoption designation.

### Parent resolution

Decimal section ownership is determined by designation prefixes. For example, `1004.1.1` is owned by `1004.1`, which is owned by `1004`. A section may not attach beneath a numerically unrelated open section merely because it follows it in source order.

Parts scope subsequent sections until the next Part or chapter boundary. Parts do not replace decimal ancestry.

Nonstructural prose attaches to the deepest open structural owner unless a stronger ownership rule applies. Stronger rules include:

- an exception belongs to the immediately preceding applicable provision or exception group;
- numbered exception entries belong to the open Exceptions node;
- a table or figure belongs to the provision that announces or immediately precedes it when the designation supports that relationship;
- Chapter 2 definition continuations belong to the active definition entry;
- notes belong to the nearest structurally valid owner and remain typed as notes rather than requirements.

### Enumerations

IBC enumerations are more context-sensitive than decimal sections. A numbered list such as `1.` must not become a publication section. The hierarchy builder should maintain a local enumeration stack beneath the current provision and infer sibling or child relationships from marker form, indentation or layout evidence, and source sequence.

When the evidence cannot distinguish a child list from a new sibling, the node remains source-backed under the nearest safe owner and receives an ambiguity diagnostic. The parser must not invent a deeper locator solely to create a balanced tree.

### Span expansion and source preservation

Every extracted block must be represented exactly once in the hierarchy or as a diagnostic-backed retained node. Structural parent spans expand from their own source start through the end of their last descendant. Child ordering remains source order.

The normalized chapter text and source-map entries remain unchanged. Hierarchy construction reorganizes Document AST ownership but does not rewrite source text.

### Outline reconciliation

A separate, optional outline module may extract the chapter and section sequence from table-of-contents pages or load an independently prepared source-free outline artifact.

It compares, without mutating parser output:

- expected and inferred designations;
- duplicate designations;
- parent designation;
- normalized title;
- depth;
- source order;
- chapter boundary.

The reconciliation report must contain structural metadata and diagnostics only, not proprietary body prose.

## Document AST compatibility

The public `DocumentNodeType` enum already contains Chapter, Section, Subsection, Paragraph, List Item, Definition Entry, Table, Heading, Note, Footnote, and Unsupported. The initial implementation should use these existing neutral types rather than changing Document AST `0.1.0`.

IBC-specific identity and ownership belong in locators and attributes. A later AST version may add explicit exception or figure node types only if multiple publication adapters demonstrate that the generic distinction is necessary.

ChapterSeed advances independently if its serialized private structure changes. The generic Document AST version does not change unless its public contract changes.

Existing consumers that scan flat chapter children should receive a documented preorder traversal helper, matching the compatibility technique used by the NEC hierarchy work. New consumers should traverse the recursive tree directly.

## Failure behavior

- Unknown designations are retained and diagnosed.
- A subsection whose expected parent is missing attaches to the nearest safe chapter or part owner and receives a missing-parent diagnostic.
- Duplicate canonical locators are not collapsed or silently renamed.
- Out-of-order sections remain in source order and receive an order diagnostic.
- A title mismatch against the outline is reported independently from parent or presence mismatches.
- Ambiguous numbered lists remain list items rather than being promoted to sections.
- Unsupported table or figure geometry remains retained as unsupported structure.
- The outline never repairs, inserts, deletes, or reorders production nodes.

## Testing

Synthetic tests should cover:

1. Chapter, Part, Section, and decimal subsection nesting.
2. Sibling resets across decimal depth changes.
3. Missing decimal parents.
4. Duplicate and out-of-order designations.
5. Numbered lists that must not become sections.
6. Nested enumerations with repeated marker classes.
7. Singular and plural exception ownership.
8. Chapter 2 definition continuation ownership.
9. Table and figure attachment.
10. Parent-span expansion and exact source round-tripping.
11. Preorder compatibility for existing consumers.
12. Outline reconciliation mismatch classes.
13. Preservation and diagnostics for ambiguous or unsupported structures.
14. Appendix-prefixed designations.

Private production validation should run on Chapters 1 through 3 at the exact source checksum already used by the bounded IBC pipeline. It should verify zero source loss, unique retained block identity, valid Document AST spans, deterministic output, and a source-free hierarchy conformance summary.

## Implementation boundary

The implementation should be stacked on `agent/ibc-layout-analysis` at exact head `13117253ed3c30c2762bb538bb8bf71b7b723e8b`.

The first implementation slice should add:

- an IBC structural recognizer and hierarchy builder;
- projection integration;
- neutral preorder traversal compatibility;
- synthetic hierarchy tests;
- optional source-free outline reconciliation contracts and tests;
- private Chapters 1 through 3 validation tooling and documentation.

It should not expand the chapter page-range catalog or begin semantic provision interpretation in the same change.
