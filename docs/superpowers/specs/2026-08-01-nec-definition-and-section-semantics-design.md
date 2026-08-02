# NEC Definition and Section Semantics

Date: 2026-08-01
Status: Approved from the preceding ArticleSeed review
Base: draft PR #13, local NEC 2017 ingestion

## Context

The local ingestion slice produces coordinate-backed ArticleSeed JSON for Articles 90, 100, and 110. The publication AST preserves text and broad node types, but it intentionally does not yet represent definition internals or normative section clauses.

The next layer must remain source-safe. Public Git may contain only project-authored code, schemas, documentation, and synthetic fixtures. Actual NEC text and text-bearing derived output remain private.

## Decision

Add a separate `building_code_ast.nec` package with two independently versioned contracts:

1. **NEC Definition Index `0.1.0`** converts Article 100 definition-entry blocks and their attached continuation, list, and note nodes into structured entries.
2. **NEC Section Review `0.1.0`** converts selected Article 90 and 110 sections into conservative, evidence-backed clause reviews.

The new contracts do not modify or depend on the generic Provision AST contract. They consume ArticleSeed JSON and preserve exact evidence spans.

## Definition index contract

Each definition entry records:

- deterministic identity from source artifact identity and the original document-node locator;
- the exact displayed term and its source span;
- a conservative canonical term;
- alternate terms that are clearly parenthetical names or abbreviations;
- applicability or scope qualifiers preserved with exact spans;
- ordered body fragments with their original node locators and node types;
- attached informational notes;
- code-making-panel markers;
- section, article, and table references;
- exact full-entry source span;
- diagnostics when a heading, body, or attachment cannot be classified safely.

Parenthetical text containing digits or explicit scope language is not guessed to be an alias. It remains a qualifier. Definition continuations extend through subsequent non-heading nodes until the next definition entry or structural heading.

## Section review contract

A section review is self-contained. It records the exact section text, the corresponding span in the source ArticleSeed, and local spans addressing the section text.

Each review contains:

- ordered source-node projections;
- normative clauses split conservatively from non-note fragments;
- modality classified as requirement, prohibition, permission, nonrequirement, or unknown;
- exact modal, subject, predicate, and leading-condition spans when recognized;
- exception blocks kept separate from ordinary clauses;
- informational notes kept separate from normative content;
- code references;
- links to matched Article 100 definitions;
- semantic tags for authority approval, examination, installation, listing, connections, warnings, markings, and working space;
- diagnostics for ambiguous sentence boundaries, unclassified modal language, and table-like material.

The parser recognizes phrase precedence in this order:

1. `shall not be required` as nonrequirement;
2. `shall be permitted` as permission;
3. `shall not` as prohibition;
4. `shall` as requirement;
5. `may` as permission.

The parser does not determine project compliance, perform table lookups, infer omitted subjects, or resolve AHJ discretion into a yes/no conclusion.

## Article 90 language policy

Section 90.5 is reviewed with the same section contract. A derived language profile records evidence for mandatory, permissive, explanatory, and nonmandatory categories. Building the private bundle fails closed if the policy section does not contain evidence for the required modal phrases and explanatory-material marker.

## Initial reviewed corpus

The private generator produces:

- Article 100 definition index;
- section review for 90.5;
- section reviews for 110.2, 110.3, 110.14, 110.16, and 110.26.

This selection exercises approval, examination, installation instructions, listing, conductor connections, warning labels, exceptions, working-space geometry, and extensive subsection/list structure.

## Interfaces

Public entry points under `building_code_ast.nec`:

```python
build_definition_index(article_seed: Mapping[str, Any]) -> DefinitionIndex
build_section_review(
    article_seed: Mapping[str, Any],
    section_locator: str,
    *,
    definitions: DefinitionIndex | None = None,
) -> SectionReview
derive_language_profile(review: SectionReview) -> NecLanguageProfile
validate_definition_index(index: DefinitionIndex) -> None
validate_section_review(review: SectionReview) -> None
```

The private CLI reads existing ArticleSeed JSON files and writes deterministic JSON files plus a source-free manifest. It refuses to overwrite unexpected directory contents.

## Error handling

- Wrong article numbers fail with `ValueError`.
- Missing section locators fail with `ValueError`.
- Malformed ArticleSeed shapes fail before semantic output is produced.
- Every output is validated before serialization.
- Uncertain classification produces diagnostics and preserved evidence, not guessed semantics.
- Absolute local paths are never serialized.

## Testing

Public tests use only synthetic project-authored code-style text. They cover:

- definition headings, alternates, applicability qualifiers, continuation fragments, notes, panel markers, and references;
- deterministic identity and exact span round-tripping;
- section extent selection;
- modality precedence;
- conditions introduced by `if`, `when`, `where`, and `unless`;
- exception and informational-note separation;
- Article 100 definition linking;
- Section 90.5 language-profile derivation;
- fail-closed malformed inputs and safe force replacement;
- JSON Schema parseability and version alignment.

The supplied NEC PDF is used only for a private production smoke test. Generated text-bearing files are uploaded to the user's Google Drive and are not committed.

## Acceptance criteria

- Every Article 100 source block labeled `definition_entry` is either represented as a structured definition start or preserved as a continuation fragment. The current production result is 234 structured definitions with five false heading candidates retained as continuations.
- Definition and section-review spans round-trip to their source text.
- Section 90.5 yields a complete language profile.
- Reviews are generated for all five selected Article 110 sections.
- Notes and exceptions are not counted as ordinary normative clauses.
- Defined terms such as approval, listing, and identification link to Article 100 entries when exact term matching supports the link.
- Public tests and exact-head CI pass.
- No NEC source text or generated private semantic JSON appears in the Git diff.
