# Current architecture projection

## Governing layers

1. **Source and publication evidence.** `SourceRegister` identifies exact artifacts, publication states, evidence roles, access scope, rights status, and cryptographic identity. Evidence adapters verify those boundaries before extraction.
2. **Layout evidence.** PDF blocks, page coordinates, printed-page labels, offsets, and geometry remain reproducibility and debugging evidence. They do not become code identity merely because they are available.
3. **Document and provision ASTs.** Document AST `0.1.0` preserves publication structure and exact evidence spans. Provision AST `0.3.0` provides nullable recursive condition expressions while rejecting unsupported grouping or mixed connectors without partial semantic output.
4. **Family-specific grammars and corpora.** Shared contracts coexist with NEC-, IBC-, ICC-evidence-, and NFPA-specific machinery. Published code sections, subsections, tables, figures, exceptions, definitions, and equations are the primary navigation addresses where the source establishes them.
5. **Validation.** Deterministic identities, span equality, containment, source ordering, diagnostics, regression fixtures, private source replay, reviewed cases, schemas, and corpus validators constrain every claim.
6. **Downstream resolution.** References, amendments, definitions, equipment evidence, and jurisdictional applicability can be projected into downstream graphs without erasing source ownership or promoting parser guesses into requirements.

## Current main support

- Document AST `0.1.0` and Provision AST `0.3.0` composable condition expressions.
- Local-only 2017 NEC ingestion, hierarchy inference, conformance reporting, definition indexing, and selected semantic review.
- A source-safe NEC 2020 expected-change framework derived from development records, with independent observed-edition reconciliation kept separate.
- A source-safe 2018 IBC structural corpus with section-first navigation, deterministic corpus and schema validation, inventories, review queues, and explicit unresolved records.
- Local-only NFPA 13 (2019) hierarchy extraction, strict bundle contracts, reviewed non-reconstructive cases, source-linked relationships, and producer provenance checks.
- Source register and guarded evidence-adapter boundaries, including ICC development evidence and Washington amendment adapters.

## Remaining gates and non-goals

- NEC 2020 observed-change reconciliation still requires an authorized issued-edition source artifact. Development records do not establish the controlling text by themselves.
- NFPA 13 figure and diagram semantics, and semantic table-column interpretation, remain unsupported unless separately reviewed.
- IBC disputed vector candidates, pilot semantic interpretations, and publisher-copy comparison remain review gates rather than asserted corpus truth.
- PDF pagination remains secondary provenance because editions, printings, and source files can move the same code section between pages.
- The repository does not provide a universal parser grammar, complete legal consolidation, jurisdictional applicability, equipment certification, or compliance reasoning.

The machine-readable projection is [`current-architecture.json`](current-architecture.json). The patch set preserves the superseded review branches as historical evidence while recording PRs #33, #34, #35, and #37 as the clean merged integration outcomes.
