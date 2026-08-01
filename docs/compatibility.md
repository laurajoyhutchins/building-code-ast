# AST Compatibility

Document structure and semantic provision ASTs are versioned independently because they serve different compiler stages and may evolve at different rates.

## Document AST version 0.1.0

Version `0.1.0` introduces the publication-structure contract:

- exact original `source_text`;
- `source_artifact.artifact_id` and `source_artifact.edition_id`;
- recursive structural nodes with deterministic `docnode:<sha256>` identities;
- exact source spans on every node;
- document, chapter, section, subsection, paragraph, list item, definition entry, table, heading, note, footnote, and unsupported node types;
- document-level diagnostics;
- strict runtime deserialization and provenance validation.

This is a separate contract and does not replace or wrap the provision AST. Consumers should choose the representation that matches their compiler stage.

## Provision AST version 0.3.0

Version `0.3.0` replaces the flat `conditions` array with a required nullable `condition` expression.

A provision condition is now one of:

- a comparison object;
- an `all_of` logical group;
- an `any_of` logical group;
- `null` when no supported structured condition was recognized.

Logical groups contain at least two recursive operands and preserve source order. Runtime validation requires exact source-span round-tripping, comparison evidence equality, group containment, strict operand ordering, non-overlap, exact group boundaries, and an acyclic active recursion path.

The deterministic parser emits logical groups only for homogeneous chains in which every segment matches the existing numeric comparison grammar. Parenthesized grouping, mixed `and` and `or` connectors, and malformed clauses remain explicit diagnostics and produce no partial condition expression.

### Migration from provision AST 0.2.0

Migration is deterministic only in these cases:

- zero `conditions` values become `condition: null`;
- one `conditions` value becomes that comparison object as `condition`.

More than one `conditions` value cannot be migrated safely because version `0.2.0` did not record whether the comparisons were conjunctive or disjunctive. Consumers must reparse the original source or obtain human review rather than inventing a connector.

The project does not provide an automatic migration utility for this boundary.

## Provision AST version 0.2.0

Version `0.2.0` replaced the initial `0.1.0` draft contract before its first release.

The provision object:

- preserved the exact original `source_text`, including leading and trailing whitespace;
- required `source_artifact.artifact_id` and `source_artifact.provision_locator`;
- included `modality_span` for recognized modalities;
- included `subject_span` for non-empty regulated subjects;
- represented conditions as a flat comparison array;
- validated all spans against the exact original source text.

Consumers of the provision `0.1.0` draft had to update their schema and runtime models before reading `0.2.0` output. The project did not provide an automatic migration because provision `0.1.0` did not retain enough information to reconstruct source identity or offsets removed by input trimming.

The `inline` provision source identity defaults are intended for interactive CLI use and tests. Durable ingestion pipelines should provide stable identifiers for the source artifact or edition and the provision's location within it.
