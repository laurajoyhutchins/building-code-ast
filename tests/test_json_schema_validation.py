from __future__ import annotations

import unittest

from building_code_ast.json_schema_validation import validate_instances


class JsonSchemaValidationTests(unittest.TestCase):
    def test_reports_indexed_errors_and_accepts_valid_instances(self) -> None:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string"}},
            "additionalProperties": False,
        }
        errors = validate_instances([{"id": "ok"}, {"id": 3}, {"extra": True}], schema)
        self.assertEqual(len(errors), 3)
        self.assertEqual([item["instance_index"] for item in errors], [1, 2, 2])
        self.assertEqual(validate_instances([{"id": "ok"}], schema), [])


if __name__ == "__main__":
    unittest.main()
