from __future__ import annotations

import unittest
from dataclasses import replace

from building_code_ast import validate_ast
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


SOURCE = (
    "Rooms exceeding 40 feet in height and exceeding 20000 square feet "
    "in floor area shall provide access."
)


def _height_condition() -> ComparisonCondition:
    return ComparisonCondition(
        subject_property="height",
        operator=">",
        threshold=Quantity(
            value=40.0,
            unit="ft",
            original_text="exceeding 40 feet in height",
        ),
        span=SourceSpan(6, 33, "exceeding 40 feet in height"),
    )


def _area_condition() -> ComparisonCondition:
    return ComparisonCondition(
        subject_property="floor area",
        operator=">",
        threshold=Quantity(
            value=20000.0,
            unit="ft2",
            original_text="exceeding 20000 square feet in floor area",
        ),
        span=SourceSpan(38, 79, "exceeding 20000 square feet in floor area"),
    )


def _group(
    *operands: ComparisonCondition | LogicalCondition,
    span: SourceSpan | None = None,
) -> LogicalCondition:
    return LogicalCondition(
        type=LogicalConditionType.ALL_OF,
        operands=operands,
        span=span or SourceSpan(6, 79, SOURCE[6:79]),
    )


def _ast(condition: ComparisonCondition | LogicalCondition | None) -> ProvisionAst:
    return ProvisionAst(
        source_text=SOURCE,
        source_artifact=SourceArtifact(
            artifact_id="synthetic:model:v1",
            provision_locator="fixture:1",
        ),
        modality=Modality.REQUIREMENT,
        modality_span=SourceSpan(80, 85, "shall"),
        subject="Rooms",
        subject_span=SourceSpan(0, 5, "Rooms"),
        condition=condition,
        action=Action(
            text="provide access.",
            normalized_verb="provide",
            object_text="access",
            span=SourceSpan(86, 101, "provide access."),
        ),
        source_span=SourceSpan(0, len(SOURCE), SOURCE),
    )


class ConditionModelTests(unittest.TestCase):
    def test_logical_condition_serializes_recursively(self) -> None:
        ast = _ast(_group(_height_condition(), _area_condition()))

        payload = ast.to_dict()

        self.assertEqual(payload["ast_version"], "0.3.0")
        self.assertNotIn("conditions", payload)
        self.assertEqual(payload["condition"]["type"], "all_of")
        self.assertEqual(
            [operand["subject_property"] for operand in payload["condition"]["operands"]],
            ["height", "floor area"],
        )


class ConditionValidationTests(unittest.TestCase):
    def test_valid_logical_condition_passes(self) -> None:
        validate_ast(_ast(_group(_height_condition(), _area_condition())))

    def test_comparison_original_text_must_match_span(self) -> None:
        height = _height_condition()
        bad_height = replace(
            height,
            threshold=replace(height.threshold, original_text="40 feet"),
        )

        with self.assertRaisesRegex(ValueError, "original text"):
            validate_ast(_ast(bad_height))

    def test_group_must_start_at_first_operand(self) -> None:
        group = _group(
            _height_condition(),
            _area_condition(),
            span=SourceSpan(5, 79, SOURCE[5:79]),
        )

        with self.assertRaisesRegex(ValueError, "start at its first operand"):
            validate_ast(_ast(group))

    def test_group_operands_must_be_in_source_order(self) -> None:
        group = _group(_area_condition(), _height_condition())

        with self.assertRaisesRegex(ValueError, "source order"):
            validate_ast(_ast(group))

    def test_logical_condition_cycle_is_rejected(self) -> None:
        group = _group(_height_condition(), _area_condition())
        object.__setattr__(group, "operands", (group, _area_condition()))

        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_ast(_ast(group))


if __name__ == "__main__":
    unittest.main()
