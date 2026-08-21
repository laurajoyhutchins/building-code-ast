# Source Text IR

`source-text/v1` is the publication-neutral compiler representation between source extraction/layout reconstruction and downstream document/semantic structure.

The representation is deliberately source-expression preserving. Generated bundles containing protected source prose belong in private retained-object storage, not in the public repository. The public repository may contain the schema contract, implementation, synthetic fixtures, hashes, and source-safe verification receipts.

## Compiler boundary

The intended data flow is:

```text
retained source artifact
  -> page/layout observations
  -> normalized canonical text + provenance
  -> source-text/v1
  -> Document AST
  -> reviewed semantic projections
```

A `source-text/v1` bundle owns the canonical UTF-8 text coordinate space for one bounded source projection. It records:

- exact source artifact and edition identity;
- exact source SHA-256 and byte size;
- extractor and projection identity/version;
- canonical text and its deterministic SHA-256;
- ordered fragments mapped to extraction provenance;
- a deterministic locator/document-node index over canonical text ranges;
- explicit diagnostics; and
- a deterministic hash over the complete bundle payload.

The bundle does not determine code applicability or compliance. It also does not replace the retained source artifact as the source of record.

## Persistence and lookup

`SourceTextBundle.save()` writes canonical JSON. `SourceTextBundle.load()` validates source identity fields, canonical text hash, fragment ordering and round-trip text, index ranges/uniqueness, and the complete bundle hash before returning data.

The `building-code-text` entry point is the cheap read path for already-ingested text. `building-code-text get <bundle> <locator>` loads only the persisted Source Text IR and returns exact canonical text plus provenance for that locator. The command does not import the PDF extraction pipeline, reopen a PDF, rebuild hierarchy, or invoke semantic parsing.

## Migration rule

Existing publication-specific ingesters should project their already-normalized intermediate state into this contract rather than creating new extraction systems. NEC 2017 already emits normalized text plus source-map entries. IBC 2018 already emits normalized logical blocks with source fragments. Those existing observations are the migration inputs.

Migration is complete only after retained-source verification establishes that the persisted representation round-trips the bounded NEC and IBC scopes without changing current Document AST or semantic behavior. Retained verification evidence stored in Git must remain source-safe.
