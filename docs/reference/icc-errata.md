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
- the correction instruction and optional replacement text;
- source PDF page and source anchor.

The closed JSON projection is [`schemas/icc-errata-record.schema.json`](../../schemas/icc-errata-record.schema.json). Runtime deserialization recomputes the record identity, rejects unknown fields, and requires immutable printing scope.

## Adapter boundary

`IccErrataPdfAdapter` accepts a registered `application/pdf` source with evidence role `official_correction`. It must be invoked through `run_evidence_adapter`, so source-role, media-type, and exact-byte SHA-256 checks occur before PDF parsing.

The default page extractor uses PyMuPDF from the optional `evidence-pdf` dependency group:

```bash
python -m pip install -e '.[evidence-pdf]'
```

Tests inject synthetic page text and therefore keep the base runtime dependency-free.

## Bounded syntax

The adapter recognizes entries beginning with a source line shaped like:

```text
Page <printed-page>, <target>: <directive>
```

It also accepts ICC-style referenced-standard entries where the target and directive are separated by a recognized directive phrase rather than a colon.

Recognized target classes are sections, tables, figures, definitions, referenced standards, and explicit `other` targets. Recognized directives map only to insert, replace, and delete operations.

An entry with an unknown directive, malformed header, or missing replacement body is not guessed. It becomes a source-located warning and an unsupported region.

## Printing semantics

The correction source and the affected base publication are distinct identities. Adapter construction therefore requires:

- `base_publication_state_id`, identifying the state being corrected;
- `applies_to_printings`, naming the printing scope;
- a registered source whose publication identity includes a nonempty `correction_set`.

A nominal edition alone is insufficient. Two corrections with different printing scope, replacement content, or source location receive different deterministic record identities.

## Official-source validation

The bounded syntax was checked against ICC's official Digital Codes page titled **Editorial Changes – Second Printing** for the 2021 IBC. That page exposes page-labeled definition, section, referenced-standard, and appendix corrections and directs users to ICC Errata Central for complete history.

The repository does not reproduce that page's correction prose. Durable private validation should register the exact official PDF or archived official artifact, retain its digest, run the adapter locally, and record source-free counts and diagnostics.

## Non-goals

This layer does not:

- decide whether corrected language is legally adopted in a jurisdiction;
- infer that an online consolidated code corresponds to a particular printing;
- treat proposals or hearing actions as errata;
- apply amendments;
- perform compliance evaluation;
- silently coerce unrecognized editorial instructions into a known operation.
