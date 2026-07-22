# AST Compatibility

## Version 0.2.0

Version 0.2.0 replaces the initial 0.1.0 draft contract before its first release.

The provision object now:

- preserves the exact original `source_text`, including leading and trailing whitespace;
- requires `source_artifact.artifact_id` and `source_artifact.provision_locator`;
- includes `modality_span` for recognized modalities;
- includes `subject_span` for non-empty regulated subjects;
- validates all spans against the exact original source text.

Consumers of the 0.1.0 draft must update their schema and runtime models before reading 0.2.0 output. The project does not provide an automatic migration because 0.1.0 did not retain enough information to reconstruct source identity or offsets removed by input trimming.

The `inline` source identity defaults are intended for interactive CLI use and tests. Durable ingestion pipelines should provide stable identifiers for the source artifact or edition and the provision's location within it.
