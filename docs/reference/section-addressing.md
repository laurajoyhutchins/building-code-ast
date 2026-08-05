# Section addressing contract

## Purpose

Building Code AST uses the code publication's own hierarchy as its primary coordinate system. Engineers navigate and cite sections, subsections, tables, figures, exceptions, definitions, and equations. PDF pagination is a property of one source artifact, not the durable identity of a code provision.

A canonical code address combines publication, edition, structural kind, locator, and any necessary qualifier. Examples include:

- `IBC-2018 §1604.5`
- `IBC-2018 §1604.5.1`
- `IBC-2018 Table 1604.5`
- `IBC-2018 Figure 1604.5`
- `IBC-2018 §1604.5 Exception 2`
- `IBC-2018 §202 Definition "APPROVED"`

The machine representation keeps these components separate even when a display string is also provided.

## Authority and layer boundary

Section addresses are authoritative for normalized navigation, citations, relationships, ordering, APIs, and downstream projections. They are also the starting point for edition comparison.

PDF page numbers, printed-page labels, text offsets, bounding boxes, and raw block numbers remain secondary provenance. They locate evidence inside an exact artifact and support extraction debugging, reproducibility, and human review. They must not become a normalized provision identity, a user-facing navigation fallback, or an edition-comparison key.

Raw page-evidence nodes may temporarily use locators such as `page/328/block/14` because no code structure has yet been established. That locator belongs to the raw evidence layer. A normalized record must either resolve to a structural code address or remain explicitly unresolved.

## Required behavior

1. Prefer the most specific published structural locator supported by evidence.
2. Preserve entity kind. A table, figure, exception, definition, or equation is not silently collapsed into its containing section.
3. Preserve context separately where needed, such as the section containing a table.
4. Never derive a structural address from PDF or printed pagination.
5. Never use page movement as evidence of a code change.
6. Sort navigation in code order, not lexical string order or page order.
7. Keep unresolved records visible rather than assigning plausible page-derived addresses.
8. Resolve record references back to source inventories when page-level evidence is needed.

## Edition comparison

Edition comparison operates on independent structural addresses and explicit relationships such as unchanged, renumbered, moved, split, merged, added, removed, or substantively changed. Page movement is ignored unless the task is specifically about source-artifact layout or extraction behavior.

A renumbering map is an interpretation backed by evidence. Similar text, nearby pages, or parser output alone must not silently establish cross-edition equivalence.

## Section-first projection

`building_code_ast.section_index.build_section_index` creates a navigation projection over normalized inventory records. The projection contains code addresses and stable record references. It deliberately omits page anchors. Records that lack a structural locator are emitted in `unresolved_record_refs`.

Source inventories continue to retain page anchors. This separation keeps the code hierarchy clean while preserving an audit trail to the exact PDF artifact.
