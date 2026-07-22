# Architecture

## Objective

Building Code AST converts selected regulatory language into a reviewable semantic representation while preserving what the source actually says, what the parser inferred, and what remains unresolved.

The project is a compiler pipeline, not a question-answering wrapper around an opaque model.

## Staged representations

```text
source artifact
  -> document structure tree
  -> provision AST
  -> cross-reference and definition graph
  -> reviewed normalized rule model
  -> separately governed project evaluation
```

Only the provision-AST slice exists today.

## Current AST contract

The `0.1.0` provision AST contains:

- complete source text and source span;
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
- unit normalization;
- structural validation;
- cross-reference identities;
- diagnostic codes;
- fixture comparison and regressions.

Future statistical or language-model parsers may propose candidate nodes, but they must not bypass the same contracts. Candidate output must retain source evidence, confidence, parser identity, and review status.

## Why a graph follows the AST

A single provision can be represented as a tree, but a usable code corpus cannot. Definitions, exceptions, tables, amendments, and references are reused across many provisions. Later stages therefore resolve AST nodes into a versioned semantic graph without erasing the original tree or source evidence.

## Amendment model

Jurisdictional amendments should eventually be represented as explicit patch operations against an identified base source and edition. A consolidated text view may be rendered, but the system must preserve:

- the base source and edition;
- the amending authority and enactment;
- the operation applied;
- effective dates;
- conflicts or failed patch applications;
- the resulting node provenance.

## Non-goals for the initial milestone

- ingesting an entire model code;
- deciding whether a real project complies;
- resolving discretionary terms such as "approved";
- inferring missing jurisdictional amendments;
- redistributing licensed source text;
- presenting model output as authoritative interpretation.
