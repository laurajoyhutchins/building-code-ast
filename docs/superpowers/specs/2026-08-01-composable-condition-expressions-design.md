# Composable Provision Condition Expressions

Date: 2026-08-01
Status: Approved and self-reviewed design
Target provision AST version: `0.3.0`
Target package version: `0.3.0.dev0`
Related issue: #3

## Context

Provision AST `0.2.0` represents conditions as a flat tuple of numeric comparisons. That model cannot preserve whether multiple conditions are conjunctive or disjunctive, and it cannot later represent nested condition logic without another public-contract change.

This increment introduces a recursive condition-expression boundary while retaining the project's core constraints:

- exact source text remains authoritative evidence;
- every derived node has an exact source span;
- unsupported or ambiguous language remains explicit;
- parser output is not a compliance determination;
- the slice remains smaller than the full scope of issue #3.

## Decision

Provision AST `0.3.0` replaces `ProvisionAst.conditions` with a required nullable `ProvisionAst.condition` field.

A condition expression is either:

- one `ComparisonCondition` leaf;
- an `all_of` logical group;
- an `any_of` logical group.

The runtime model and JSON Schema permit recursive groups. The initial parser emits only one logical group level and only from homogeneous chains of the existing comparison grammar.

## Goals

1. Represent one comparison, conjunction, or disjunction without losing source order.
2. Preserve exact spans for leaves and groups.
3. Parse repeated `and` or repeated `or` chains conservatively.
4. Reject mixed, grouped, or malformed candidate chains without partial semantic output.
5. Make the breaking migration from provision AST `0.2.0` explicit.
6. Keep the document AST and unrelated semantic families unchanged.

## Non-goals

This slice does not add:

- general applicability or scope clauses;
- negated conditions;
- action alternatives or substitutions;
- inline exception expressions;
- definition resolution;
- reference graph resolution;
- calculations or table lookups;
- authority discretion;
- project-specific compliance evaluation;
- arbitrary Boolean-language parsing;
- new units, comparison operators, participles, or implied properties.

## Public contract

`ProvisionAst` changes from:

```python
conditions: tuple[ComparisonCondition, ...] = ()
```

to:

```python
condition: ConditionExpression | None = None
```

The serialized top-level `condition` property is required. A provision with no recognized structured condition serializes `"condition": null`.

The old `conditions` property is removed rather than retained as a competing representation.

### Comparison condition

The existing comparison leaf shape remains:

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

### Logical condition

```json
{
  "type": "all_of",
  "operands": [
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
    },
    {
      "type": "comparison",
      "subject_property": "floor area",
      "operator": ">",
      "threshold": {
        "value": 20000.0,
        "unit": "ft2",
        "original_text": "exceeding 20000 square feet in floor area"
      },
      "span": {
        "start": 53,
        "end": 98,
        "text": "exceeding 20000 square feet in floor area"
      }
    }
  ],
  "span": {
    "start": 20,
    "end": 98,
    "text": "exceeding 40 feet in height and exceeding 20000 square feet in floor area"
  }
}
```

`all_of` represents a repeated `and` chain. `any_of` represents a repeated `or` chain. Every logical group contains at least two operands.

## Runtime model

The Python model introduces exactly:

```python
class LogicalConditionType(StrEnum):
    ALL_OF = "all_of"
    ANY_OF = "any_of"


@dataclass(frozen=True, slots=True)
class LogicalCondition:
    type: LogicalConditionType
    operands: tuple[ComparisonCondition | LogicalCondition, ...]
    span: SourceSpan


ConditionExpression = ComparisonCondition | LogicalCondition
```

`LogicalCondition.to_dict()` serializes the enum value and recursively serializes operands in source order.

The object model has value semantics. Shared Python object identity is not part of the public contract. Validation rejects actual recursion cycles by tracking the active recursion path, but it does not reject finite reuse of an equivalent subtree merely because two references point to the same Python object.

## Parser grammar

The parser continues to recognize the existing single comparison tail:

```text
<regulated subject> <comparison clause>
```

It additionally recognizes a homogeneous chain:

