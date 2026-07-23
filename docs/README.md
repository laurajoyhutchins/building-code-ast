# Documentation Map

Building Code AST prefers the [Diátaxis](https://diataxis.fr/) documentation model. Each page should primarily serve one reader need rather than mixing learning, task execution, factual lookup, and conceptual discussion.

The repository is early-stage and does not yet contain all four documentation types. Existing stable paths are retained for now, but new documentation should be placed and written according to the categories below.

## Tutorials

Learning-oriented material that guides a new reader through a complete experience.

Current status: no dedicated tutorial yet.

Future examples:

- parse and inspect a synthetic provision end to end;
- extend the grammar with a reviewed synthetic fixture;
- trace a source span from input through JSON output.

## How-to guides

Task-oriented procedures for readers who already understand the basics.

Current material:

- the root [`README.md`](../README.md) contains the initial installation and CLI quick start;
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) contains contribution and verification procedures.

Future how-to guides should move into a dedicated `docs/how-to/` section when their number or complexity justifies it.

## Reference

Precise factual contracts, policies, compatibility information, and decision criteria.

Current reference material:

- [`compatibility.md`](compatibility.md): AST version compatibility;
- [`corpus-policy.md`](corpus-policy.md): source inclusion and redistribution rules;
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
