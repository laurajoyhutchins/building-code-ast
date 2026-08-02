from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.nec import (
    DEFINITION_INDEX_VERSION,
    LANGUAGE_PROFILE_VERSION,
    SECTION_REVIEW_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]


class NecSemanticContractTests(unittest.TestCase):
    def test_definition_schema_matches_runtime_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "nec-definition-index.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["index_version"]["const"],
            DEFINITION_INDEX_VERSION,
        )
        self.assertEqual(schema["properties"]["type"]["const"], "nec_definition_index")
        self.assertTrue(
            {
                "source_text",
                "source_artifact",
                "article_locator",
                "entries",
                "diagnostics",
            }.issubset(schema["required"])
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["$defs"]["definitionEntry"]["properties"]["definition_id"]["pattern"],
            "^necdef:[0-9a-f]{64}$",
        )

    def test_section_schema_matches_runtime_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "nec-section-review.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["review_version"]["const"],
            SECTION_REVIEW_VERSION,
        )
        self.assertEqual(schema["properties"]["type"]["const"], "nec_section_review")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["$defs"]["reviewedClause"]["properties"]["clause_id"]["pattern"],
            "^necclause:[0-9a-f]{64}$",
        )
        self.assertEqual(
            set(schema["$defs"]["reviewedModality"]["enum"]),
            {"requirement", "prohibition", "permission", "nonrequirement", "unknown"},
        )

    def test_language_profile_schema_matches_runtime_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "nec-language-profile.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["properties"]["profile_version"]["const"],
            LANGUAGE_PROFILE_VERSION,
        )
        self.assertEqual(schema["properties"]["type"]["const"], "nec_language_profile")
        self.assertFalse(schema["additionalProperties"])

    def test_public_documentation_names_private_output_boundary(self) -> None:
        reference = (
            ROOT / "docs" / "reference" / "nec-section-review.md"
        ).read_text(encoding="utf-8")
        how_to = (
            ROOT / "docs" / "how-to" / "build-nec-semantic-seed.md"
        ).read_text(encoding="utf-8")

        self.assertIn("not a compliance determination", reference.lower())
        self.assertIn("must remain private", how_to.lower())
        self.assertIn("definitions-article-100.json", how_to)
        self.assertIn("section-110.26.json", how_to)


if __name__ == "__main__":
    unittest.main()
