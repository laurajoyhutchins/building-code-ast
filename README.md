# Building Code AST

Building Code AST is an early-stage parser and semantic-modeling project for converting selected natural-language regulatory publications into reviewable, provenance-preserving abstract syntax trees.

The project is intentionally narrower than "AI understands the building code." Its compiler boundary now has two explicit representations:

```text
source artifact and edition
  -> publication structure document AST
  -> selected provision text
  -> semantic provision AST
  -> structural validation
  -> exact source-span traceability
  -> diagnostics for unsupported or ambiguous language
```

> **Project status:** pre-1.0 research and engineering. Parsed output is not an authoritative legal interpretation, a compliance determination, or a substitute for current official publications, the authority having jurisdiction, or qualified professional judgment.

## What works today

### Document structure AST `0.1.0`

The document contract represents publication structure before semantic interpretation:

- source artifact and edition identity;
- document, chapter, section, subsection, paragraph, and nested list nodes;
- definition entries;
- table headings, columns, rows, and cells;
- headings, notes, footnotes, and unsupported structures;
- deterministic node identity from artifact ID, edition ID, node type, and structural locator;
- exact source spans for every node and diagnostic;
- strict dependency-free JSON deserialization and recursive provenance validation.

The document contract does not contain modality, condition, action, compliance, or interpretation fields. It is a source-structure layer, not a rule meaning layer.

### Provision AST `0.2.0`

The provision parser recognizes a bounded family of synthetic code-style provisions containing:

- requirement, prohibition, and permission modalities;
- a regulated subject;
- simple numeric threshold conditions;
- generic actions;
- section-reference exceptions;
- durable source-artifact identity and provision locators;
- exact source spans for recognized modality, subject, conditions, action, exceptions, and diagnostics.

The parser preserves the exact original input, including leading and trailing whitespace. All offsets address that unmodified string. Unsupported language remains visible in the output instead of being silently guessed.

### Source evidence register `0.1.0`

The publication-neutral evidence layer registers exact source artifacts without storing their prose. It distinguishes normative text, official corrections, development history, jurisdictional law, guidance, interpretations, commentary, and secondary analysis; records printing and correction state; and binds every artifact to a lowercase SHA-256.

Future source-family adapters run through a guarded boundary that checks evidence role, media type, and exact source bytes before extraction. The scaffold does not yet parse IBC errata, development monographs, or jurisdictional amendments. See [`docs/reference/source-evidence.md`](docs/reference/source-evidence.md).

## Provision example

Input:

```text
Research facilities exceeding 40 feet in height shall provide two marked evacuation routes, except as permitted by Section 12.4.
```

Run:

```bash
python -m building_code_ast.cli parse \
  --source-artifact-id "synthetic:example:v1" \
  --provision-locator "example:1" \
  "Research facilities exceeding 40 feet in height shall provide two marked evacuation routes, except as permitted by Section 12.4."
```

The output records source identity, the requirement and its evidence span, the regulated subject and its evidence span, the threshold condition, action, exception reference, exact original source text, and parser diagnostics.

## Quick start

Prerequisites:

- Python 3.12

Python 3.12 is the only supported and tested runtime during the project's pre-1.0 phase. Runtime support can expand later when an integration or downstream user establishes a concrete compatibility requirement.

From the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
building-code-ast parse "Doors shall not be obstructed."
```

The runtime package has no third-party dependencies. CLI calls default provision source identity and locator to `inline`; durable ingestion should provide stable identifiers tied to a source artifact, edition, and location.

## 2018 IBC structural corpus

The repository includes a source-safe structural corpus bound to one exact user-supplied 2018 IBC PDF. The corpus inventories formally captioned tables and figures, incidental layouts, technical-graphic candidates, displayed equations, definitions, exceptions, Chapter 35 rows, external citations, internal cross-references, and representative semantic records without committing the copyrighted source artifact.

```bash
PYTHONPATH=src python tools/validate_ibc_2018_corpus.py corpora/ibc-2018
PYTHONPATH=src python tools/validate_ibc_2018_schemas.py corpora/ibc-2018 schemas
```

The source manifest records SHA-256 `c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d`, 32,608,171 bytes, and 761 PDF pages. Counts are versioned assertions with review states and correction history, not hard-coded legal truth. See [`docs/reference/ibc-2018-corpus-contract.md`](docs/reference/ibc-2018-corpus-contract.md) and [`docs/how-to/build-ibc-2018-corpus.md`](docs/how-to/build-ibc-2018-corpus.md).

## Local NEC 2017 ingestion

The optional local ingestion adapter can convert selected articles from a user-supplied 2017 NEC PDF into validated document AST seeds with block-level PDF coordinates. PyMuPDF is isolated in the `nec-pdf` optional dependency group; the base runtime remains dependency-free.

```bash
python -m pip install -e '.[nec-pdf]'
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf \
  --output-dir generated-private/nec-2017
