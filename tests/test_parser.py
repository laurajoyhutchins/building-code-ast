from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast import parse_provision, validate_ast
from building_code_ast.model import ComparisonCondition, Modality


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_threshold_requirement_with_exception_matches_reviewed_fixture(self) -> None:
        source = (ROOT / "fixtures/sources/threshold-with-exception.txt").read_text(encoding="utf-8").strip()
        expected = json.loads((ROOT / "fixtures/expected/threshold-with-exception.json").read_text(encoding="utf-8"))

        ast = parse_provision(
            source,
            source_artifact_id="synthetic:threshold-with-exception:v1",
            provision_locator="fixture:1",
        )

        self.assertEqual(ast.to_dict(), expected)
        self.assertEqual(ast.exceptions[0].section, "12.4")
        self.assertIsInstance(ast.condition, ComparisonCondition)
        validate_ast(ast)

    def test_prohibition_is_distinct_from_requirement(self) -> None:
        ast = parse_provision("Doors shall not be obstructed.")

        self.assertEqual(ast.modality, Modality.PROHIBITION)
        self.assertEqual(ast.subject, "Doors")
        self.assertEqual(ast.modality_span.text, "shall not")
        self.assertEqual(ast.subject_span.text, "Doors")
        self.assertEqual(ast.action.text, "be obstructed.")
        self.assertEqual(ast.action.normalized_verb, None)
        self.assertIn("unsupported-action-shape", {diagnostic.code for diagnostic in ast.diagnostics})

    def test_permission_is_preserved(self) -> None:
        ast = parse_provision("Doors may be locked during testing.")

        self.assertEqual(ast.modality, Modality.PERMISSION)
        self.assertEqual(ast.subject, "Doors")
        self.assertEqual(ast.modality_span.text, "may")

    def test_missing_modality_is_an_explicit_error(self) -> None:
        ast = parse_provision("Doors located along the route.")

        self.assertEqual(ast.modality, Modality.UNKNOWN)
        self.assertIsNone(ast.modality_span)
        self.assertIsNone(ast.subject_span)
        self.assertEqual(ast.diagnostics[0].code, "missing-modality")
        self.assertEqual(ast.diagnostics[0].severity.value, "error")

    def test_source_spans_round_trip(self) -> None:
        source = "Research facilities exceeding 40 feet in height shall provide two marked evacuation routes."
        ast = parse_provision(source)

        self.assertEqual(source[ast.source_span.start : ast.source_span.end], ast.source_span.text)
        self.assertEqual(source[ast.modality_span.start : ast.modality_span.end], ast.modality_span.text)
        self.assertEqual(source[ast.subject_span.start : ast.subject_span.end], ast.subject_span.text)
        self.assertEqual(source[ast.action.span.start : ast.action.span.end], ast.action.span.text)
        self.assertIsInstance(ast.condition, ComparisonCondition)
        self.assertEqual(source[ast.condition.span.start : ast.condition.span.end], ast.condition.span.text)

    def test_original_whitespace_and_offsets_are_preserved(self) -> None:
        source = "  Doors shall provide clear access.  \n"
        ast = parse_provision(source)

        self.assertEqual(ast.source_text, source)
        self.assertEqual(ast.source_span.start, 0)
        self.assertEqual(ast.source_span.end, len(source))
        self.assertEqual(ast.source_span.text, source)
        self.assertEqual(ast.subject_span.start, 2)
        self.assertEqual(ast.subject_span.text, "Doors")
        self.assertEqual(ast.modality_span.text, "shall")
        self.assertEqual(ast.action.span.text, "provide clear access.")
        validate_ast(ast)

    def test_identical_text_is_distinguished_by_source_identity(self) -> None:
        source = "Doors shall provide clear access."
        first = parse_provision(
            source,
            source_artifact_id="edition:2024",
            provision_locator="Section 1.1",
        )
        second = parse_provision(
            source,
            source_artifact_id="edition:2027",
            provision_locator="Section 8.3",
        )

        self.assertNotEqual(first.source_artifact, second.source_artifact)
        self.assertEqual(first.source_text, second.source_text)
        self.assertEqual(first.source_artifact.artifact_id, "edition:2024")
        self.assertEqual(second.source_artifact.provision_locator, "Section 8.3")

    def test_empty_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            parse_provision("   ")

    def test_empty_source_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "source_artifact_id"):
            parse_provision("Doors shall provide access.", source_artifact_id="")
        with self.assertRaisesRegex(ValueError, "provision_locator"):
            parse_provision("Doors shall provide access.", provision_locator="")


if __name__ == "__main__":
    unittest.main()
