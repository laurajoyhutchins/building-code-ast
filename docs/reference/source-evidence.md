# Source Evidence Register and Adapter Boundary

## Purpose

The source-evidence layer identifies the exact artifacts that support document ASTs, change histories, amendments, interpretations, and other later-stage records. It records what a source is, which publication state it belongs to, why it is being used, how it was obtained, and whether its bytes match the registered artifact.

The layer does not contain building-code prose and does not decide what a provision means. It is provenance infrastructure for later source-family-specific models.

The public API is available from:

```python
from building_code_ast.evidence import ...
```

The root `building_code_ast` package does not re-export these pre-1.0 contracts.

## Source register `0.1.0`

A `SourceRegister` contains one or more unique `SourceRegisterEntry` values. Every entry includes:

- a stable `source_id`;
- the exact `artifact_id` and `edition_id` used by related AST output;
- title and issuing body;
- one primary evidence role;
- publication family, edition, printing, digital revision, correction set, publication date, and optional issuer-defined effective date;
- retrieval timestamp with timezone;
- lowercase SHA-256 and media type;
- access scope and rights status;
- optional source URL, jurisdiction, and rights note.

The JSON projection is defined by [`schemas/source-register.schema.json`](../../schemas/source-register.schema.json). Runtime deserialization is stricter than schema parsing alone: it rejects duplicate source IDs, recomputes publication identity, validates dates and timezone-bearing timestamps, and enforces cross-field rights requirements.

## Evidence roles

Every source has one primary role:

| Role | Intended use |
|---|---|
| `normative_text` | Issued model-code or legally controlling text |
| `official_correction` | Errata or another official correction to a publication state |
| `development_history` | Proposal, public comment, hearing action, or similar process evidence |
| `jurisdictional_law` | Adoption instrument, regulation, ordinance, or enacted amendment |
| `administrative_guidance` | Bulletin, code note, agency guide, or implementation material |
| `official_interpretation` | Interpretation issued through an identified official process |
| `commentary` | Explanatory commentary kept separate from normative text |
| `secondary_analysis` | Handbook, comparison, or other corroborating analysis |

The singular role is deliberate. A source may be cited by several downstream records, but the register does not blend normative language, legal amendments, historical evidence, guidance, and commentary into one undifferentiated authority class.

## Publication-state identity

`PublicationIdentity` supplements the AST's existing artifact and edition identity. Its deterministic identifier has the form:

```text
publication:<sha256>
```

The digest is calculated from canonical JSON containing:

- publication family;
- edition;
- printing;
- digital revision;
- correction set;
- publication date;
- issuer-defined effective date, when the publication itself establishes one;
- an explicit addenda set when one is modeled.

Reprocessing the same publication state produces the same identifier. A change to printing, correction set, digital revision, incorporated addenda, or intrinsic publication timing can therefore produce a different state identifier even when the nominal edition remains unchanged.

Publication-state identity is deliberately independent of the bytes of any one evidence artifact. A PDF, HTML rendition, or other exact source artifact has its own source identity and SHA-256 and may evidence a publication state without becoming that state. This allows multiple exact artifacts to support one issued state while retaining byte-level provenance for each artifact.

A `DocumentAst` may bind its `source_artifact` directly to a known `publication_state_id`. That binding does not participate in structural `docnode:*` identity, so attaching publication-state provenance to an existing exact artifact does not renumber its nodes.

`PublicationIdentity.effective_on` must not be used for jurisdiction adoption timing. It is reserved for an effective date intrinsic to the issued publication state itself. State, municipal, or other jurisdiction adoption/effective intervals belong to a separate jurisdiction/adoption layer that references the immutable publication state. Different jurisdictions making the same model-code state effective on different dates must not create different publisher publication-state identities.

This permits the system to distinguish, for example, an original 2021 printing from a later corrected digital publication while keeping jurisdiction-specific adoption history outside the publisher-state identity.

## Access and rights

Access scope and rights status answer different questions:

- `access_scope` describes how the artifact is available to the ingestion process;
- `rights_status` records the project's publication or redistribution classification.

Non-public access, licensed material, and material classified as uncertain or restricted require a nonempty `rights_note`. The note records the handling boundary; it does not grant rights.

Restricted source bytes remain outside Git. Register serialization may contain metadata, checksums, locators, and project-authored descriptions, but not bulk source text, page images, commentary, or licensed tables.

## Adapter protocol

An evidence adapter declares:

```python
adapter_id: str
adapter_version: str
supported_roles: frozenset[EvidenceRole]
supported_media_types: frozenset[str]
```

and implements:

```python
def extract(
    source: SourceRegisterEntry,
    content: bytes,
) -> AdapterResult[RecordT]: ...
```

Adapters are invoked through `run_evidence_adapter`, not by calling `extract` directly in a durable ingestion workflow.

Before extraction, the runner verifies:

1. adapter identity and version are present;
2. the source evidence role is supported;
3. the source media type is supported;
4. the supplied bytes have the registered SHA-256.

Digest verification occurs before adapter code runs. A mismatched artifact therefore cannot produce records or partial parser effects.

After extraction, the runner checks that the result repeats the exact source ID, adapter ID, and adapter version used for the invocation.

## Adapter result envelope

`AdapterResult[T]` contains:

- typed source-family-specific records;
- source-located diagnostics;
- unsupported source regions retained for review;
- exact source and adapter identity.

`SourceRegion` can identify a page, a source anchor, or a page-bound PDF bounding box. Bounding boxes require a positive page number and positive area. A region with no locator is invalid.

The generic envelope deliberately does not define errata, code-change proposals, amendments, referenced standards, or interpretations. Those records require their own closed and versioned models.

## Failure behavior

The layer fails closed for:

- unknown JSON fields;
- unsupported enum values;
- malformed dates or timestamps;
- invalid digests;
- duplicate source IDs;
- missing rights notes for restricted material;
- invalid pages or bounding boxes;
- adapter and source incompatibility;
- source-byte digest mismatch;
- adapter result identity mismatch.

It does not repair metadata, infer missing publication state, select a nearby edition, or treat a helpful secondary source as normative evidence.

## Intended first adapters

The first planned IBC source-family adapters are:

1. ICC errata PDF extraction for printing-sensitive correction records;
2. ICC code-development monograph extraction for proposal and action lineage;
3. Washington WAC HTML extraction for jurisdictional amendment patches.

Those adapters are not implemented by this scaffold. Their records, extraction logic, fixtures, and independent verification belong in separate bounded changes.

## Relationship to current NEC and IBC work

The NEC expected-changelog work already has NEC-specific development-record and reconciliation contracts. It may later map its source manifests to this register, but this scaffold does not require or perform that migration.

The local IBC ingestion pipeline may use `AstSourceIdentity` to connect supplementary records to the exact AST artifact and edition it parsed. Errata, development events, amendments, jurisdiction adoptions, and effective-code projections remain separate evidence or provenance graphs rather than fields inserted into structural document nodes.