```

The default slice produces Articles 90, 100, and 110. Generated files may reproduce protected source expression and must remain private and outside public Git. The repository contains only the ingestion code, synthetic tests, and source-policy documentation. See [`docs/how-to/ingest-nec-2017.md`](docs/how-to/ingest-nec-2017.md).

## NEC hierarchy inference and validation

NEC ingestion infers a publication tree instead of leaving every PDF block directly beneath the Article. It recognizes Parts, Sections, uppercase subdivisions, numeric subdivisions, lowercase subdivisions, and repeated deeper marker levels; assigns canonical locators such as `110.26(A)(1)`; nests notes, exceptions, prose, and unsupported structures beneath the deepest open owner; and preserves ambiguity as diagnostics.

An independently prepared NEC 2017 clause hierarchy may serve as a local parser-development oracle. It is not copied into generated output and is not required at runtime. Compare private ArticleSeeds with that reference using:

```bash
PYTHONPATH=src python scripts/check_nec_2017_hierarchy.py \
  --article-seed generated-private/nec-2017/article-90.json \
  --article-seed generated-private/nec-2017/article-100.json \
  --article-seed generated-private/nec-2017/article-110.json \
  --oracle /path/to/nec-2017-clauses.csv \
  --report generated-private/nec-2017/hierarchy-conformance.json \
  --strict
```

The conformance report contains structural metadata and mismatch diagnostics only. It does not copy NEC prose, PDF coordinates, or source hashes. See [`docs/how-to/validate-nec-hierarchy.md`](docs/how-to/validate-nec-hierarchy.md).

## Private NEC definition and section semantics

The next local stage converts those private ArticleSeed files into a structured Article 100 definition index, an evidence-backed Section 90.5 language profile, and clause-level reviews of Sections 110.2, 110.3, 110.14, 110.16, and 110.26. This NEC-specific review layer is independently versioned from the generic Provision AST.

```bash
PYTHONPATH=src python scripts/build_nec_2017_semantics.py \
  --article-90 generated-private/nec-2017/article-90.json \
  --article-100 generated-private/nec-2017/article-100.json \
  --article-110 generated-private/nec-2017/article-110.json \
  --output-dir generated-private/nec-2017-semantics
