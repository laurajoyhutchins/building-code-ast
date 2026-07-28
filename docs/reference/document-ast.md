# Document AST Reference

## Contract version

The document structure AST is versioned independently as `0.1.0`. Its JSON Schema is [`schemas/document-ast.schema.json`](../../schemas/document-ast.schema.json).

## Top-level object

A document AST contains:

- `ast_version`: exactly `0.1.0`;
- `type`: exactly `document_tree`;
- `source_text`: the exact original source string;
- `source_artifact`: artifact and edition identity;
- `root`: the recursive publication-structure node;
- `diagnostics`: document-structure diagnostics with optional exact source spans.

`source_artifact.artifact_id` identifies the publication family or durable source artifact. `source_artifact.edition_id` identifies the exact edition, release, or snapshot being represented.

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

The UTF-8 bytes of that canonical JSON are hashed with SHA-256. The lowercase hexadecimal digest is prefixed with `docnode:`.

Source text and offsets are not identity inputs. Reprocessing the same edition and locator therefore retains the same node ID even when a parser implementation changes. A corrected publication snapshot should receive a new `edition_id`.

## Validation invariants

Runtime validation requires:

- non-empty source, artifact ID, edition ID, and locators;
- a root node of type `document`;
- a root span that covers the exact original source;
- every node and diagnostic span to round-trip to `source_text`;
- every child span to remain within its parent span;
- every locator and node ID to be unique;
- every node ID to match the deterministic identity function;
- every attribute name and value to be a string.

Table columns may overlap row and cell spans because columns are cross-cutting structural identities anchored to their source headings. Containment, not sibling non-overlap, is the required tree invariant.

## Representation boundary

The document AST records publication structure only. It does not represent:

- modality;
- applicability or conditions;
- actions or exceptions;
- definition resolution;
- amendments;
- compliance conclusions;
- professional or authority interpretation.

Those concerns belong to later compiler stages. Keeping the document tree separate allows semantic parsers to be replaced or reviewed without erasing the publication structure or source evidence.
