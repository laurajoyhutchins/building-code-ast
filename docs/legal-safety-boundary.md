# Legal and Product-Safety Boundary

Building Code AST represents language; it does not establish the controlling law or decide compliance.

## Required distinctions

Downstream systems must preserve the difference among:

1. source text;
2. deterministic normalization;
3. parser inference;
4. unresolved ambiguity;
5. human-reviewed interpretation;
6. project facts supplied for evaluation;
7. a resulting machine evaluation;
8. a professional or authority determination.

These categories must not collapse into a single confidence score or Boolean answer.

## Discretionary language

Terms such as "approved," "adequate," "where necessary," or language dependent on the building official remain explicit unresolved or discretionary nodes. They are not automatically converted into true or false predicates.

## Failure behavior

When a provision is unsupported or ambiguous, the preferred behavior is:

- preserve the source text;
- emit a stable diagnostic;
- identify the unsupported span;
- avoid a compliance conclusion;
- permit later review or parser improvement.

Silently producing a plausible AST is a failure mode.

## User-facing claims

Interfaces using this project should state the source edition, jurisdictional assumptions, parser version, review status, missing facts, and unresolved terms near any result. A generic disclaimer does not repair missing provenance or unsupported certainty.
