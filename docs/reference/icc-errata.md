# ICC Errata Record and Bounded PDF Adapter

## Purpose

The ICC errata layer represents official corrections as records that apply to a named base publication state. It remains separate from the structural Document AST, issued normative text, code-development history, and jurisdictional amendments.

Public Git contains the contract, parser, schema, and synthetic fixtures. Official ICC source bytes and extracted correction text remain outside Git unless redistribution is independently authorized.

## Record contract `0.1.0`

`ErratumRecord` preserves:

- registered source identity and source-local sequence;
- deterministic `erratum:<sha256>` identity;
- the affected base `publication:<sha256>` state;
- correction-set identity and printing applicability;
- target kind, target locator, and printed page label;
- bounded operation: `insert`, `replace`, or `delete`;
- the correction instruction and operation-appropriate replacement text;
- source PDF page and source anchor.

The closed JSON projection is [`schemas/icc-errata-record.schema.json`](../../schemas/icc-errata-record.schema.json). Runtime deserialization recomputes the record identity, rejects unknown fields, requires immutable printing scope, requires replacement text for insert and replace, and prohibits replacement text for delete.

## Adapter boundary

`IccErrataPdfAdapter` accepts a registered `application/pdf` source with evidence role `official_correction`. It must be invoked through `run_evidence_adapter`, so source-role, media-type, and exact-byte SHA-256 checks occur before PDF parsing.

The default page extractor uses PyMuPDF from the optional `evidence-pdf` dependency group:

```bash
python -m pip install -e '.[evidence-pdf]'
```

Tests inject synthetic page text and therefore keep the base runtime dependency-free.

## Bounded syntax

ICC correction lists are not completely uniform. The adapter recognizes page-labeled entries using either a comma or period after the printed page label:

```text
Page <printed-page>, <target>: <directive>
Page <printed-page>. <target> <directive>
```

A colon is optional when a recognized target and directive phrase can be separated without ambiguity. The bounded directive vocabulary includes added, deleted, corrected, revised, renumbered, relocated, and now-reads forms. Renumbering and relocation are represented as replacements because the record preserves the complete instruction rather than reducing the change to a bare text substitution.

Section targets are reduced to the explicit section locator before instruction prose is interpreted. Other recognized target classes are tables, figures, definitions, referenced standards, and explicit `other` targets.

Each page-labeled header starts a new candidate entry even when its directive is unsupported. This prevents an unfamiliar correction from being absorbed into the preceding entry's replacement text.

An entry with an unknown directive, malformed header, or missing required replacement body is not guessed. It becomes a source-located warning and an unsupported region.

## Printing semantics

The correction source and the affected base publication are distinct identities. Adapter construction therefore requires:

- `base_publication_state_id`, identifying the state being corrected;
- `applies_to_printings`, naming the printing scope;
- a registered source whose publication identity includes a nonempty `correction_set`.

A nominal edition alone is insufficient. Two corrections with different printing scope, replacement content, or source location receive different deterministic record identities.

## Official-source validation

The bounded syntax was checked against ICC's official Digital Codes page titled **Editorial Changes – Second Printing** for the 2021 IBC. That page includes comma-form and period-form page headers, page-labeled definition and section corrections, deletions, renumbering, referenced-standard changes, and appendix corrections. It also directs users to ICC Errata Central for complete history.

The repository does not reproduce that page's correction prose. Durable private validation should register the exact official PDF or archived official artifact, retain its digest, run the adapter locally, and record source-free counts and diagnostics.

## Non-goals

This layer does not:

- decide whether corrected language is legally adopted in a jurisdiction;
- infer that an online consolidated code corresponds to a particular printing;
- treat proposals or hearing actions as errata;
- apply amendments;
- perform compliance evaluation;
- silently coerce unrecognized editorial instructions into a known operation.
