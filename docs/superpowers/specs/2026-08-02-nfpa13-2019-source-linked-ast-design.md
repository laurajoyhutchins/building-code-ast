# NFPA 13 (2019) Source-Linked AST Design

## Objective

Extend the local-only NFPA 13 hierarchy extractor into a deterministic compiler pipeline that converts the owner-supplied 2019 PDF into a source-linked document AST, block syntax tree, reference graph, and bounded semantic annotations without committing licensed source text or generated bulk output.

## Scope

The implementation processes the NFPA 13 portion of the supplied compilation, beginning at Chapter 1 and ending at Annex F. It preserves all extracted source text in local output only. Repository changes contain parser code, synthetic fixtures, tests, schemas for the local bundle, and validation logic.

The implementation does not decide compliance, resolve discretionary terms, infer missing language, or publish the source PDF, clause bodies, tables, figures, or generated full-document AST.

## Architecture

The existing hierarchy extractor remains the structural authority for chapter, annex, and numbered-clause identity. A new AST extractor consumes that hierarchy and the PDF layout in four deterministic stages:

1. **Source stream**: normalize PDF reading order into page/column-aware lines with exact canonical text offsets and physical provenance.
2. **Document AST**: compute hierarchical structural spans, assign direct text to paragraph/list/note/definition/table/figure/unsupported nodes, and preserve deterministic locators.
3. **Reference graph**: identify internal clause, chapter, table, figure, and external-standard references; resolve only exact internal targets.
4. **Semantic annotations**: classify source-backed modalities and bounded syntactic roles without altering the document AST or claiming reviewed interpretation.

The output is a local bundle with a versioned envelope:

```text
nfpa13-ast-bundle/0.1.0
  source metadata
  document_ast
  relations
  semantic_annotations
  diagnostics
  validation
  statistics
```

## Source Stream

Each accepted PDF line records:

- canonical text and start/end offsets in the generated `source_text`;
- PDF page, printed page, column, and bounding box;
- font names and sizes;
- font names and sizes used by deterministic artifact and block classification.

Headers, footers, page numbers, and isolated italic revision markers are excluded. Source text is joined with newline separators. Every retained character is owned by exactly one leaf block, while structural nodes may span descendants.

## Structural Spans

Numbered-clause anchors come from the existing hierarchy. The span for an anchored structural node begins at its source anchor and ends immediately before the next explicit anchor outside that node's actual hierarchy subtree. This ancestry rule is necessary for sparse Annex A material, where omitted intermediate headings make depth-only termination incorrect. Chapter and annex spans begin at their printed heading and end before the next container.

Implicit Annex A containers resolve only after all direct descendants have ranges, then derive their span from the full descendant extent. A structural node's direct text is the part of its span not occupied by immediate structural children. Those direct intervals are parsed into block nodes.

## Block Syntax

The block parser emits the existing document node vocabulary where possible:

- `paragraph`
- `list_item`
- `definition_entry`
- `table`, `table_heading`, `table_row`, `table_cell`
- `heading`
- `note`
- `footnote`
- `unsupported`

Figures, equations, and unresolved layout objects are represented as `unsupported` nodes with a `kind` attribute. Figure captions remain exact source-backed children.

Nested list items are recognized from markers such as `(1)`, `(a)`, and `(i)`, indentation, and continuation lines. A marker attached to a numbered locator, such as `20.15.2.1(2)`, is treated as the corresponding list-item continuation rather than a new clause.

Chapter 3 definition clauses are emitted as `definition_entry` blocks when their direct text contains the definition label and body. Notes and exceptions retain their own block identity.

## Tables and Figures

Bold source-backed table captions define conservative page or column clips. Lines inside an accepted clip are grouped into geometry-derived rows and cells without invoking a probabilistic or expensive table solver. Accepted tables receive deterministic `table_heading`, `table_row`, and `table_cell` nodes whose leaf spans point to the exact canonical source lines. Captions that do not produce an accepted geometry-backed table remain source-backed `table_heading` nodes and receive diagnostics rather than guessed rows or cells.

Figure captions are recognized from printed `FIGURE` labels. The caption is preserved as a source-backed `unsupported` child with `kind=figure`; image pixels and diagram semantics are not interpreted.

## References and Relations

The reference pass recognizes:

- numbered clauses and sections;
- chapters;
- table locators;
- figure locators;
- NFPA and other external publication identifiers.

Relations record the source node, exact evidence span, relation type, target locator when resolved, and resolution state. Annex A `explains` relations remain deterministic. Bare numbers are not treated as clause references without a qualifying context or an exact hierarchy match with punctuation boundaries.

## Semantic Annotations

Semantic annotations are independent projections over leaf blocks. They preserve the exact evidence span and may include:

- `requirement`
- `prohibition`
- `permission`
- `recommendation`
- `definition`
- `scope`
- `exception`
- `condition`
- `alternative`
- `applicability`
- `calculation`
- `informative`

Modal recognition covers `shall`, `shall not`, `must`, `must not`, `may`, `may not`, `should`, and passive `is/are required` or `is/are permitted` forms. The projection does not infer a compliance result. Unsupported figure interpretation, unresolved references, and table captions without accepted geometry receive evidence-linked diagnostics and remain fully visible. Other graphical text remains explicit `unsupported` syntax rather than fabricated semantics.

## Validation

A run fails unless:

- hierarchy validation passes;
- every explicit clause has a valid source anchor;
- all node IDs are deterministic and locators unique;
- every node span round-trips to `source_text`;
- every child span is contained by its parent;
- retained source characters are covered exactly once by leaf blocks, excluding deliberate newline separators;
- relation, semantic-annotation, and diagnostic evidence spans round-trip exactly;
- internal resolved references identify existing nodes or declared table/figure aliases;
- Annex A correspondence remains complete;
- no isolated revision markers, headers, or footers enter clause bodies;
- output serialization is deterministic across repeated runs.

The CLI writes a Markdown validation report and optional PDF overlay pages showing structural and block boundaries for source review.

## Error Handling

The extractor fails closed on duplicate anchors, missing structural parents, invalid spans, non-deterministic output, or source-hash mismatch when an expected hash is supplied. Unsupported table geometry, figures, equations, and ambiguous list nesting produce diagnostics rather than fabricated structure.

## Testing

Synthetic tests cover reading order, hierarchical span computation, direct-text subtraction, nested lists, clause-attached list markers, notes, exceptions, definitions, table acceptance, figure captions, internal references, semantic modality classification, deterministic serialization, and validation failures.

A source-specific local verification run processes the complete owner-supplied PDF, validates the resulting bundle, runs a second extraction to compare deterministic hashes, and renders representative overlays from Chapters 1, 20, 21, Annex A, Annex C, and Annex F.

## Publication Boundary

Only code, tests, synthetic fixtures, design documentation, and aggregate validation statistics are suitable for the public repository. The PDF, canonical source text, full AST bundle, table contents, figure contents, and overlays remain local artifacts.
