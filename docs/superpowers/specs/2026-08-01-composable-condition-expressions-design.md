# Composable Provision Condition Expressions

Date: 2026-08-01
Status: Approved design
Target provision AST version: `0.3.0`
Related issue: #3

## Context

Provision AST `0.2.0` represents conditions as a flat tuple of numeric comparisons. That model cannot preserve whether multiple conditions are conjunctive or disjunctive, and it cannot later represent nested condition logic without changing the public contract.

The next increment should add enough structure to represent deterministic conjunction and disjunction while retaining the project's core boundaries:

- exact source text remains authoritative evidence;
- every derived node has an exact source span;
- unsupported or ambiguous language remains explicit;
- parser output is not a compliance determination;
- the change stays smaller than the full scope of issue #3.

## Goals

1. Introduce a recursive condition-expression contract.
2. Represent one comparison, an `all_of` conjunction, or an `any_of` disjunction.
3. Parse a bounded family of two-or-more compatible numeric threshold clauses joined by one repeated conjunction.
4. Preserve exact source spans for comparison leaves and logical groups.
5. Reject or diagnose ambiguous mixed conjunctions rather than inventing precedence.
6. Version the semantic contract explicitly as provision AST `0.3.0`.
7. Update runtime models, validation, JSON Schema, fixtures, tests, and compatibility documentation together.

## Non-goals

This slice does not add:

- general applicability or scope clauses;
- negated conditions;
- alternatives or substitutions in the action;
- inline exception expressions;
- definition resolution;
- section-reference graph resolution;
- calculations or table lookups;
- authority discretion;
- project-specific compliance evaluation;
- arbitrary natural-language Boolean parsing.

These remain later slices of issue #3 or subsequent graph work.

## Approaches considered

### 1. Keep the flat condition array and add a connector field

A top-level field such as `condition_operator: "and" | "or"` would minimally represent one homogeneous list. It would not support nesting, would create another breaking change later, and would couple logical meaning to array position. Rejected.

### 2. Introduce recursive condition expressions

A tagged union represents comparison leaves and logical groups. It is slightly more verbose, but it preserves structure, supports future nesting, and gives validation a clear recursive boundary. Selected.

### 3. Add a general expression language now

A broad expression grammar could include negation, references, calculations, and arbitrary nesting immediately. That would exceed the reviewed corpus and invite false confidence. Rejected.

## Public contract

`ProvisionAst.conditions` is replaced by a nullable `condition` field.

A provision with no recognized structured condition has `condition: null` and retains the existing informational diagnostic.

A condition expression is one of the following tagged node families.

### Comparison condition

```json
{
  "type": "comparison",
  "subject_property": "height",
  "operator": ">",
  "threshold": {
    "value": 40.0,
    "unit": "ft",
    "original_text": "exceeding 40 feet in height"
  },
  "span": {
    "start": 20,
    "end": 48,
    "text": "exceeding 40 feet in height"
  }
}
```

### Logical condition group

```json
{
  "type": "all_of",
  "operands": [
    { "type": "comparison", "...": "..." },
    { "type": "comparison", "...": "..." }
  ],
  "span": {
    "start": 20,
    "end": 89,
    "text": "exceeding 40 feet in height and containing at least 3 stories"
  }
}
```

Logical group types are:

- `all_of` for repeated `and` connectors;
- `any_of` for repeated `or` connectors.

Each logical group must contain at least two operands. The initial parser emits only one logical level, but the runtime model, validator, and JSON Schema allow recursive operands so future parser slices do not require another contract redesign.

## Parser grammar

The parser recognizes subject tails containing one or more comparison clauses in this bounded form:

```text
<regulated subject> <comparison clause> (<connector> <comparison clause>)+
```

Supported connectors are case-insensitive `and` and `or`.

Each clause must independently match the existing numeric threshold grammar, extended only as needed to recognize repeated clauses such as:

```text
Research facilities exceeding 40 feet in height and containing at least 3 stories
```

The parser may recognize a clause-introducing participle such as `containing` only when the remainder still matches the reviewed threshold pattern. The parser must not infer omitted properties, units, values, or operators.

The first reviewed examples are:

```text
Research facilities exceeding 40 feet in height and containing at least 3 stories shall provide two marked evacuation routes.
```

```text
Research facilities exceeding 40 feet in height or containing at least 3 stories shall provide two marked evacuation routes.
```

## Ambiguity and failure behavior

The parser fails visibly rather than assigning conventional Boolean precedence.

For a subject tail containing both `and` and `or` without explicit supported grouping, the parser:

1. preserves the entire subject text;
2. returns `condition: null`;
3. emits an `ambiguous-condition-connectors` warning spanning the candidate condition tail;
4. does not emit partially trusted comparison nodes.

Parentheses are not interpreted in this slice. A parenthesized condition candidate remains unsupported and receives an `unsupported-condition-grouping` warning.

