# Composable Condition Expressions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Advance provision AST to `0.3.0` with provenance-preserving comparison leaves and recursive `all_of` / `any_of` expressions while rejecting ambiguous language without partial semantic output.

**Architecture:** Replace the flat condition tuple with a tagged recursive expression model. Validate every expression recursively against exact source spans. Extend the deterministic parser only to homogeneous chains of the existing numeric comparison grammar. Keep the document AST unchanged.

**Tech Stack:** Python 3.12, standard-library `dataclasses`, `enum.StrEnum`, `re`, `unittest`, JSON Schema Draft 2020-12, GitHub Actions.

## Global Constraints

- Provision AST version is exactly `0.3.0`.
- Package version is exactly `0.3.0.dev0`.
- Runtime dependencies remain empty.
- Public JSON contains required nullable `condition` and no `conditions` property.
- Supported markers, units, operators, and property grammar remain unchanged.
- Parentheses, mixed connectors, and malformed clauses produce one specific warning and no partial expression.
- Rejection precedence is grouping, then mixed connectors, then unsupported clause.
- Every leaf and group span addresses the exact unmodified source.
- Document AST source, schema, fixtures, validation, and documentation remain unchanged.

---

## File Map

- `src/building_code_ast/model.py`: condition expression types and serialization.
- `src/building_code_ast/validation.py`: recursive provenance and structural validation.
- `src/building_code_ast/parser.py`: candidate-tail recognition and diagnostic precedence.
- `schemas/provision-ast.schema.json`: external provision AST `0.3.0` contract.
- `tests/test_conditions.py`: model, validation, and parser behavior tests.
- `tests/test_condition_fixtures.py`: exact reviewed fixture and schema tests.
- `tests/test_parser.py`: legacy provision regressions migrated to `condition`.
- `fixtures/conditions.json`: reviewed exact-output condition corpus.
- `fixtures/expected/threshold-with-exception.json`: migrated legacy reviewed fixture.
- `README.md`, `docs/compatibility.md`, `pyproject.toml`: public behavior and version boundary.

### Task 1: Recursive public model and schema

**Interfaces:**

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

`ProvisionAst.condition` is `ConditionExpression | None`; `to_dict()` always emits `condition` and never emits `conditions`.

- [x] Write a failing serialization test using exact offsets: first comparison `6:33`, second comparison `38:79`, group `6:79`, modality `80:85`, action `86:101`.
- [x] Verify CI fails because `LogicalCondition` is absent.
- [x] Add `LogicalConditionType`, `LogicalCondition`, `ConditionExpression`, and AST version `0.3.0`.
- [x] Replace the schema array with recursive `conditionExpression` and `logicalCondition` definitions.
- [x] Migrate the existing parser call site, regression tests, and threshold fixture mechanically to the new field.
- [x] Verify the model and migrated regressions pass.

### Task 2: Recursive fail-closed validation

**Validator requirements:**

- validate each condition span against `source_text`;
- require supported comparison operators;
- require `threshold.original_text == comparison.span.text`;
- require enum-backed logical types and at least two operands;
- require child containment, strict source order, and non-overlap;
- require group start/end equality with first/last operands;
- reject only active-path recursion cycles;
- accept `condition=None` as structurally valid.

- [x] Add failing tests for evidence mismatch, wide group start, reversed operands, and active-path cycles.
- [x] Replace obsolete `ast.conditions` traversal with `_validate_condition(...)`.
- [x] Verify all model, validation, document, and legacy provision tests pass.

### Task 3: Homogeneous chain parsing and diagnostic precedence

**Parser interface:**

```python
def _extract_condition(
    source: str,
    subject_start: int,
    subject_text: str,
) -> tuple[
    str,
    SourceSpan | None,
    ConditionExpression | None,
    tuple[Diagnostic, ...],
]:
    ...
```

**Algorithm:**

1. Find the first supported threshold marker in pre-modal text.
2. Preserve the complete pre-modal subject and emit `condition=None` if no marker exists.
3. Reject any candidate containing `(` or `)` as `unsupported-condition-grouping`.
4. Reject a remaining candidate containing both whole-word `and` and `or` as `ambiguous-condition-connectors`.
5. Split a homogeneous chain on the repeated connector while preserving absolute offsets.
6. Require every segment to fully match the existing comparison regex.
7. Emit one comparison leaf or one `LogicalCondition` spanning first operand start through last operand end.
8. On any rejection, preserve the full pre-modal text as subject and suppress `no-structured-condition`.

- [x] Add failing tests for single leaves, `all_of`, `any_of`, three operands, grouping precedence, mixed-connector precedence, malformed candidates, and no-marker behavior.
- [x] Verify only the six new parser behaviors fail.
- [x] Implement whole-word marker/connector recognition and all-or-nothing parsing.
- [x] Verify all 33 tests and compilation pass.
- [x] Add `fixtures/conditions.json` with exact outputs for success and rejection cases.
- [x] Add fixture and schema contract tests.
- [x] Verify exact-output fixtures pass.

### Task 4: Publish compatibility and verify exact head

- [x] Set package version to `0.3.0.dev0`.
- [x] Update README with recursive condition behavior and explicit rejection diagnostics.
- [x] Document deterministic and non-deterministic migration cases from `0.2.0`.
- [x] Keep runtime dependencies empty and Python support at `>=3.12,<3.13`.
- [ ] Run final exact-head verification:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -c "import json; json.load(open('schemas/provision-ast.schema.json', encoding='utf-8'))"
python -c "from building_code_ast.model import AST_VERSION; assert AST_VERSION == '0.3.0'"
python -c "import pathlib; assert 'version = \"0.3.0.dev0\"' in pathlib.Path('pyproject.toml').read_text()"
```

- [ ] Self-review the exact PR head for contract drift, parser overreach, span defects, and unrelated changes.
- [ ] Mark PR ready only after exact-head CI passes and no critical or important issue remains.
