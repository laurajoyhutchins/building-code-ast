from __future__ import annotations

import json
from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]


class NecChangeHistoryContractTests(unittest.TestCase):
    def test_schema_matches_dataset_contract_without_source_prose(self) -> None:
        schema_path = _ROOT / "schemas" / "nec-change-history.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["dataset_version"]["const"], "0.1.0")
        self.assertEqual(schema["properties"]["type"]["const"], "nec_expected_changelog")
        self.assertFalse(schema["additionalProperties"])
        schema_text = json.dumps(schema, sort_keys=True)
        self.assertNotIn('"source_text"', schema_text)
        self.assertNotIn('"proposal_text"', schema_text)
        self.assertNotIn('"replacement_text"', schema_text)

    def test_public_documentation_states_authority_and_private_source_boundary(self) -> None:
        how_to = (
            _ROOT / "docs" / "how-to" / "build-nec-2020-expected-changelog.md"
        ).read_text(encoding="utf-8")
        reference = (
            _ROOT / "docs" / "reference" / "nec-change-history.md"
        ).read_text(encoding="utf-8")
        combined = f"{how_to}\n{reference}".casefold()

        self.assertIn("issued 2020 nec", combined)
        self.assertIn("controlling text", combined)
        self.assertIn("private", combined)
        self.assertIn("development records", combined)
        self.assertIn("expected", combined)
        self.assertIn("observed", combined)
        self.assertIn("reconciliation", combined)
        self.assertNotIn("authoritative changelog", combined)


if __name__ == "__main__":
    unittest.main()
