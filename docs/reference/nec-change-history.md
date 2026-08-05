# NEC change-history contract

The NEC change-history contract represents development evidence, expected edition changes, independently observed AST changes, and their reconciliation.

The **issued 2020 NEC is the controlling text** for the 2020 edition. Development records support an expected-change oracle; they are not substituted for the issued text.

## Contract version

Current dataset version: `0.1.0`.

The JSON Schema is [`schemas/nec-change-history.schema.json`](../../schemas/nec-change-history.schema.json).

## Dataset layers

### Sources

`SourceManifestEntry` identifies a privately retained development artifact by stable ID and SHA-256 digest. It records retrieval and media metadata but contains no extracted source prose.

Required fields:

- `source_id`;
- `document_type`;
- `title`;
- `cycle`;
- `source_url`;
- `retrieved_at`;
- `sha256`;
- `media_type`;
- `access_scope`;
- nullable `panel` and `page_count`.

### Development records

`DevelopmentRecord` is the normalized process evidence used to derive expectations. Each record includes a project-authored summary, affected-reference strings, structural change classifications, procedural disposition, related-record IDs, and a `SourceLocator`.

Development records are private inputs to the builder and are intentionally absent from the generated public projection. The generated dataset retains source manifests and the record IDs that support each expectation.

### Expected changes

`ExpectedChange` records the controlling procedural result for one `change_chain_id`.

Important fields:

- `from_locators`: references resolved against the supplied 2017 hierarchy;
- `expected_target_references`: expected 2020 locations or unresolved target labels;
- `unresolved_references`: controlling affected references the resolver could not map;
- `change_types`: expected structural changes;
- `disposition`: `change_expected`, `no_change_expected`, or `uncertain`;
- `confidence`: `high`, `medium`, or `low`;
- `controlling_record_id`;
- `supporting_record_ids`.

A negative expectation uses `no_final_change` as its change type. This records that a proposed change should not appear in the issued edition; it does not assert that the provision's text is byte-identical for unrelated reasons.

### Observed changes

`ObservedChange` represents lineage generated from independent 2017 and 2020 ASTs. It contains source and target locators, structural classifications, a project-authored summary, and alignment confidence.

The expected dataset must not be an input to the 2020 parser or AST alignment rules. This independence is necessary for the expected layer to function as a test oracle.

### Reconciliation

`Reconciliation` compares one expectation with zero or more observed changes.

Outcomes:

- `confirmed`: the observed result agrees with the expectation;
- `expected_not_observed`: a positive expectation has no aligned observed change;
- `contradicted`: a change appears where the controlling record predicts no final change;
- `ambiguous`: locators align but classifications differ, or procedural finality is uncertain;
- `unexpected_observed`: an observed change has no matching expectation.

Reconciliation is a review queue, not an interpretation of electrical requirements.

## Procedural projection

Records are grouped by `change_chain_id`. The highest available stage controls:

1. erratum;
2. TIA;
3. Standards Council action;
4. Technical Meeting action;
5. Second Revision;
6. Public Comment;
7. First Revision;
8. Public Input.

If multiple records occupy the controlling stage, they must agree on disposition, affected references, expected targets, and change classifications. Conflicts fail closed.

Disposition mapping:

| Development disposition | Expected disposition |
|---|---|
| accepted, accepted in principle, accepted in part, issued, corrected | change expected |
| rejected, withdrawn, failed ballot, returned to prior edition | no change expected |
| proposed | uncertain |

## Reference resolution

Version `0.1.0` resolves exact canonical NEC locators and explicit sibling ranges. Resolution is performed only against the supplied 2017 locator set.

Supported examples:

```text
210.8
Section 210.8(F)
210.8(A)(1) through (5)
```

Unsupported references remain unresolved, including table names, figures, positional exceptions, and phrases such as “the second paragraph.” The resolver never guesses the nearest provision.

## Change classifications

Supported classifications are:

```text
add
add_subdivision
delete
modify_text
move
renumber
split
merge
restructure
change_heading
change_definition
change_table
change_exception
change_cross_reference
editorial_only
no_final_change
unknown
```

These classifications describe document structure and lineage. They do not claim code applicability, safety effect, or legal interpretation.

## Source and publication boundary

The implementation and schema are source-safe. They have no fields for proposal text, replacement text, committee statements, or source text.

Private acquisition work may use authorized NFPA development records and edition files. Keep those artifacts, extraction intermediates, authenticated exports, and generated text-bearing data outside public Git.

Publicly reviewable material should be limited to project-authored software, schemas, synthetic fixtures, classifications, record identifiers, source locators, and short project-authored summaries.
