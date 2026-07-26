# Architecture

## Objective

Building Code AST converts selected regulatory publications into reviewable structural and semantic representations while preserving what the source actually says, what a parser inferred, and what remains unresolved.

The project is a compiler pipeline, not a question-answering wrapper around an opaque model.

## Staged representations

```text
source artifact and edition
  -> document structure tree
  -> selected provision text
  -> provision AST
  -> cross-reference and definition graph
  -> reviewed normalized rule model
  -> separately governed project evaluation
```

The document-structure and provision-AST slices exist today. Reference resolution, amendment application, reviewed normalization, and project evaluation remain future stages.

## Document structure contract

Document AST `0.1.0` records publication structure before semantic interpretation. It includes:

- explicit artifact and edition identity;
- structural locators and deterministic node IDs;
- document, chapter, section, subsection, paragraph, and list nodes;
- definition entries;
- table headings, columns, rows, and cells;
- headings, notes, footnotes, and unsupported structures;
- exact source spans on every node and diagnostic.

A node ID is the SHA-256 digest of canonical JSON containing `artifact_id`, `edition_id`, `node_type`, and `locator`, prefixed with `docnode:`. Source text and offsets are deliberately excluded from the identity input. Reprocessing the same edition preserves node identity; changing the edition changes node identity.

Runtime validation proves that every span round-trips to the exact original source, every child remains within its parent span, every locator and node ID is unique, and every supplied ID matches the deterministic identity function.

The document tree must not encode modality, conditions, actions, compliance conclusions, or interpretation. Those belong to later representations.

## Provision AST contract

Provision AST `0.2.0` contains:

- complete source text and source span;
- source artifact identity and a provision locator;
- modality: requirement, prohibition, permission, or unknown;
- regulated subject;
- zero or more numeric comparison conditions;
- an action preserved as source text, with optional normalized verb and object;
- zero or more section-reference exceptions;
- diagnostics for unsupported, ambiguous, or missing structures.

Every derived node that depends on a source phrase carries an exact character span. Runtime validation proves that each span round-trips to the original source.

## Deterministic core and model-assisted extensions

The deterministic core owns:

- source identity and spans;
- AST schema versions;
- document node identities and structural locators;
- unit normalization;
- structural validation;
- cross-reference identities;
- diagnostic codes;
- fixture comparison and regressions.

Future statistical or language-model parsers may propose candidate nodes, but they must not bypass the same contracts. Candidate output must retain source evidence, confidence, parser identity, and review status.

## Why a graph follows the AST

A single document or provision can be represented as a tree, but a usable code corpus cannot. Definitions, exceptions, tables, amendments, and references are reused across many provisions. Later stages therefore resolve AST nodes into a versioned semantic graph without erasing the original tree or source evidence.

## Amendment model

Jurisdictional amendments should eventually be represented as explicit patch operations against an identified base source and edition. A consolidated text view may be rendered, but the system must preserve:

- the base source and edition;
- the amending authority and enactment;
- the operation applied;
- effective dates;
- conflicts or failed patch applications;
- the resulting node provenance.

## Non-goals for the current milestone

- ingesting an entire model code;
- automatically parsing arbitrary publication layout;
- deciding whether a real project complies;
- resolving discretionary terms such as "approved";
- inferring missing jurisdictional amendments;
- redistributing licensed source text;
- presenting model output as authoritative interpretation.
