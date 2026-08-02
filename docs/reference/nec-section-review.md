# NEC Section Review Reference

The NEC section review contract is a source-backed intermediate representation for selected NEC sections. It records clause-level evidence, modalities, conditions, exceptions, notes, references, semantic tags, and links to structured Article 100 definitions.

A section review is **not a compliance determination**, an applicability decision, or an authoritative interpretation. It does not calculate values, evaluate tables, resolve authority discretion, or decide whether a project satisfies the Code.

## Contract

Version `0.1.0` contains:

- exact section source text and immutable artifact and edition identity;
- the article-relative source interval and section locator;
- the exact section title;
- projections of the source document nodes used to build the review;
- reviewed normative clauses;
- exceptions and informational notes kept separate from clauses;
- explicit section, article, and table references;
- diagnostics for unsupported or uncertain structures.

Clause identity is deterministic from artifact, edition, section locator, and exact clause span. The supported reviewed modalities are `requirement`, `prohibition`, `permission`, `nonrequirement`, and `unknown`.

## Language policy

The companion NEC language profile is derived from reviewed Section 90.5 evidence. It records mandatory, permissive, explanatory, and nonmandatory phrases without replacing the exact 90.5 source evidence. Modal classification uses explicit precedence so phrases such as `shall not be required` are not misclassified as prohibitions.

## Definition links

A clause may link to exact Article 100 definition identities when a canonical, display, or explicitly recorded alternate term occurs in the clause text. A link shows lexical evidence, not proof that the definition controls the clause in every context.

The JSON projections are specified by:

- `schemas/nec-section-review.schema.json`
- `schemas/nec-language-profile.schema.json`
