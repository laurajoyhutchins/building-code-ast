# Build the NEC 2020 expected changelog

Use this workflow to turn privately acquired NFPA development records into a source-safe expected 2017-to-2020 NEC changelog.

The **issued 2020 NEC is the controlling text**. Development records explain proposals and procedural outcomes; they do not replace the issued edition. The generated expectations become an independent verification oracle for a later 2020 parser run.

## Inputs

Prepare one private JSON bundle containing:

- the canonical 2017 NEC locators available to the resolver;
- a content-addressed manifest for each development-record source;
- normalized development records with project-authored summaries;
- optional observed changes generated independently from the 2017 and 2020 ASTs.

Keep the bundle, downloaded reports, authenticated exports, PDFs, page images, and text-bearing working files outside public Git.

## Acquire and identify sources

For each First Draft Report, Second Draft Report, committee attachment, Technical Meeting record, Standards Council decision, TIA, or erratum:

1. Retrieve it through an authorized workflow.
2. Record the retrieval URL and timestamp.
3. Calculate its SHA-256 digest without changing the bytes.
4. Assign a stable `source_id`.
5. Record the document type, development cycle, panel, media type, page count, and access scope.
6. Store the original artifact privately.

Example manifest entry:

```json
{
  "source_id": "nfpa70-2020-cmp02-second-draft",
  "document_type": "second_draft_report",
  "title": "NEC 2020 CMP-02 Second Draft material",
  "cycle": "2017-to-2020",
  "source_url": "https://example.invalid/private-source-location",
  "retrieved_at": "2026-08-02T13:30:00Z",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "media_type": "application/pdf",
  "access_scope": "private-reference",
  "panel": "CMP-02",
  "page_count": 100
}
```

Do not copy proposal language, replacement text, committee statements, or NEC prose into the normalized public contract. Preserve exact source locations so an authorized reviewer can inspect the private artifact.

## Normalize development records

Create one record for each procedurally meaningful action. Supported stages are:

```text
public_input
first_revision
public_comment
second_revision
technical_meeting
standards_council
tia
erratum
```

Each record belongs to a stable `change_chain_id`. Records in the same chain describe successive actions concerning the same intended change.

Example source-safe record:

```json
{
  "record_id": "SR-synthetic",
  "change_chain_id": "gfci-synthetic",
  "record_type": "second_revision",
  "stage": "second_revision",
  "disposition": "accepted",
  "panel": "CMP-02",
  "affected_references_raw": ["210.8(A)(1) through (5)"],
  "target_references_raw": ["210.8(A)"],
  "change_types": ["modify_text"],
  "summary": "Project-authored summary of the procedural effect.",
  "source_locator": {
    "source_id": "nfpa70-2020-cmp02-second-draft",
    "page": 42,
    "anchor": "SR-synthetic"
  },
  "related_record_ids": ["FR-synthetic"]
}
```

Every `source_locator.source_id` must match a manifest entry. Unknown source IDs fail closed.

The CLI rejects extra development-record fields. In particular, do not add fields such as `proposal_text`, `replacement_text`, or `source_text`.

## Assemble the private input bundle

```json
{
  "bundle_version": "0.1.0",
  "cycle": "2017-to-2020",
  "known_2017_locators": [
    "210",
    "210.8",
    "210.8(A)",
    "210.8(A)(1)",
    "210.8(A)(2)"
  ],
  "sources": [],
  "development_records": [],
  "observed_changes": []
}
```

Populate `known_2017_locators` from the canonical 2017 hierarchy projection. Do not derive them from the development records themselves.

The initial resolver supports:

- exact Article, Section, and nested-clause locators;
- an optional `Section` prefix;
- numeric or alphabetic sibling ranges such as `210.8(A)(1) through (5)`.

Table references, figure references, exception positions, and prose-relative references remain unresolved. They are reported rather than attached to a nearby provision.

## Generate the expected dataset

Run from the repository root:

```bash
PYTHONPATH=src python scripts/build_nec_2020_expected_changelog.py \
  --input generated-private/nec-2020/development-input.json \
  --output generated-private/nec-2020/expected-changelog.json \
  --strict
```

Without `--strict`, the command writes the dataset even when review diagnostics exist. With `--strict`, diagnostics produce exit status `1` after the output is written.

Strict diagnostics include:

- unresolved controlling references;
- an expected change not found in the observed diff;
- an observed change contradicting a negative expectation;
- differing change classifications;
- an observed change with no development expectation.

Same-stage controlling records with conflicting dispositions or effects raise an error and produce no dataset.

## Procedural precedence

Within one change chain, later stages control earlier stages:

```text
erratum
TIA
Standards Council action
technical-meeting action
second revision
public comment
first revision
public input
```

A rejection, withdrawal, failed ballot, or return to prior-edition language creates a negative expectation. An accepted, issued, or corrected action creates a positive expectation. A proposal without a later disposition remains uncertain.

Confidence is derived from stage and reference resolution:

- `high`: Standards Council, TIA, or erratum with resolved controlling references;
- `medium`: Second Revision or Technical Meeting action with resolved controlling references;
- `low`: earlier-stage action, uncertain disposition, or unresolved controlling reference.

## Add observed changes later

The 2020 parser must operate without access to this expectation dataset. After the final 2020 edition has been parsed independently, generate observed AST lineage records and add them to `observed_changes`.

Rerun the command to produce reconciliation records:

- `confirmed`;
- `expected_not_observed`;
- `contradicted`;
- `ambiguous`;
- `unexpected_observed`.

Treat reconciliation findings as parser and provenance review signals. Never repair the 2020 AST merely to make it agree with the expected dataset.

## Publication boundary

The code, schemas, synthetic fixtures, source identifiers, classifications, and project-authored summaries may be versioned publicly. The private input bundle and generated corpus dataset may include source hashes and authenticated locators and should remain in an authorized private workspace unless separately reviewed for publication.

Do not commit:

- NEC or NFPA source prose;
- development-report PDFs or exports;
- page images;
- verbatim proposal or committee text;
- private source hashes tied to nonpublic artifacts;
- absolute local paths.
