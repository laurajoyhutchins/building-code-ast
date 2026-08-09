# Source structural metadata

Status: implemented on this branch.

## Purpose

Add publication-neutral structural observations and explicitly derived structural candidates to retrieval evidence without assigning provision semantics, authority, or publication roles.

## Owns

`annotate_structural_metadata()` preserves the existing evidence identity while adding:

Observed metadata:

- physical page width and height
- bbox width/height and origin when a bbox exists
- optional font size and font name supplied by a positioned extractor
- previously recorded observed metadata without mutation

Derived metadata:

- normalized bbox position and size fractions
- optional font-size ratio to an explicitly supplied body-font estimate
- closed boolean structural candidate flags for heading, table, figure, and equation
- previously recorded derived metadata without mutation

Structural metadata collisions fail closed rather than silently overwriting prior observations.

## Candidate boundary

Candidate flags are investigation aids, not parser truth. They do not create Document AST nodes or assign requirement, exception, definition, commentary, mandatory, informative, normative, or other code semantics.

Heading candidates use only bounded generic typography/text-shape evidence. Table, figure, and equation candidates use conservative publication-neutral source-form prefixes. Arbitrary prose containing an equals sign is not promoted to an equation candidate.

All structural metadata is identity-neutral: exact source artifact and physical coordinates remain the durable evidence identity.

## TDD evidence

RED head: `550d801c680c4287cf8ebfbc396ea143310723a0`.

At RED, 378 inherited tests passed and CI failed only because `building_code_ast.retrieval.structural` did not yet exist.

First GREEN implementation head: `6254c370aafe364205460fd72d6ab0ccc0b9ae43`.

Fresh checks on that exact head:

- CI: success
- LORE: success
- Deciduous archaeology: success

Behavioral coverage includes observed-versus-derived separation, font-relative heading candidates, table/figure/equation candidates, all-caps heading candidates without font data, rejection of arbitrary equation-like prose, identity stability, and fail-closed geometry/font/metadata conflicts.

## Excludes

- provision semantics
- publication roles
- AST construction
- authority inference
- parser confidence
- semantic search

## Stack

Predecessor: `feature/source-lexical-search` / PR #91.

Successor: `feature/source-structural-search` / PR #96.
