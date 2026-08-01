from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from building_code_ast import parse_provision
from building_code_ast.model import AST_VERSION


ROOT = Path(__file__).resolve().parents[1]


class ConditionFixtureTests(unittest.TestCase):
    def test_reviewed_condition_fixtures_match_exact_output(self) -> None:
        cases = json.loads(
            (ROOT / "fixtures/conditions.json").read_text(encoding="utf-8")
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                self.assertEqual(
                    parse_provision(case["source"]).to_dict(),
                    case["expected"],
                )

    def test_schema_exposes_recursive_condition_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/provision-ast.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(AST_VERSION, "0.3.0")
        self.assertEqual(schema["properties"]["ast_version"]["const"], AST_VERSION)
        self.assertIn("condition", schema["required"])
        self.assertNotIn("conditions", schema["properties"])
        self.assertEqual(
            schema["$defs"]["logicalCondition"]["properties"]["operands"]["minItems"],
            2,
        )

    def test_package_metadata_matches_provision_contract(self) -> None:
        pyproject = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(pyproject["project"]["version"], "0.3.0.dev0")
        self.assertEqual(pyproject["project"]["dependencies"], [])
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.12,<3.13")


if __name__ == "__main__":
    unittest.main()
