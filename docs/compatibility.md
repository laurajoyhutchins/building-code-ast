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

## Washington evidence adapter migration

Post-merge review split two different acquisition contracts that had previously shared the name `WashingtonWacHtmlAdapter`.

### Direct official-style ingestion

`WashingtonWacHtmlAdapter` now identifies the direct, bounded official-style adapter. Its adapter version is `0.2.0`. Construction requires:

- `base_publication_state_id`;
- a nonempty `known_base_locators` frozenset;
- optional `effective_dates_by_wac` and `effective_to_dates_by_wac` mappings;
- optional `reserved_locators_by_wac` mappings.

It emits only operations that can be classified from citation-led, locator-bearing WAC presentation plus the base-locator oracle: `add`, `replace`, and explicitly mapped `reserve`.

### Project-normalized directive ingestion

Code written against the former explicit-directive constructor must migrate to `NormalizedWashingtonWacHtmlAdapter`. Its adapter version is `0.1.0`, and it retains the prior constructor shape:

```python
NormalizedWashingtonWacHtmlAdapter(
    base_publication_state_id=state_id,
    effective_from="2024-03-15",
    effective_to=None,
    known_base_locators=locators,
)
```

This adapter consumes project-normalized directives such as `Section 107.3 is added.` and supports `add`, `replace`, `delete`, `reserve`, and `scope`.

There is no silent compatibility shim. The old class name implied direct official WAC ingestion while its grammar required normalized project-authored markup. Failing at construction is preferable to silently running the wrong acquisition contract.

## ICC errata adapter version 0.2.0

`IccErrataPdfAdapter` version `0.2.0` expands the bounded grammar to official comma-form and period-form page headers and recognizes deletion, renumbering, and relocation directives. Record schema version remains `0.1.0`; the serialized record shape is unchanged, but delete records now strictly require `replacement_text: null`.
