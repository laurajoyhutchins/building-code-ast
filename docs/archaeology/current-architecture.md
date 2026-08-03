# Current architecture projection

## Governing layers

1. **Source and publication evidence.** `SourceRegister` identifies an exact artifact, publication state, evidence role, access scope, rights status, and SHA-256. Evidence adapters verify the registered role, media type, and exact bytes before extraction.
2. **Layout evidence.** PDF layout records text blocks, page coordinates, outline candidates, and normalized ordering. Coordinates are retained as evidence; they are not assumed to be hierarchy.
3. **Document AST 0.1.0.** The publication tree uses stable identities, recursive parent-child structure, exact spans, tables, definitions, notes, footnotes, and unsupported nodes without semantic modality fields.
4. **Family grammar.** NEC hierarchy and selected semantic review are merged. IBC and NFPA 13 grammars remain branch-bound. ICC errata and development adapters are evidence-family parsers, not code-tree parsers.
5. **Validation.** Deterministic identities, span equality, containment, parent legality, source ordering, diagnostics, regression fixtures, private source replay, and official-corpus cases validate bounded claims.
6. **Downstream graph and products.** Definitions, exceptions, references, amendments, equipment evidence, and jurisdictional applicability can be resolved into graphs without erasing the source tree.

## Current main support

- Document AST `0.1.0` and Provision AST `0.2.0`.
- Local-only 2017 NEC ingestion for selected Articles 90, 100, and 110.
- NEC hierarchy inference and independent conformance reporting for the exercised slice.
- Article 100 definition indexing and selected Section 90.5/110 reviews.
- Source register and guarded evidence adapter boundary.
- ICC errata, proposal, action-report, and development-lineage evidence adapters.
- Washington normalized and official WAC amendment adapters.

## Not current main support

- Provision AST `0.3.0` composable condition expressions in PR #12.
- 2018 IBC ingestion, layout analysis, hierarchy runtime, figures, appendices, or full-edition coverage in PRs #15, #17, and #18.
- An observed 2017-to-2020 NEC changelog in PR #19.
- 2019 NFPA 13 ingestion or hierarchy in PR #20.
- A universal parser grammar.
- Complete legal consolidation, jurisdictional applicability, equipment certification, or compliance reasoning.

The machine-readable projection is [`current-architecture.json`](current-architecture.json).
