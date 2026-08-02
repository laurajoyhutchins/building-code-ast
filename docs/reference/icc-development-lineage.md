# ICC Code-Development Lineage

## Purpose

The development-history layer represents proposals and process actions as evidence about how potential code changes moved through ICC's process. It does not assert that proposed language appears in an issued edition.

## Record contract `0.1.0`

`DevelopmentRecord` preserves:

- registered source identity;
- ICC-style proposal identifier and stable semantic record key;
- record kind: proposal, public comment, committee action, hearing action, or final action;
- disposition: submitted, approved, approved as modified, disapproved, withdrawn, or superseded;
- source-local sequence, proponent, affected locators, parent record keys, action date, summary, and source location;
- deterministic `development:<sha256>` identity.

The closed JSON projection is [`schemas/icc-development-record.schema.json`](../../schemas/icc-development-record.schema.json). Runtime deserialization rejects unknown fields and recomputes record identity.

## Lineage validation

`DevelopmentLineage` requires unique semantic record keys and unique sequence values within each proposal. Every parent key must resolve to a record in the same loaded lineage, including deliberate cross-proposal supersession links.

Each proposal identifier must contain exactly one proposal record at sequence 1. Every non-proposal record must have a parent and must be connected through its ancestors to that proposal record. The complete parent graph must be acyclic. These rules prevent a set of individually valid records from masquerading as a valid process chain while containing cycles, detached actions, or no proposal origin.

Within one proposal, every parent sequence must precede its child sequence. Cycle detection runs first so a cyclic graph retains its most fundamental diagnostic instead of being reported only as a chronology error.

A proposal record may retain a cross-proposal parent to represent supersession or derivation, but that relationship cannot create a cycle.

The controlling record is selected by process stage, then sequence:

1. final action;
2. hearing action;
3. committee action;
4. public comment;
5. proposal.

Multiple final-action records with different dispositions are invalid. The model refuses to infer which incompatible result should control.

Rejected, withdrawn, and superseded records remain first-class evidence. They are not discarded merely because they did not become issued language.

## Bounded adapter

`IccDevelopmentTextAdapter` version `0.2.0` consumes a registered `application/pdf` source with evidence role `development_history`. It is invoked through `run_evidence_adapter`, so source role, media type, and exact-byte SHA-256 are checked before extraction.

The default extractor uses the optional `evidence-pdf` PyMuPDF group. Tests inject synthetic page text.

The bounded grammar recognizes proposal blocks beginning with an ICC-style proposal identifier and labeled fields for proponent, affected locators, proposal summary, public comment, committee action, hearing or assembly action, and final action.

Action sequence values preserve their source ordinals. At the first unsupported action, the adapter closes that proposal's extractable parent chain. Later actions remain diagnostic-backed unsupported regions instead of being linked across an unknown intermediate process event.

## Relationship to ICC's process

ICC's 2024–2026 development cycle publishes proposed-change monographs, Committee Action Hearing materials and results, public-comment materials, and final-action results as distinct artifacts. The lineage model keeps these stages separate and links them through explicit record keys rather than flattening the process into one final label.

## Verification boundary

Development history may form an expectation oracle for later edition comparison. It is not proof that a particular printing contains the expected language. Issued normative text must be independently observed and compared.

Public Git contains only project-authored contracts and synthetic fixtures. Official monographs and result documents remain registered external artifacts subject to the corpus policy.
