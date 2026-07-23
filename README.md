# Building Code AST

Building Code AST is an early-stage parser and semantic-modeling project for converting selected natural-language regulatory provisions into reviewable, provenance-preserving abstract syntax trees.

The project is intentionally narrower than "AI understands the building code." Its first goal is a deterministic vertical slice:

```text
source provision
  -> exact original source text plus artifact identity
  -> semantic provision AST
  -> structural validation
  -> exact source-span traceability
  -> diagnostics for unsupported or ambiguous language
```

> **Project status:** pre-1.0 research and engineering. Parsed output is not an authoritative legal interpretation, a compliance determination, or a substitute for current official publications, the authority having jurisdiction, or qualified professional judgment.

## What works today

The first vertical slice recognizes a bounded family of synthetic code-style provisions containing:

- requirement, prohibition, and permission modalities;
- a regulated subject;
- simple numeric threshold conditions;
- generic actions;
- section-reference exceptions;
- durable source-artifact identity and provision locators;
- exact source spans for recognized modality, subject, conditions, action, exceptions, and diagnostics.

The parser preserves the exact original input, including leading and trailing whitespace. All offsets address that unmodified string. Unsupported language remains visible in the output instead of being silently guessed.

## Example

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

- Python 3.12 or newer

From the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
building-code-ast parse "Doors shall not be obstructed."
```

The runtime package has no third-party dependencies. CLI calls default source identity and locator to `inline`; production ingestion should provide durable values tied to the source artifact and provision location.

## Repository layout

- `src/building_code_ast/`: AST model, parser, validation, and CLI
- `schemas/`: versioned JSON Schema projections of the public AST contract
- `fixtures/`: synthetic source and expected-output fixtures
- `tests/`: parser, provenance, and regression tests
- `docs/README.md`: Diátaxis documentation map and authoring guidance
- `docs/architecture.md`: representation boundaries and staged compiler model
- `docs/compatibility.md`: public AST version compatibility notes
- `docs/corpus-policy.md`: source, copyright, and redistribution rules
- `docs/legal-safety-boundary.md`: interpretation and product-safety constraints
- `docs/reference/legal-source-publication.md`: legal authorities and public-source publication analysis

## Relationship to Building Code Map

[Building Code Map](https://github.com/laurajoyhutchins/building-code-map) is concerned with determining which authorities and adopted codes apply to a location. Building Code AST is concerned with representing selected provisions from those sources faithfully enough for review and later, separately governed evaluation.

The intended long-term boundary is:

```text
location -> authority and adopted source -> selected provision -> AST -> reviewed rule model
```

Jurisdiction resolution does not imply that code text may be redistributed, and parsing does not imply that a provision has been authoritatively interpreted.

## Verification

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

CI executes both commands on Python 3.12 and 3.13.

## Data and publication boundary

This repository contains project-authored software, documentation, schemas, and synthetic fixtures. Do not commit proprietary model-code text, standards text, licensed commentary, or bulk source material merely because it is technically obtainable. See [`docs/corpus-policy.md`](docs/corpus-policy.md) and the [`legal source publication reference`](docs/reference/legal-source-publication.md).

## License

Project-authored software and documentation are licensed under the Apache License 2.0. Third-party source material retains its own terms and must be handled according to the corpus policy.
