# Architecture

## Objective

Building Code AST converts selected regulatory publications into reviewable structural and semantic representations while preserving what the source actually says, what a parser inferred, and what remains unresolved.

The project is a compiler pipeline, not a question-answering wrapper around an opaque model.

## Staged representations

```text
source artifact and edition
  -> page/block observations and layout reconstruction
  -> durable Source Text IR
  -> document structure tree
  -> selected provision text
  -> provision AST
  -> cross-reference and definition graph
  -> reviewed normalized rule model
  -> separately governed project evaluation
```

The durable Source Text, document-structure, and provision-AST slices exist today. Source Text is the reusable boundary between expensive source-family extraction/layout work and ordinary structural lookup. Reference resolution, amendment application, reviewed normalization, and project evaluation remain later stages.

## Durable Source Text contract

Source Text `source-text/v1` records canonical extracted text and provenance before publication structure is interpreted. It includes:

- exact source artifact and edition identity;
- exact retained-source SHA-256 and byte size;
- extractor and projection identities and versions;
- canonical UTF-8 text with Unicode-codepoint offsets compatible with `SourceSpan`;
- ordered non-overlapping fragments whose text hashes round-trip to canonical text;
- one or more source observations per fragment, including physical PDF page and available geometry/observation identity;
- a deterministic structural index projected from validated Document AST locators and node IDs;
- exact text, component, and bundle hashes;
- explicit extraction diagnostics.

Private bundle persistence is storage-neutral and immutable-on-write. The canonical bundle consists of `manifest.json`, `document.txt`, `fragments.jsonl`, `sections.jsonl`, and `diagnostics.jsonl`. Loading verifies every component hash and source identity before lookup. Restricted source prose and private generated bundles stay outside public Git.

The canonical text stream plus its structural index is authoritative for compiled-text lookup. Per-section text shards are not authority. `building-code-text get <bundle> <locator>` loads only the persisted Source Text bundle; it does not import the PDF extraction stack or rerun layout reconstruction, hierarchy building, or semantic parsing.

Source Text must not encode modality, conditions, actions, compliance conclusions, legal interpretation, or publication-family semantic meaning. NEC normalized block/source-map records and IBC logical-block/source-fragment records project into the same generic contract after their existing extraction/layout work.

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
- Source Text and AST schema versions;
- canonical compiled-text hashes and source provenance;
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
