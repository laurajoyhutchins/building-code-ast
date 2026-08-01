# Composable Condition Expressions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Advance provision AST to `0.3.0` with provenance-preserving single comparisons and recursive `all_of` / `any_of` condition expressions while rejecting ambiguous candidate language without partial semantic output.

**Architecture:** Keep the existing deterministic parser boundary. Replace the flat condition tuple with a tagged recursive expression model, validate its source spans recursively, and extend only the existing numeric threshold grammar into homogeneous connector chains. The document AST remains untouched.

**Tech Stack:** Python 3.12, standard-library `dataclasses`, `enum.StrEnum`, `re`, `unittest`, JSON Schema Draft 2020-12, GitHub Actions.

## Global Constraints

- Provision AST version is exactly `0.3.0`.
- Package version is exactly `0.3.0.dev0`.
- Runtime dependencies remain empty.
- Public JSON contains required nullable `condition` and does not contain `conditions`.
- Parser support remains limited to the existing numeric units, markers, operators, and properties.
- Parentheses, mixed connectors, and malformed clauses produce one specific warning and no partial condition expression.
- Diagnostic precedence is grouping, then mixed connectors, then unsupported clause.
- Every leaf and group span addresses the exact unmodified source text.
- The document AST and all document-specific files remain unchanged.

---

## File Map

- `src/building_code_ast/model.py`: public provision condition types and deterministic serialization.
- `src/building_code_ast/validation.py`: recursive structural and provenance validation.
- `src/building_code_ast/parser.py`: bounded condition-tail recognition and diagnostic precedence.
- `schemas/provision-ast.schema.json`: external `0.3.0` contract.
- `tests/test_parser.py`: existing regression tests migrated to `condition`.
- `tests/test_conditions.py`: focused parser and validator coverage for condition expressions.
- `fixtures/expected/threshold-with-exception.json`: existing reviewed fixture migrated to `0.3.0`.
- `README.md`, `docs/compatibility.md`, `pyproject.toml`: public behavior and version boundary.

### Task 1: Introduce the recursive public model and schema

**Files:**
- Modify: `src/building_code_ast/model.py`
- Modify: `schemas/provision-ast.schema.json`
- Create: `tests/test_conditions.py`

**Interfaces:**
- Produces: `LogicalConditionType`, `LogicalCondition`, `ConditionExpression`, and `ProvisionAst.condition`.
- Serialization: `LogicalCondition.to_dict() -> dict[str, Any]` recursively preserves operand order.

- [ ] **Step 1: Write failing model serialization tests**

```python
from building_code_ast.model import (
    Action,
    ComparisonCondition,
    LogicalCondition,
    LogicalConditionType,
    Modality,
    ProvisionAst,
    Quantity,
    SourceArtifact,
    SourceSpan,
)


def test_logical_condition_serializes_recursively() -> None:
    source = "Rooms exceeding 40 feet in height and exceeding 20000 square feet in floor area shall provide access."
    first = ComparisonCondition("height", ">", Quantity(40.0, "ft", "exceeding 40 feet in height"), SourceSpan(6, 34, "exceeding 40 feet in height"))
    second = ComparisonCondition("floor area", ">", Quantity(20000.0, "ft2", "exceeding 20000 square feet in floor area"), SourceSpan(39, 84, "exceeding 20000 square feet in floor area"))
    group = LogicalCondition(LogicalConditionType.ALL_OF, (first, second), SourceSpan(6, 84, source[6:84]))
    ast = ProvisionAst(
        source_text=source,
        source_artifact=SourceArtifact("synthetic:model:v1", "fixture:1"),
        modality=Modality.REQUIREMENT,
        modality_span=SourceSpan(85, 90, "shall"),
        subject="Rooms",
        subject_span=SourceSpan(0, 5, "Rooms"),
        condition=group,
        action=Action("provide access.", "provide", "access", SourceSpan(91, 106, "provide access.")),
        source_span=SourceSpan(0, len(source), source),
    )
    payload = ast.to_dict()
    assert payload["ast_version"] == "0.3.0"
    assert "conditions" not in payload
    assert payload["condition"]["type"] == "all_of"
    assert [item["subject_property"] for item in payload["condition"]["operands"]] == ["height", "floor area"]
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `python -m unittest tests.test_conditions -v`
Expected: import or constructor failure because recursive condition types and `ProvisionAst.condition` do not exist.

- [ ] **Step 3: Implement the model contract**

In `model.py`:

```python
AST_VERSION = "0.3.0"

