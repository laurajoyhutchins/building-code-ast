# Source Evidence Scaffolding Design

## Status

Approved for implementation by the owner's request to set up the scaffolding after the IBC source-strategy and agent-team review.

## Objective

Add a publication-neutral evidence boundary that can register exact source artifacts, distinguish their evidentiary roles, identify printing and correction state, and execute future source adapters without weakening provenance or corpus-policy constraints.

The first consumers are expected to be IBC errata, ICC code-development records, and Washington amendments. The contract must also be reusable by the NEC change-history work without forcing the NEC-specific development model into a generic shape.

## Scope

This slice adds:

- a versioned source-register contract;
- explicit AST source identity and publication-state metadata;
- evidence-role, access-scope, and rights-status classifications;
- deterministic publication-state identity;
- strict JSON-compatible deserialization and validation;
- a typed adapter protocol and guarded adapter runner;
- source digest verification before adapter execution;
- source-region diagnostics for pages, anchors, and PDF bounding boxes;
- JSON Schema, source-free tests, and reference documentation.

## Non-goals

This slice does not:

- download, scrape, or parse ICC, Washington, Florida, California, or NYC material;
- store model-code text, commentary, page images, or licensed source artifacts;
- define IBC erratum, proposal, amendment, interpretation, or referenced-standard records;
- replace the NEC-specific change-history model;
- apply amendments, reconcile editions, or produce compliance conclusions;
- add third-party runtime dependencies.

## Package boundary

The new public subpackage is `building_code_ast.evidence`.

```text
src/building_code_ast/evidence/
  __init__.py       stable public exports for the evidence layer
  model.py          immutable source-register and publication-state values
  io.py             strict JSON-compatible deserialization
  adapters.py       adapter protocol, result envelope, and guarded runner
```

The root `building_code_ast` package will not re-export the new contract in this slice. Consumers opt into the evidence layer explicitly, reducing accidental coupling while the contract is pre-1.0.

## Source register

`SourceRegister` is independently versioned as `0.1.0` and contains unique `SourceRegisterEntry` values.

Each entry records:

- `source_id`: stable register identity;
- `ast_source`: the exact `artifact_id` and `edition_id` used by AST products;
- `title` and `issuing_body`;
- one primary `evidence_role`;
- `publication`: publication family, edition, printing, digital revision, correction set, publication date, and effective date;
- `retrieved_at`, lowercase SHA-256, and media type;
- `access_scope` and `rights_status`;
- optional public source URL, jurisdiction, and rights note.

The role is singular on purpose. When one artifact genuinely serves several roles, downstream records may cite it in several contexts, but the register does not blur normative text, correction, development history, enacted law, guidance, interpretation, commentary, and secondary analysis into one classification.

## Publication identity

`PublicationIdentity.state_id` is a deterministic `publication:<sha256>` value derived from canonical JSON containing all publication-state fields. Reprocessing the same state preserves identity. Changing a printing, digital revision, correction set, or effective date changes identity even when the nominal edition remains the same.

The state identity supplements rather than replaces existing AST `artifact_id` and `edition_id` fields. Existing local ingestion outputs therefore remain valid.

## Rights and source boundary

The register distinguishes access from publication basis:

- access describes how the artifact was obtained or must be held;
- rights status records the project's publication basis or restriction classification.

Licensed, private, authenticated, or uncertain-restricted entries require a nonempty rights note. The source bytes remain outside Git. Public serialization contains metadata, checksums, locators, and project-authored summaries only.

## Adapter contract

An `EvidenceAdapter[T]` declares:

- `adapter_id` and `adapter_version`;
- supported evidence roles;
- supported media types;
- `extract(source, content) -> AdapterResult[T]`.

`run_evidence_adapter` verifies before extraction that:

1. adapter identity and version are nonempty;
2. the source role and media type are supported;
3. the supplied bytes match the registered SHA-256;
4. the returned envelope repeats the exact source ID, adapter ID, and adapter version.

An adapter result preserves typed records, diagnostics, and unsupported source regions. The scaffold deliberately leaves record types generic so each future adapter can emit a closed source-family-specific model.

## Failure behavior

The layer fails closed for:

- unknown JSON fields;
- unsupported enum values;
- malformed dates or timestamps;
- invalid digests;
- duplicate source IDs;
- empty required values;
- invalid page numbers or bounding boxes;
- missing rights notes for restricted material;
- adapter/source incompatibility;
- source-byte digest mismatch;
- result-envelope identity mismatch.

No failure path repairs metadata, guesses publication state, or invokes an adapter after digest verification fails.

## Interaction with current work

The NEC expected-changelog branch may later map its `SourceManifestEntry` values into this register or adopt the shared values in a separate migration. This scaffold does not modify that open branch or make its merge contingent on a cross-branch refactor.

The open IBC ingestion and hierarchy branches continue to produce `DocumentAst` and private source-bound seeds. Later IBC evidence adapters will cite those AST source identities through `AstSourceIdentity` and will emit their own typed erratum, development-event, and amendment records.

## Verification

Source-free unit tests will prove:

- register round-trip serialization;
- deterministic and printing-sensitive publication-state identity;
- strict unknown-field rejection;
- duplicate source-ID rejection;
- restricted-source rights-note enforcement;
- source-region validation;
- digest verification before adapter invocation;
- role and media-type compatibility checks;
- result-envelope identity validation;
- schema and runtime enum/version alignment.

The repository-wide unit suite and source compilation remain the final exact-head verification gates.