```

The output preserves exact source spans, separates clauses, exceptions, and informational notes, records references and conservative semantic tags, and links lexical Article 100 definition evidence. It is not a compliance determination. Generated semantic files reproduce NEC text and must remain private. See [`docs/how-to/build-nec-semantic-seed.md`](docs/how-to/build-nec-semantic-seed.md).

## Repository knowledge

Repository intent, component boundaries, decisions, constraints, and maintenance procedures are maintained with [LORE](https://github.com/laurajoyhutchins/LORE).

The durable knowledge layer consists of:

- accepted semantic records under `.lore/records/`;
- transaction receipts under `.lore/transactions/`;
- deterministic extracted facts under `.lore/extracted/`;
- the shipped maintenance skill under `skills/maintain-repository-documentation/`;
- generated, non-authoritative projections under `docs/generated/`.

Start with the [repository card](docs/generated/repository-card.md), [architecture](docs/generated/architecture.md), [component catalog](docs/generated/component-catalog.md), [current decisions](docs/generated/current-decisions.md), and [maintainer guide](docs/generated/maintainer-guide.md).

Do not edit accepted records, transaction receipts, extracted facts, or generated projections directly. Documentation changes are proposed through the shipped LORE skill as one validated `lore-proposal/v1` artifact and accepted through LORE's transaction engine.

## Repository layout

- `src/building_code_ast/`: document and provision AST models, strict input handling, parsing, validation, and local ingestion adapters
- `src/building_code_ast/evidence/`: publication-neutral source registration and guarded adapter contracts
- `schemas/`: versioned JSON Schema projections of the public AST contracts and LORE trust-root schemas
- `schemas/source-register.schema.json`: closed source-register `0.1.0` projection
- `fixtures/`: synthetic fixtures plus source-safe IBC geometry anchors and rationale
- `corpora/ibc-2018/`: versioned source-safe 2018 IBC inventories, vector-path detections, reconciled references, coverage, corrections, and prioritized review packets
- `tests/`: parser, provenance, malformed-input, and regression tests
- `scripts/ingest_ibc_2018.py`: local-only coordinate-aware IBC 2018 chapter ingestion CLI
- `tools/build_ibc_2018_corpus.py`: source-safe whole-document IBC structural inventory builder
- `tools/validate_ibc_2018_corpus.py`: deterministic source-free IBC corpus validator
- `scripts/ingest_nec_2017.py`: local-only coordinate-aware NEC 2017 ingestion CLI
- `scripts/check_nec_2017_hierarchy.py`: source-free local hierarchy conformance reporter
- `scripts/build_nec_2017_semantics.py`: private Article 100 definition and selected-section review generator
- `schemas/ibc-2018-*.schema.json`: IBC source, corpus, and inventory-record contracts
- `schemas/nec-*.schema.json`: versioned NEC definition, section-review, and language-profile contracts
- `docs/reference/source-evidence.md`: source identity, publication state, rights, and adapter execution reference
- `docs/reference/nec-definition-index.md`: structured Article 100 definition contract
- `docs/reference/nec-section-review.md`: selected-section review and Section 90.5 language policy contract
- `.lore/records/`: append-only accepted semantic knowledge
- `.lore/transactions/`: accepted LORE transaction receipts
- `skills/maintain-repository-documentation/`: the shipped provider-neutral LORE maintenance skill
- `docs/generated/`: deterministic projections from accepted LORE records
- `docs/README.md`: Diátaxis documentation map and authoring guidance
- `docs/architecture.md`: representation boundaries and staged compiler model
- `docs/compatibility.md`: public AST version compatibility notes
- `docs/reference/document-ast.md`: document AST fields, identity, and invariants
- `docs/corpus-policy.md`: source, copyright, and redistribution rules
- `docs/legal-safety-boundary.md`: interpretation and product-safety constraints
- `docs/reference/legal-source-publication.md`: legal authorities and public-source publication analysis

## Relationship to Building Code Map

[Building Code Map](https://github.com/laurajoyhutchins/building-code-map) is concerned with determining which authorities and adopted codes apply to a location. Building Code AST is concerned with representing selected publication structure and provisions from those sources faithfully enough for review and later, separately governed evaluation.

The intended long-term boundary is:

```text
location -> authority and adopted source -> document AST -> selected provision -> provision AST -> reviewed rule model
```

Jurisdiction resolution does not imply that code text may be redistributed, and parsing does not imply that a provision has been authoritatively interpreted.

## Verification

Run the Python verification lanes:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src scripts tools tests
PYTHONPATH=src python tools/validate_ibc_2018_corpus.py corpora/ibc-2018
PYTHONPATH=src python tools/validate_ibc_2018_schemas.py corpora/ibc-2018 schemas
```

The read-only LORE workflow pins an exact upstream LORE revision and verifies:

```text
lore extract --check
lore validate
lore project --check
```

CI executes the Python and LORE verification lanes independently.

## Data and publication boundary

This repository contains project-authored software, documentation, schemas, and synthetic fixtures. Do not commit proprietary model-code text, standards text, licensed commentary, or bulk source material merely because it is technically obtainable. See [`docs/corpus-policy.md`](docs/corpus-policy.md) and the [`legal source publication reference`](docs/reference/legal-source-publication.md).

## License

Project-authored software and documentation are licensed under the Apache License 2.0. Third-party source material retains its own terms and must be handled according to the corpus policy.