class LogicalConditionType(StrEnum):
    ALL_OF = "all_of"
    ANY_OF = "any_of"

@dataclass(frozen=True, slots=True)
class LogicalCondition:
    type: LogicalConditionType
    operands: tuple[ComparisonCondition | LogicalCondition, ...]
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "operands": [operand.to_dict() for operand in self.operands],
            "span": self.span.to_dict(),
        }

ConditionExpression = ComparisonCondition | LogicalCondition
```

Replace `ProvisionAst.conditions` with `condition: ConditionExpression | None = None` and serialize it as `"condition": self.condition.to_dict() if self.condition else None`.

- [ ] **Step 4: Replace the schema condition contract**

Set `ast_version` to `0.3.0`, require `condition`, remove `conditions`, add recursive `$defs.conditionExpression`, and define logical groups with `minItems: 2`, `type` enum `all_of` / `any_of`, and `additionalProperties: false`.

- [ ] **Step 5: Run focused tests and schema parse**

Run:

```bash
python -m unittest tests.test_conditions -v
python -c "import json; json.load(open('schemas/provision-ast.schema.json', encoding='utf-8'))"
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/building_code_ast/model.py schemas/provision-ast.schema.json tests/test_conditions.py
git commit -m "feat: add recursive condition model"
```

### Task 2: Add recursive fail-closed validation

**Files:**
- Modify: `src/building_code_ast/validation.py`
- Modify: `tests/test_conditions.py`

**Interfaces:**
- Consumes: `ConditionExpression`, `ComparisonCondition`, `LogicalCondition`, `LogicalConditionType`.
- Produces: `_validate_condition(source, condition, label, active_path)` used by `validate_ast`.

- [ ] **Step 1: Add failing validation tests**

Cover these exact failures:

```python
with self.assertRaisesRegex(ValueError, "original text"):
    validate_ast(ast_with_mismatched_threshold_text)

with self.assertRaisesRegex(ValueError, "start at its first operand"):
    validate_ast(ast_with_wide_group_start)

with self.assertRaisesRegex(ValueError, "source order"):
    validate_ast(ast_with_reversed_operands)

with self.assertRaisesRegex(ValueError, "cycle"):
    validate_ast(ast_with_active_path_cycle)
```

Also assert that reusing the same finite comparison object twice in separate non-overlapping groups is not rejected solely because of Python object identity.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m unittest tests.test_conditions -v`
Expected: new validation assertions fail because recursive checks are absent.

- [ ] **Step 3: Implement recursive validation**

Implement a helper that:

- validates comparison spans and supported operators;
- requires `threshold.original_text == span.text`;
- requires logical enum instances and at least two operands;
- checks exact group start/end equality with first/last operands;
- checks containment, strictly increasing starts, and non-overlap;
- tracks only active logical node IDs and removes them on return;
- rejects unsupported runtime expression objects.

Call it from `validate_ast` only when `ast.condition is not None`.

- [ ] **Step 4: Run focused and full tests**

Run:

```bash
python -m unittest tests.test_conditions -v
python -m unittest discover -s tests -v
```

Expected: PASS after existing parser tests are migrated in Task 3; during this task, only focused model/validator tests must pass.

- [ ] **Step 5: Commit**

```bash
git add src/building_code_ast/validation.py tests/test_conditions.py
git commit -m "feat: validate recursive conditions"
```

### Task 3: Parse homogeneous chains and deterministic rejection diagnostics

**Files:**
- Modify: `src/building_code_ast/parser.py`
- Modify: `tests/test_parser.py`
- Modify: `tests/test_conditions.py`
- Modify: `fixtures/expected/threshold-with-exception.json`

