# Composable Provision Condition Expressions

Date: 2026-08-01
Status: Approved design
Target provision AST version: `0.3.0`
Related issue: #3

## Context

Provision AST `0.2.0` represents conditions as a flat tuple of numeric comparisons. That model cannot preserve whether multiple conditions are conjunctive or disjunctive, and it cannot later represent nested condition logic without another public-contract change.

The next increment adds enough structure to represent deterministic conjunction and disjunction while retaining the project's core boundaries:

- exact source text remains authoritative evidence;
- every derived node has an exact source span;
- unsupported or ambiguous language remains explicit;
- parser output is not a compliance determination;
- the change stays smaller than the full scope of issue #3.

## Goals

1. Introduce a recursive condition-expression contract.
2. Represent one comparison, an `all_of` conjunction, or an `any_of` disjunction.
3. Parse a bounded family of compatible numeric threshold clauses joined by one repeated connector.
4. Preserve exact source spans for comparison leaves and logical groups.
5. Diagnose mixed or malformed candidate groups instead of inventing precedence or returning partial meaning.
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

A top-level field such as `condition_operator: "and" | "or"` would represent one homogeneous list. It would not support nesting, would create another breaking change later, and would couple logical meaning to array position. Rejected.

### 2. Introduce recursive condition expressions

A tagged union represents comparison leaves and logical groups. It is slightly more verbose, but it preserves structure, supports future nesting, and gives validation a clear recursive boundary. Selected.

### 3. Add a general expression language now

A broad expression grammar could include negation, references, calculations, and arbitrary nesting immediately. That would exceed the reviewed corpus and invite false confidence. Rejected.

## Public contract

`ProvisionAst.conditions` is replaced by a required nullable `condition` field.

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

Logical group types are:

- `all_of` for repeated `and` connectors;
- `any_of` for repeated `or` connectors.

Each logical group must contain at least two operands. The initial parser emits only one logical level. The runtime model, validator, and JSON Schema allow recursive operands so later parser slices do not require another contract redesign.

## Parser grammar

The parser continues to recognize the existing single comparison tail:

```text
<regulated subject> <comparison clause>
```

It additionally recognizes a homogeneous chain:

```text
<regulated subject> <comparison clause> (<connector> <comparison clause>)+
```

Supported connectors are case-insensitive `and` and `or`.

Each clause must independently match the existing numeric threshold grammar. This slice does not add new units, operators, clause-introducing participles, or implied properties.

The first reviewed examples are:

```text
Research facilities exceeding 40 feet in height and exceeding 20000 square feet in floor area shall provide two marked evacuation routes.
```

```text
Research facilities exceeding 40 feet in height or exceeding 20000 square feet in floor area shall provide two marked evacuation routes.
```

The parser locates the first supported threshold marker in the pre-modal subject text. Text before that marker remains the regulated subject. The candidate condition tail begins at that marker.

For a homogeneous chain, the parser splits the candidate tail on the connector while preserving each segment's absolute source offsets. Every segment must match the comparison grammar in full. The parser must not infer omitted properties, units, values, or operators.

## Ambiguity and failure behavior

The parser fails visibly rather than assigning conventional Boolean precedence.

For a candidate tail containing both `and` and `or`, the parser:

1. preserves the entire pre-modal text as the subject;
2. returns `condition: null`;
3. emits an `ambiguous-condition-connectors` warning spanning the candidate tail;
4. does not emit partially trusted comparison nodes.

Parentheses are not interpreted in this slice. A parenthesized candidate tail receives an `unsupported-condition-grouping` warning, preserves the entire pre-modal text as the subject, and returns `condition: null`.

If one clause in a homogeneous chain does not match the bounded comparison grammar, the parser emits `unsupported-condition-clause` over the candidate tail, preserves the entire pre-modal text as the subject, and returns `condition: null`.

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

When a condition is recognized, the regulated `subject` and `subject_span` exclude the complete condition tail. When a candidate group is rejected, the complete pre-modal text remains the subject so the parser does not silently discard unsupported language.

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

`ProvisionAst` changes from:

```python
conditions: tuple[ComparisonCondition, ...] = ()
```

to:

```python
condition: ConditionExpression | None = None
```

The old `conditions` tuple is removed from `ProvisionAst` in `0.3.0` rather than retained as a competing representation.

Serialization remains deterministic and preserves operand order from the source. `LogicalCondition.to_dict()` serializes `type` to its string value and recursively serializes operands.

## Validation

Runtime validation recursively checks:

- the expression is a `ComparisonCondition` or `LogicalCondition`;
- every node span round-trips to the exact source text;
- comparison operators remain in the supported set;
- logical types are `ALL_OF` or `ANY_OF`;
- every logical group has at least two operands;
- child spans are contained in the parent group span;
- child spans appear in strictly increasing source order;
- child spans do not overlap;
- the same in-memory logical node is not revisited during one validation traversal.

`condition: null` is structurally valid. Validation does not infer whether the source should have produced a condition. That remains parser behavior, not an AST invariant.

Validation does not attempt to prove semantic equivalence between the wording and the parsed expression. It proves structural and provenance invariants only.

## JSON Schema

`schemas/provision-ast.schema.json` advances to provision AST `0.3.0` and:

- replaces required `conditions` with required `condition`;
- defines `condition` as comparison, logical group, or `null`;
- defines recursive logical operands using `$ref`;
- requires at least two operands;
- restricts logical `type` to `all_of` or `any_of`;
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
- cycle detection in recursive logical nodes;
- deterministic serialization;
- preservation of source identity and exact whitespace;
- unchanged modality, action, exception, and diagnostic behavior outside the condition contract.

## Compatibility

Provision AST `0.3.0` is intentionally incompatible with `0.2.0` because:

- `conditions` is removed;
- `condition` may be a recursive expression or `null`;
- consumers must handle logical groups.

Migration for a valid `0.2.0` object is deterministic only in these cases:

- zero `conditions` becomes `condition: null`;
- one condition becomes that comparison object as `condition`.

More than one `conditions` value cannot be migrated safely because `0.2.0` did not encode conjunction or disjunction. Migration must fail and require source re-parsing or human review.

No automatic migration utility is required in this slice. Compatibility documentation must state this rule explicitly.

## Implementation boundaries

The change remains focused in:

- `src/building_code_ast/model.py`;
- `src/building_code_ast/parser.py`;
- `src/building_code_ast/validation.py`;
- `schemas/provision-ast.schema.json`;
- provision fixtures and tests;
- `README.md` and `docs/compatibility.md`;
- `pyproject.toml` if the package version must advance with the semantic contract.

Unrelated document AST code remains unchanged.

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
