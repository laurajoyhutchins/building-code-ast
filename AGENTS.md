# Building Code AST Repository Guidance

## Purpose

Building Code AST is a provenance-preserving compiler and semantic-modeling system for selected regulatory publications. It transforms exact source artifacts into reviewable page observations, document structure, bounded provision semantics, references, definitions, and later reviewed rule candidates without collapsing parser output into legal requirements.

## Non-goals

Do not turn this repository into legal advice, a compliance engine, a building-design authority, a jurisdiction resolver, a generic PDF-to-text tool, a RAG system, a project checker, or a repository of copyrighted source PDFs and extracted corpora.

## Compiler authority model

Preserve these stages:

```text
source artifact and edition
  -> page and block observations
  -> Document AST
  -> selected provision text
  -> Provision AST
  -> reference and definition graph
  -> amendment-aware reviewed rule model
  -> separately governed project evaluation
```

- Source evidence owns artifact, edition, printing, correction state, hash, page count, metadata, provenance, access, and redistribution restrictions.
- Page and block records are source observations, not legal propositions.
- Document AST represents publication structure before semantic interpretation.
- Provision AST represents bounded syntactic and semantic candidates, not reviewed rules or project requirements.
- Reviewed rules and project evaluation are later, separately versioned and governed representations.
- Generated-private corpora and restricted source artifacts remain outside Git.

## Core invariants

- Every node and diagnostic traces to exact source evidence.
- Source spans name their coordinate space and round-trip correctly.
- IDs are deterministic, edition-specific, and independent of array order.
- Unsupported or ambiguous structures remain visible.
- Source-specific adapters pass through generic validation.
- Definitions and references resolve only in explicit edition and context.
- Amendments preserve base text and patch operations rather than destructively rewriting history.
- Model-assisted parsing may propose candidates but cannot bypass deterministic contracts or human review.
- Code sections and subsections are the primary navigational model; PDF pages remain secondary provenance and debugging metadata.

## Source-family boundaries

Keep generic compiler models separate from NEC, IBC, and future publication adapters. Do not force NEC hierarchy rules onto IBC or encode every source quirk in generic nodes. Tables, figures, definitions, references, notes, exceptions, appendices, and footnotes require explicit structures and diagnostics.

## Source and publication policy

Do not commit proprietary model-code PDFs, source text, full tables or figures, licensed commentary, privately retained hierarchy oracles, or generated private ASTs that reproduce protected expression. Use synthetic fixtures, metadata, hashes, locators, compact factual observations, and source-free structural summaries.

## Skill routing

Read the current `using-lauras-skills` guidance first. Use `architecture-review` for stage and authority boundaries, `ontology-design` for semantic models, `data-engineering-design` for corpus pipelines, `python-idiomatic` for implementation, `repo-config-governance` for schemas and private outputs, and the testing, debugging, review, and verification skills for delivery.

## Working method

- Inspect models, schemas, validators, adapters, source registers, corpus contracts, tests, open PRs, recent decisions, and reviewed repository knowledge before editing.
- Use an isolated branch or worktree.
- Use test-driven development for behavioral changes.
- Change authoritative models and schemas before regenerating lawful projections.
- Record compatibility and schema-version implications.
- Prefer simplification and deletion when provenance and semantics are preserved.
- Reviewed repository knowledge lives under `.lore/knowledge/`; edit it directly and use normal Git review. LORE has no proposal or transaction lifecycle in this repository.

## Deciduous

- Use upstream Deciduous directly. The Git-shared graph state is native sync state under `.deciduous/sync/**`; `.deciduous/deciduous.db` is local operational state.
- Rebuild local database state from `.deciduous/sync/**` when needed and inspect `deciduous pulse` before relying on graph context.
- Include material native sync changes with the repository work that caused the decision, outcome, supersession, or unresolved question.
- Do not build BCAST-specific Deciduous wrappers, schemas, parsers, validators, mirrors, replay systems, or recovery machinery.
- If Deciduous cannot run in the current environment, do not emulate it. Use Git and GitHub as the durable technical authority and defer graph mutation until the stock CLI is available.

## Testing

Verify source identity, span bounds and round trips, deterministic IDs and serialization, strict deserialization, diagnostic stability, unsupported-structure preservation, NEC and IBC hierarchy fixtures, tables, figures, definitions, references, units, modalities, amendment targets, schema compatibility, publication exclusions, and deterministic private-source runs.

Ordinary CI must use synthetic or lawfully publishable fixtures. Private NEC and IBC verification must use the exact retained artifact and remain outside Git.

## Git and completion

Open a draft PR for substantive work. Include exact head SHA, compiler-stage and schema changes, parser and adapter changes, compatibility impact, corpus and publication implications, tests, private-source verification, unresolved research, and owner decisions. Do not merge stale or unverified heads. Do not claim corpus completeness, semantic correctness, legal interpretation, or publication safety beyond verified evidence.
