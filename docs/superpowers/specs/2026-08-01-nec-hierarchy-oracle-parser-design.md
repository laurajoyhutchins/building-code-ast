# NEC hierarchy oracle parser design

**Status:** Approved for implementation

## Problem

The NEC 2017 PDF ingestion layer preserves text, block order, page coordinates, and coarse node kinds, but it currently appends every extracted block directly beneath the Article node. That loses the document's real hierarchy and weakens downstream section review, note attachment, exception ownership, and structural diagnostics.

A separately prepared NEC 2017 hierarchy already exists in `laurajoyhutchins/junk-drawer`. It contains canonical clause locators, titles, parent relationships, and order. That work should be used as a development and validation oracle, not copied into production output or required at runtime.

## Goals

1. Infer NEC hierarchy from extracted PDF text and source order.
2. Produce canonical full locators for sections and nested clause markers.
3. Nest Part, Section, subsection, list-item, note, exception, and paragraph nodes under their inferred owners.
4. Expand structural-node spans so every parent covers its descendants exactly.
5. Compare inferred structure with a locally supplied clause oracle.
6. Report missing, unexpected, duplicate, parent, title, depth, and order mismatches.
7. Preserve all source text and provenance when structure is uncertain.
8. Keep the public repository source-free and keep the oracle out of production dependencies.

## Non-goals

- Shipping the junk-drawer hierarchy inside this repository.
- Requiring the oracle when users ingest another NEC edition.
- Claiming legal interpretation or code compliance.
- Reconstructing table cells or diagram geometry in this slice.
- Silently forcing parser output to match the oracle.

## Architecture

### Production path

`PdfLayoutDocument` remains the source of text, page, block, and bounding-box evidence. Classification identifies Article anchors, Parts, Sections, parenthesized subdivisions, definitions, notes, exceptions, unsupported visual structures, and prose.

A new hierarchy builder consumes classified nodes in source order. It maintains an open structural stack:

- Article
- optional Part
- Section
- uppercase subdivision such as `(A)`
- numeric subdivision such as `(1)`
- lowercase subdivision such as `(a)`
- repeated deeper numeric/lowercase levels when supported by context

The builder derives full locators such as `110.26(A)(1)`, attaches nonstructural nodes to the deepest open owner, and emits a diagnostic rather than guessing when marker depth or identity is ambiguous.

Structural nodes receive canonical document locators of the form `nec:<clause-locator>`. Their `nec_locator`, `nec_parent`, `nec_depth`, and structural role are also recorded as attributes. Block-level nodes retain their existing source-block locators.

### Oracle path

A separate conformance module loads the existing `clause_id,clause_title,parent` CSV shape from a local path or text stream. It flattens inferred structural nodes and compares:

- canonical locator presence;
- parent locator;
- normalized title;
- structural depth;
- source order;
- duplicate locator identity.

The result is a versioned JSON-serializable report. It contains structural metadata and diagnostics, not NEC source prose.

The oracle is used only by tests, local evaluation, and parser development. Production ingestion never imports from junk-drawer and never repairs output from the expected hierarchy.

## Compatibility

The Article node locator remains `article:<number>`. Existing semantic consumers receive a preorder-flattened view of nested Article children, preserving their section-scanning behavior while allowing the publication AST itself to become hierarchical.

Canonical structural locators replace block locators only for inferred structural nodes. Source spans, source-map entries, and original block provenance remain unchanged.

## Failure behavior

- Unknown or contextually impossible markers are preserved as source-backed nodes and receive diagnostics.
- Duplicate inferred locators are not collapsed.
- Missing oracle records do not mutate parser output.
- Title disagreement is reported independently from parent disagreement.
- Unsupported tables and diagrams continue to be retained as unsupported nodes.

## Verification

Synthetic fixtures cover nesting, sibling resets, repeated marker classes, Part ownership, note and exception attachment, parent-span expansion, preorder semantic compatibility, oracle loading, and each mismatch class.

A local full-corpus command can compare private ArticleSeed output with the junk-drawer clause CSV and emit a conformance report without publishing the source corpus.