**Interfaces:**
- Produces: `_extract_condition(...) -> tuple[str, SourceSpan | None, ConditionExpression | None, tuple[Diagnostic, ...]]`.
- Preserves: `parse_provision(...) -> ProvisionAst` public signature.

- [ ] **Step 1: Add failing parser tests**

Add tests for:

- one comparison produces `ComparisonCondition`;
- repeated `and` produces `LogicalConditionType.ALL_OF`;
- repeated `or` produces `LogicalConditionType.ANY_OF`;
- three operands preserve source order;
- parentheses beat mixed connectors in diagnostic precedence;
- mixed connectors beat malformed clause diagnostics;
- malformed single candidate produces `unsupported-condition-clause`;
- rejected candidates preserve the complete pre-modal subject;
- specific condition warnings suppress `no-structured-condition`;
- missing modality behavior remains unchanged.

- [ ] **Step 2: Run parser tests and confirm failure**

Run:

```bash
python -m unittest tests.test_parser tests.test_conditions -v
```

Expected: FAIL because parser still returns a flat condition tuple.

- [ ] **Step 3: Implement candidate-tail parsing**

Add whole-word marker and connector regexes. Locate the first supported marker in the pre-modal text. Apply rejection precedence in this exact order:

1. any `(` or `)` -> `unsupported-condition-grouping`;
2. both whole-word `and` and `or` -> `ambiguous-condition-connectors`;
3. any single clause or homogeneous segment not fully matching `_THRESHOLD_PATTERN` -> `unsupported-condition-clause`.

On rejection, preserve the full pre-modal text as subject and return `condition=None`. On success, trim the regulated subject before the marker, preserve absolute segment offsets, and emit one comparison or one logical group.

- [ ] **Step 4: Migrate existing fixture and regression tests**

Change fixture `ast_version` to `0.3.0`, replace `conditions: [comparison]` with `condition: comparison`, and update tests from `ast.conditions[0]` to `ast.condition` with an `isinstance` assertion.

- [ ] **Step 5: Run all runtime verification**

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/building_code_ast/parser.py tests/test_parser.py tests/test_conditions.py fixtures/expected/threshold-with-exception.json
git commit -m "feat: parse composable conditions"
```

### Task 4: Publish the compatibility boundary and verify exact head

**Files:**
- Modify: `README.md`
- Modify: `docs/compatibility.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: package metadata `0.3.0.dev0` and explicit consumer migration rules.

- [ ] **Step 1: Update package metadata**

Set `project.version = "0.3.0.dev0"`.

- [ ] **Step 2: Update README behavior**

Describe provision AST `0.3.0`, required nullable `condition`, single comparisons, homogeneous `all_of` / `any_of` groups, and explicit warnings for unsupported grouping, mixed connectors, and malformed clauses.

- [ ] **Step 3: Update compatibility documentation**

Add provision AST `0.3.0` before `0.2.0`. State:

- zero old conditions migrate to `condition: null`;
- one old condition migrates to that comparison;
- multiple old conditions require source re-parsing or human review because connector meaning was absent.

- [ ] **Step 4: Run final verification**

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -c "import json; json.load(open('schemas/provision-ast.schema.json', encoding='utf-8'))"
python -c "from building_code_ast.model import AST_VERSION; assert AST_VERSION == '0.3.0'"
python -c "import pathlib; assert 'version = \"0.3.0.dev0\"' in pathlib.Path('pyproject.toml').read_text()"
```

Expected: every command exits zero.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/compatibility.md pyproject.toml docs/superpowers/plans/2026-08-01-composable-condition-expressions.md
git commit -m "docs: publish provision ast 0.3.0 boundary"
```

- [ ] **Step 6: Open a draft pull request and verify exact-head CI**

PR title: `Add composable provision condition expressions`

The PR body must summarize the breaking contract, conservative parser boundary, recursive validation, fixtures/tests, migration rule, and exact verification commands. Do not mark ready or merge until CI passes at the exact head and a self-review finds no critical or important defect.