```text
<regulated subject> <comparison clause> (<connector> <comparison clause>)+
```

Supported connectors are case-insensitive whole words `and` and `or`.

Each clause must independently match the existing numeric comparison grammar in full. The slice does not add units, operators, clause-introducing participles, or implied values or properties.

Reviewed examples are:

```text
Research facilities exceeding 40 feet in height and exceeding 20000 square feet in floor area shall provide two marked evacuation routes.
```

```text
Research facilities exceeding 40 feet in height or exceeding 20000 square feet in floor area shall provide two marked evacuation routes.
```

The parser locates the first supported threshold marker in the pre-modal text. Text before that marker is the regulated subject candidate. Text from that marker to the modal is the condition candidate tail.

For a homogeneous chain, the parser splits on the repeated connector while preserving absolute offsets. Every resulting segment must match the comparison grammar in full. A successful single comparison produces a `ComparisonCondition`. A successful chain produces one `LogicalCondition` whose operands are the parsed comparisons.

## Failure behavior and diagnostic precedence

Condition parsing is all-or-nothing. At most one condition-specific diagnostic is emitted for a candidate tail.

When more than one rejection rule applies, the parser uses this fixed precedence:

1. `unsupported-condition-grouping` when the candidate contains `(` or `)`;
2. `ambiguous-condition-connectors` when the remaining candidate contains both whole-word `and` and whole-word `or`;
3. `unsupported-condition-clause` when a single candidate clause or any segment of a homogeneous chain fails full comparison matching.

This order is part of the parser contract and fixture expectations.

### No candidate marker

When the pre-modal text contains no supported threshold marker:

- the complete pre-modal text remains the subject;
- `condition` is `null`;
- the parser emits the existing `no-structured-condition` informational diagnostic.

### Unsupported grouping

When a candidate tail contains `(` or `)`:

- the complete pre-modal text remains the subject;
- `condition` is `null`;
- the parser emits `unsupported-condition-grouping` as a warning over the candidate tail;
- no partial comparison is emitted;
- no lower-precedence condition diagnostic is emitted;
- `no-structured-condition` is not emitted.

### Mixed connectors

When a non-parenthesized candidate tail contains both whole-word `and` and whole-word `or`:

- the complete pre-modal text remains the subject;
- `condition` is `null`;
- the parser emits `ambiguous-condition-connectors` as a warning over the candidate tail;
- no partial comparison is emitted;
- no lower-precedence condition diagnostic is emitted;
- `no-structured-condition` is not emitted.

### Unsupported clause

When a single candidate clause does not fully match the comparison grammar, or any segment of a homogeneous chain fails full matching:

- the complete pre-modal text remains the subject;
- `condition` is `null`;
- the parser emits `unsupported-condition-clause` as a warning over the candidate tail;
- no partial comparison is emitted;
- `no-structured-condition` is not emitted.

Specific condition diagnostics may coexist with independent action diagnostics. The existing missing-modality path remains unchanged and does not attempt condition parsing.

## Source-span invariants

Every condition node must round-trip to the exact original source text.

For every comparison leaf:

- `span` covers the complete comparison clause;
- `source_text[span.start:span.end] == span.text`;
- `threshold.original_text == span.text`;
- offsets address the unmodified provision source.

For every logical group:

- the group span starts exactly at the first operand start;
- the group span ends exactly at the last operand end;
- the group span includes connectors and intervening source text;
- every operand is contained in the group span;
- operands appear in strictly increasing source order;
- operand spans do not overlap.

When condition parsing succeeds, `subject` and `subject_span` exclude the complete condition tail. When a candidate tail is rejected, `subject` and `subject_span` cover the complete pre-modal text so unsupported language is not silently discarded.

## Runtime validation

Validation recursively checks:

- each expression is a `ComparisonCondition` or `LogicalCondition`;
- every node span round-trips to `source_text`;
- every comparison operator is supported;
- every comparison has `threshold.original_text == span.text`;
- every logical type is `ALL_OF` or `ANY_OF`;
- every logical group has at least two operands;
- every child span is contained in its parent span;
- child spans are strictly source ordered and non-overlapping;
- each group start equals its first operand start;
- each group end equals its last operand end;
- no object on the active recursion path is visited again.

