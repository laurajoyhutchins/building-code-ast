# AST and Evidence Compatibility

Document structure, semantic provision ASTs, and source-evidence adapters are versioned independently because they serve different compiler stages and may evolve at different rates.

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

## Jurisdictional amendment patch version 0.2.0

Version `0.2.0` makes amendment payloads exclusive by operation. The `scope` field must be null for `add`, `replace`, `delete`, and `reserve`; only the `scope` operation may carry a scope statement.

Serialized `0.1.0` patches whose non-scope operation carries a non-null `scope` value are invalid under `0.2.0` and must be corrected from source evidence before migration. Their deterministic identities change when the invalid payload is removed.

`AmendmentSet` now requires each `(source_id, sequence)` pair to be unique. Ordering adds deterministic patch identity as the final tie-breaker, making projections independent of input tuple order.

## Washington evidence adapter migration

Post-merge review split two different acquisition contracts that had previously shared the name `WashingtonWacHtmlAdapter`. Later official-corpus validation strengthened direct ingestion against the Washington state site's live HTML layout.

### Direct official ingestion

`WashingtonWacHtmlAdapter` version `0.4.0` identifies the public direct adapter. Construction requires:

- `base_publication_state_id`;
- a nonempty `known_base_locators` frozenset;
- optional `effective_dates_by_wac` and `effective_to_dates_by_wac` mappings;
- optional `effective_dates_by_locator` and `effective_to_dates_by_locator` mappings;
- optional `reserved_locators_by_wac` mappings.

Locator-specific dates override WAC-section dates, which override a source-level publication effective date. It emits only operations that can be classified from citation-led, locator-bearing WAC presentation plus the base-locator oracle: `add`, `replace`, and explicitly mapped `reserve`.

Version `0.4.0` adds scoped extraction of leaf `span` blocks inside `div.section-page`, matching the live Washington site while excluding navigation and breadcrumb text. Paragraph- and list-shaped fixtures remain supported. Output sequence values preserve source candidate ordinals.

Consumers importing the direct adapter from the public package namespace receive `WashingtonOfficialWacHtmlAdapter` under the established `WashingtonWacHtmlAdapter` name.

### Project-normalized directive ingestion

Code written against the former explicit-directive constructor must use `NormalizedWashingtonWacHtmlAdapter` version `0.2.0`:

```python
NormalizedWashingtonWacHtmlAdapter(
    base_publication_state_id=state_id,
    effective_from="2024-03-15",
    effective_to=None,
    known_base_locators=locators,
)
```

This adapter consumes project-normalized directives such as `Section 107.3 is added.` and supports `add`, `replace`, `delete`, `reserve`, and `scope`.

Version `0.2.0` preserves the original normalized section ordinal in output. It also allows whole-number added IBC sections to resolve through their chapter designation and appendix-prefixed sections to resolve through their appendix designation.

There is no silent compatibility shim between direct official HTML and normalized project-authored directives. Failing at construction is preferable to silently running the wrong acquisition contract.

## ICC development adapters

`IccDevelopmentTextAdapter` version `0.2.0` remains the reviewed combined-artifact grammar. It preserves source action ordinals and closes an extractable proposal chain at the first unsupported action. Later actions remain diagnostic-backed unsupported regions instead of being linked across an unknown intermediate action.

Direct official ICC artifacts use separate version `0.1.0` adapters:

- `IccProposalMonographPdfAdapter` for single-part proposal roots;
- `IccCommitteeActionReportPdfAdapter` for proposal-bounded committee-action reports.

`IccCommitteeActionPdfAdapter` is a public compatibility alias for `IccCommitteeActionReportPdfAdapter`.

The action adapter requires an affected-locator mapping derived from the registered proposal artifact. Multipart proposal headings fail closed until a part-aware lineage identity is introduced.

`DevelopmentLineage` requires every same-proposal parent sequence to precede its child sequence. Existing records with backward parentage must be corrected from the source process record; they are not automatically reordered.

The serialized development-record contract remains `0.1.0` because its shape is unchanged.

## ICC errata adapter version 0.3.0

`IccErrataPdfAdapter` version `0.3.0` uses each source candidate's ordinal as the emitted record sequence. Unsupported candidates therefore leave intentional gaps rather than causing later records to be renumbered.

Version `0.2.0` previously expanded the bounded grammar to official comma-form and period-form page headers and recognized deletion, renumbering, and relocation directives. Version `0.3.0` retains that grammar and changes only candidate-sequence provenance.

The serialized erratum-record contract remains `0.1.0`; the record shape is unchanged.

## Official-corpus validation

The August 2, 2026 source-free validation receipt is [`docs/validation/official-evidence-2026-08-02.json`](validation/official-evidence-2026-08-02.json). It records exact source digests, adapter versions, bounded record and diagnostic counts, deterministic projection digests, and repeat-run results without embedding source text.
