# Documentation Map

Building Code AST prefers the [Diátaxis](https://diataxis.fr/) documentation model. Each page should primarily serve one reader need rather than mixing learning, task execution, factual lookup, and conceptual discussion.

The repository is early-stage and does not yet contain all four documentation types. Existing stable paths are retained for now, but new documentation should be placed and written according to the categories below.

## Tutorials

Learning-oriented material that guides a new reader through a complete experience.

Current status: no dedicated tutorial yet.

Future examples:

- construct and validate a synthetic document tree;
- parse and inspect a synthetic provision end to end;
- extend the grammar with a reviewed synthetic fixture;
- trace a source span from input through JSON output.

## How-to guides

Task-oriented procedures for readers who already understand the basics.

Current material:

- the root [`README.md`](../README.md) contains the initial installation and CLI quick start;
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) contains contribution and verification procedures;
- [`how-to/ingest-nec-2017.md`](how-to/ingest-nec-2017.md) explains how to generate private ArticleSeed files from a locally supplied NEC 2017 PDF;
- [`how-to/validate-nec-hierarchy.md`](how-to/validate-nec-hierarchy.md) explains how to compare inferred hierarchy with the locally supplied NEC 2017 clause oracle without making it a runtime dependency;
- [`how-to/build-nec-semantic-seed.md`](how-to/build-nec-semantic-seed.md) explains how to generate the private Article 100 definition index and selected Article 90/110 section reviews.

Future how-to guides should remain in `docs/how-to/` and preserve the repository's source-publication boundary.

## Reference

Precise factual contracts, policies, compatibility information, and decision criteria.

Current reference material:

- [`compatibility.md`](compatibility.md): independent document and provision AST version compatibility;
- [`corpus-policy.md`](corpus-policy.md): source inclusion and redistribution rules;
- [`reference/document-ast.md`](reference/document-ast.md): document AST fields, identity algorithm, and validation invariants;
- [`reference/source-evidence.md`](reference/source-evidence.md): publication-state identity, source registration, rights handling, and guarded evidence-adapter execution;
- [`reference/nec-definition-index.md`](reference/nec-definition-index.md): structured Article 100 definition fields and provenance invariants;
- [`reference/nec-section-review.md`](reference/nec-section-review.md): selected-section review, modal-language policy, and definition-link boundaries;
- [`reference/nec-style-manual-profile.md`](reference/nec-style-manual-profile.md): edition-aware editorial rules used as parser priors and validation context;
- [`reference/legal-source-publication.md`](reference/legal-source-publication.md): legal authorities and operational publication boundaries.

Reference pages should state what the system, format, or policy is. Extended rationale belongs in explanation pages.

## Explanation

Conceptual material that develops understanding, tradeoffs, and design reasoning.

Current explanation material:

- [`architecture.md`](architecture.md): compiler stages and representation boundaries;
- [`legal-safety-boundary.md`](legal-safety-boundary.md): why representation, interpretation, evaluation, and professional judgment remain distinct.

Explanation pages may discuss alternatives and rationale, but should not become step-by-step operating procedures or exhaustive field specifications.

## Authoring rule

Before adding a page, identify its primary reader question:

- **Tutorial:** “Can you teach me through a complete learning experience?”
- **How-to:** “How do I accomplish this specific task?”
- **Reference:** “What exactly is the contract, rule, field, or authority?”
- **Explanation:** “Why is the system designed or understood this way?”

Cross-links are encouraged. Genre soup is not.