from __future__ import annotations

import unittest

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


class ConditionModelTests(unittest.TestCase):
    def test_logical_condition_serializes_recursively(self) -> None:
        source = (
            "Rooms exceeding 40 feet in height and exceeding 20000 square feet "
            "in floor area shall provide access."
        )
        first = ComparisonCondition(
            subject_property="height",
            operator=">",
            threshold=Quantity(
                value=40.0,
                unit="ft",
                original_text="exceeding 40 feet in height",
            ),
            span=SourceSpan(6, 33, "exceeding 40 feet in height"),
        )
        second = ComparisonCondition(
            subject_property="floor area",
            operator=">",
            threshold=Quantity(
                value=20000.0,
                unit="ft2",
                original_text="exceeding 20000 square feet in floor area",
            ),
            span=SourceSpan(
                38,
                79,
                "exceeding 20000 square feet in floor area",
            ),
        )
        group = LogicalCondition(
            type=LogicalConditionType.ALL_OF,
            operands=(first, second),
            span=SourceSpan(6, 79, source[6:79]),
        )
        ast = ProvisionAst(
            source_text=source,
            source_artifact=SourceArtifact(
                artifact_id="synthetic:model:v1",
                provision_locator="fixture:1",
            ),
            modality=Modality.REQUIREMENT,
            modality_span=SourceSpan(80, 85, "shall"),
            subject="Rooms",
            subject_span=SourceSpan(0, 5, "Rooms"),
            condition=group,
            action=Action(
                text="provide access.",
                normalized_verb="provide",
                object_text="access",
                span=SourceSpan(86, 101, "provide access."),
            ),
            source_span=SourceSpan(0, len(source), source),
        )

        payload = ast.to_dict()

        self.assertEqual(payload["ast_version"], "0.3.0")
        self.assertNotIn("conditions", payload)
        self.assertEqual(payload["condition"]["type"], "all_of")
        self.assertEqual(
            [operand["subject_property"] for operand in payload["condition"]["operands"]],
            ["height", "floor area"],
        )


if __name__ == "__main__":
    unittest.main()