If one clause in a homogeneous chain does not match the bounded comparison grammar, the parser does not emit a partial logical group. It preserves the subject and emits `unsupported-condition-clause` over the candidate tail.

This all-or-nothing rule prevents a partially parsed condition from appearing more complete than the source supports.

## Source-span invariants

Every condition node must round-trip to the exact original source text.

For comparison leaves:

- `span` covers the complete comparison clause;
- `threshold.original_text` equals the comparison span text;
- offsets address the unmodified provision source.

For logical groups:

- `span` starts at the first operand start;
- `span` ends at the last operand end;
- the span includes the literal connectors and intervening source text;
- every operand span is contained within the group span;
- operands appear in strictly increasing source order;
- operand spans do not overlap.

The regulated `subject` and `subject_span` exclude the recognized condition tail, preserving the existing semantic boundary.

## Runtime model

The Python model introduces:

- a `ConditionExpression` type alias or protocol-compatible union;
- `ComparisonCondition` as the existing leaf type;
- `LogicalConditionType` with `ALL_OF` and `ANY_OF` values, or equivalent literal tagging;
- `LogicalCondition` with `type`, recursive `operands`, and `span`;
- `ProvisionAst.condition: ConditionExpression | None`.

The old `conditions` tuple is removed from `ProvisionAst` in `0.3.0` rather than retained as a competing representation.

Serialization remains deterministic and preserves operand order from the source.

## Validation

Runtime validation recursively checks:

- supported node type;
- exact source-span round-tripping;
- supported comparison operators;
- at least two logical operands;
- child containment in the parent group span;
- source-order monotonicity;
- non-overlapping operands;
- no object cycles in the in-memory expression graph;
- `condition is None` when no structured condition was recognized.

Validation does not attempt to prove semantic equivalence between the source wording and the parsed expression. It proves structural and provenance invariants only.

## JSON Schema

`schemas/provision-ast.schema.json` advances to provision AST `0.3.0` and:

- replaces required `conditions` with required `condition`;
- defines `condition` as comparison, logical group, or `null`;
- defines recursive logical operands using `$ref`;
- requires at least two operands;
- keeps `additionalProperties: false` throughout;
- retains all existing provenance, modality, subject, action, exception, and diagnostic fields.

## Fixtures and tests

The implementation adds reviewed synthetic fixtures for:

1. two comparisons joined by `and`;
2. two comparisons joined by `or`;
3. three homogeneous comparisons to verify operand ordering;
4. mixed `and` and `or`, producing no structured condition;
5. one malformed clause in an otherwise homogeneous chain;
6. parenthesized grouping, explicitly unsupported;
7. the existing single threshold with exception, migrated to the new `condition` field;
8. provisions with no structured condition, producing `condition: null`.

Tests cover:

- exact expected JSON for reviewed fixtures;
- recursive validation;
- group and leaf span round-tripping;
- group containment and operand ordering;
- malformed logical groups rejected by validation;
- deterministic serialization;
- preservation of source identity and exact whitespace;
- unchanged modality, action, exception, and diagnostic behavior outside the condition contract.

## Compatibility

Provision AST `0.3.0` is intentionally incompatible with `0.2.0` because:

- `conditions` is removed;
- `condition` may be a recursive expression or `null`;
- consumers must handle logical groups.

Migration for a valid `0.2.0` object is deterministic:

- zero `conditions` becomes `condition: null`;
- one condition becomes that comparison object as `condition`;
- more than one `conditions` value cannot be migrated safely because `0.2.0` did not encode conjunction or disjunction. Migration must fail and require source re-parsing or human review.

No automatic migration utility is required in this slice, but the compatibility documentation must state this rule explicitly.

## Implementation boundaries

The change should remain focused in:

- `src/building_code_ast/model.py`;
- `src/building_code_ast/parser.py`;
- `src/building_code_ast/validation.py`;
- `schemas/provision-ast.schema.json`;
- provision fixtures and tests;
- `README.md` and `docs/compatibility.md`;
- package version metadata if needed to keep the public package and AST documentation aligned.

Unrelated document AST code must remain unchanged.

## Verification

The implementation is complete when:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

pass on Python 3.12, the schema parses as JSON, all reviewed fixtures match deterministic parser output, and CI passes at the exact pull-request head.

## Acceptance criteria

- Provision AST reports version `0.3.0`.
- Public output contains `condition`, not `conditions`.
- Single comparisons and homogeneous `all_of` or `any_of` groups parse deterministically.
- Mixed or malformed candidate groups produce diagnostics and no partial expression.
- Every condition span round-trips to the original source.
- Logical operands are ordered, contained, and non-overlapping.
- Existing non-condition behavior remains covered by regression tests.
- Documentation states the breaking migration boundary.
- No project-specific compliance conclusion is introduced.
