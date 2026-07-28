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

This is a new contract and does not replace or wrap provision AST `0.2.0`. Consumers should choose the representation that matches their compiler stage.

## Provision AST version 0.2.0

Version `0.2.0` replaces the initial `0.1.0` draft contract before its first release.

The provision object:

- preserves the exact original `source_text`, including leading and trailing whitespace;
- requires `source_artifact.artifact_id` and `source_artifact.provision_locator`;
- includes `modality_span` for recognized modalities;
- includes `subject_span` for non-empty regulated subjects;
- validates all spans against the exact original source text.

Consumers of the provision `0.1.0` draft must update their schema and runtime models before reading `0.2.0` output. The project does not provide an automatic migration because provision `0.1.0` did not retain enough information to reconstruct source identity or offsets removed by input trimming.

The `inline` provision source identity defaults are intended for interactive CLI use and tests. Durable ingestion pipelines should provide stable identifiers for the source artifact or edition and the provision's location within it.