`condition: null` is structurally valid. Validation does not infer whether source text should have produced a condition, and it does not inspect connector wording to prove semantic equivalence between source prose and a logical tag. Those are parser and review responsibilities.

## JSON Schema

`schemas/provision-ast.schema.json` advances to provision AST `0.3.0` and:

- changes `ast_version` to `0.3.0`;
- replaces required `conditions` with required `condition`;
- defines `condition` as comparison, logical group, or `null`;
- defines recursive logical operands through `$ref`;
- requires at least two operands;
- restricts logical `type` to `all_of` or `any_of`;
- keeps `additionalProperties: false` throughout;
- retains all existing source, modality, subject, action, exception, and diagnostic fields.

## Fixtures and tests

The implementation adds or updates reviewed synthetic fixtures for:

1. one comparison;
2. two comparisons joined by `and`;
3. two comparisons joined by `or`;
4. three homogeneous comparisons;
5. mixed `and` and `or`;
6. one malformed single comparison candidate;
7. one malformed clause in a homogeneous chain;
8. parenthesized grouping;
9. a candidate with both grouping and mixed connectors to prove diagnostic precedence;
10. the existing threshold-with-exception fixture migrated to `condition`;
11. a provision with no condition candidate.

Tests cover:

- exact expected JSON for reviewed fixtures;
- deterministic serialization and operand order;
- leaf and group span round-tripping;
- exact group boundary equality;
- containment, ordering, and non-overlap;
- rejection of a mismatched `threshold.original_text`;
- rejection of malformed logical groups;
- active-path cycle detection;
- deterministic condition diagnostic precedence;
- specific condition diagnostics without redundant `no-structured-condition` output;
- preservation of source identity and exact whitespace;
- unchanged modality, action, exception, and missing-modality behavior.

## Compatibility

Provision AST `0.3.0` is intentionally incompatible with `0.2.0` because:

- `conditions` is removed;
- `condition` may be a recursive expression or `null`;
- consumers must handle logical groups.

Migration is deterministic only for these valid `0.2.0` values:

- zero `conditions` becomes `condition: null`;
- one condition becomes that comparison object as `condition`.

More than one `conditions` value cannot be migrated safely because `0.2.0` did not encode conjunction or disjunction. Migration must fail and require source re-parsing or human review.

No automatic migration utility is required in this slice. `docs/compatibility.md` must state the rule explicitly.

## Implementation boundaries

The implementation changes only:

- `src/building_code_ast/model.py`;
- `src/building_code_ast/parser.py`;
- `src/building_code_ast/validation.py`;
- `schemas/provision-ast.schema.json`;
- provision fixtures and tests;
- `README.md`;
- `docs/compatibility.md`;
- `pyproject.toml`, advancing the package version to `0.3.0.dev0`.

The document AST and its schema, fixtures, validation, and documentation remain unchanged.

## Verification

The implementation is complete when all of the following pass on Python 3.12:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -c "import json; json.load(open('schemas/provision-ast.schema.json', encoding='utf-8'))"
```

All reviewed fixtures must match deterministic parser output, and GitHub Actions must pass at the exact pull-request head.

## Acceptance criteria

- Provision AST reports version `0.3.0`.
- Package metadata reports `0.3.0.dev0`.
- Public output contains required nullable `condition`, not `conditions`.
- Single comparisons and homogeneous `all_of` or `any_of` groups parse deterministically.
- Mixed, grouped, or malformed candidate chains produce exactly one specific condition diagnostic and no partial expression.
- Diagnostic precedence is deterministic when multiple rejection rules apply.
- Every condition span round-trips to the original source.
- Comparison evidence text and logical group boundaries are validated exactly.
- Logical operands are ordered, contained, and non-overlapping.
- Existing non-condition behavior remains covered by regression tests.
- Documentation states the breaking migration boundary.
- No project-specific compliance conclusion is introduced.
