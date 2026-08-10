# Document AST Reference

## Contract version

The document structure AST is versioned independently as `0.1.0`. Its JSON Schema is [`schemas/document-ast.schema.json`](../../schemas/document-ast.schema.json).

## Top-level object

A document AST contains:

- `ast_version`: exactly `0.1.0`;
- `type`: exactly `document_tree`;
- `source_text`: the exact original source string;
- `source_artifact`: artifact, edition, optional publication-component identity, and optional publication-state binding;
- `root`: the recursive publication-structure node;
- `diagnostics`: document-structure diagnostics with optional exact source spans.

`source_artifact.artifact_id` identifies the durable source artifact consumed by the AST. `source_artifact.edition_id` identifies the edition, release, or snapshot being represented. `source_artifact.publication_component_id`, when present, distinguishes separately modeled publications or components that share one physical artifact. `source_artifact.publication_state_id`, when known, binds the AST directly to the deterministic `publication:<sha256>` identity registered by the source-evidence layer.

The publication-state binding is provenance, not a replacement for exact artifact identity. Multiple source artifacts may evidence the same issued publication state, and one source artifact may contain multiple explicitly identified publication components.

## Structural nodes

Every node contains:

- `node_id`: deterministic `docnode:<sha256>` identity;
- `type`: one supported publication-structure node type;
- `locator`: a stable structural locator within the edition;
- `span`: exact start, end, and source text;
- `label`: an optional publication label or heading;
- `attributes`: string-valued structural metadata;
- `children`: nested structural nodes.

Supported node types are:

- `document`;
- `chapter`;
- `section`;
- `subsection`;
- `paragraph`;
- `list_item`;
- `definition_entry`;
- `table`;
- `table_heading`;
- `table_column`;
- `table_row`;
- `table_cell`;
- `heading`;
- `note`;
- `footnote`;
- `unsupported`.

`unsupported` preserves source structure that has not been normalized into a more specific node type. It should be paired with an explanatory diagnostic when produced by a parser.

## Deterministic identity

The node ID input is canonical JSON with sorted keys and compact separators:

```json
{
  "artifact_id": "...",
  "edition_id": "...",
  "locator": "...",
  "node_type": "..."
}
```

When a publication component is present, `publication_component_id` is also an identity input. The UTF-8 bytes of that canonical JSON are hashed with SHA-256. The lowercase hexadecimal digest is prefixed with `docnode:`.

Source text, offsets, and `publication_state_id` are not node-identity inputs. Binding an existing AST source to its publication state therefore does not renumber its structural nodes. Reprocessing the same artifact, edition, component, and locator retains the same node ID even when parser implementation or publication-state metadata changes.

Cross-edition continuity is a relationship between distinct nodes, not node-ID reuse. A later compiler stage may record explicit predecessor/successor or equivalent lineage edges, but a node from a new edition or exact source artifact receives the identity warranted by that source state.

## Validation invariants

Runtime validation requires:

- non-empty source, artifact ID, edition ID, and locators;
- a root node of type `document`;
- a root span that covers the exact original source;
- every node and diagnostic span to round-trip to `source_text`;
- every child span to remain within its parent span;
- every locator and node ID to be unique;
- every node ID to match the deterministic identity function;
- every attribute name and value to be a string;
- any supplied `publication_state_id` to match the deterministic publication-state identifier shape.

Table columns may overlap row and cell spans because columns are cross-cutting structural identities anchored to their source headings. Containment, not sibling non-overlap, is the required tree invariant.

## Representation boundary

The document AST records publication structure only. It does not represent:

- modality;
- applicability or conditions;
- actions or exceptions;
- definition resolution;
- amendments;
- jurisdiction adoption or effective-code selection;
- compliance conclusions;
- professional or authority interpretation.

Those concerns belong to later compiler stages. Keeping the document tree separate allows semantic parsers, amendment projections, and jurisdiction-aware selection to be replaced or reviewed without erasing the publication structure or source evidence.
