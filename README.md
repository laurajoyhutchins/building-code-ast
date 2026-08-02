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

## Local NEC 2017 ingestion

The optional local ingestion adapter can convert selected articles from a user-supplied 2017 NEC PDF into validated document AST seeds with block-level PDF coordinates. PyMuPDF is isolated in the `nec-pdf` optional dependency group; the base runtime remains dependency-free.

```bash
python -m pip install -e '.[nec-pdf]'
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf \
  --output-dir generated-private/nec-2017
```

The default slice produces Articles 90, 100, and 110. Generated files may reproduce protected source expression and must remain private and outside public Git. The repository contains only the ingestion code, synthetic tests, and source-policy documentation. See [`docs/how-to/ingest-nec-2017.md`](docs/how-to/ingest-nec-2017.md).

## Local IBC 2018 ingestion

The IBC adapter converts Chapters 1 through 3 from a user-supplied 2018 IBC PDF into validated ChapterSeed files with positioned PDF fragments and private layout-analysis evidence. The supported source has no usable outline and exposes individual glyphs rather than ordinary text lines, so the adapter reconstructs visual lines, removes recurring page furniture, estimates body-font evidence, infers page-local reading order, and fails closed outside verified page ranges.

```bash
python -m pip install -e '.[ibc-pdf]'
python scripts/ingest_ibc_2018.py /path/to/icc-2018.pdf \
  --output-dir generated-private/ibc-2018
```

Publisher user-note commentary is excluded with explicit removal reasons. Announced ruled tables are reconstructed from vector boundaries into deterministic base-grid rows and cells; ambiguous layouts remain visible with diagnostics rather than being guessed. Every retained visual line and fragment is validated for exact consumption and span round-tripping. Generated files may reproduce protected source expression and must remain private and outside public Git. See [`docs/how-to/ingest-ibc-2018.md`](docs/how-to/ingest-ibc-2018.md).

## Repository layout

- `src/building_code_ast/`: document and provision AST models, strict input handling, parsing, validation, and local ingestion adapters
- `schemas/`: versioned JSON Schema projections of the public AST contracts
- `fixtures/`: synthetic source and expected-output fixtures
- `tests/`: parser, provenance, malformed-input, and regression tests
- `scripts/ingest_nec_2017.py`: local-only coordinate-aware NEC 2017 ingestion CLI
- `scripts/ingest_ibc_2018.py`: local-only positioned-glyph IBC 2018 ingestion CLI
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

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src scripts tests
```

CI executes both commands on Python 3.12.

## Data and publication boundary

This repository contains project-authored software, documentation, schemas, and synthetic fixtures. Do not commit proprietary model-code text, standards text, licensed commentary, or bulk source material merely because it is technically obtainable. See [`docs/corpus-policy.md`](docs/corpus-policy.md) and the [`legal source publication reference`](docs/reference/legal-source-publication.md).

## License

Project-authored software and documentation are licensed under the Apache License 2.0. Third-party source material retains its own terms and must be handled according to the corpus policy.
