from __future__ import annotations

from copy import deepcopy
import unittest

from building_code_ast.applicability import project_applicability_scopes


class ApplicabilityScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {
                "owner_locator": "5.1",
                "applies_to_locators": ["5.1.1", "5.1.2"],
                "resolution_state": "resolved",
                "method": "structural-owner",
                "review_status": "unreviewed",
                "evidence": {"start": 10, "end": 28, "text": "Synthetic scope text"},
            },
            {
                "owner_locator": "6.1",
                "applies_to_locators": ["6.1.1", "6.1.2"],
                "resolution_state": "ambiguous",
                "method": "structural-owner",
                "review_status": "unreviewed",
                "evidence": {"start": 40, "end": 58, "text": "Synthetic ambiguity"},
            },
        ]

    def project(self, records=None):
        return project_applicability_scopes(self.records if records is None else records)

    def test_projection_is_versioned_and_deterministic(self) -> None:
        forward = self.project()
        reverse = self.project(list(reversed(self.records)))
        self.assertEqual(forward, reverse)
        self.assertEqual("applicability-scopes/0.1.0", forward["schema"])

    def test_scope_owner_and_descendants_remain_distinct(self) -> None:
        projected = self.project()
        resolved = next(item for item in projected["scopes"] if item["owner_locator"] == "5.1")
        self.assertEqual("5.1", resolved["owner_locator"])
        self.assertEqual(["5.1.1", "5.1.2"], resolved["applies_to_locators"])
        self.assertEqual("resolved", resolved["resolution_state"])

    def test_ambiguous_ownership_remains_explicit(self) -> None:
        projected = self.project()
        ambiguous = next(item for item in projected["scopes"] if item["owner_locator"] == "6.1")
        self.assertEqual("ambiguous", ambiguous["resolution_state"])

    def test_projection_retains_coordinates_not_source_expression(self) -> None:
        projected = self.project()
        self.assertNotIn("Synthetic scope text", repr(projected))
        scope = next(item for item in projected["scopes"] if item["owner_locator"] == "5.1")
        self.assertEqual({"start": 10, "end": 28}, scope["evidence_span"])

    def test_duplicate_descendant_assignment_fails_closed(self) -> None:
        records = deepcopy(self.records)
        records[1]["applies_to_locators"] = ["5.1.2"]
        with self.assertRaisesRegex(ValueError, "multiple applicability owners"):
            self.project(records)

    def test_owner_cannot_apply_to_itself(self) -> None:
        records = deepcopy(self.records)
        records[0]["applies_to_locators"] = ["5.1"]
        with self.assertRaisesRegex(ValueError, "cannot apply to itself"):
            self.project(records)

    def test_review_status_does_not_change_resolution_state(self) -> None:
        records = deepcopy(self.records)
        records[0]["review_status"] = "reviewed"
        projected = self.project(records)
        scope = next(item for item in projected["scopes"] if item["owner_locator"] == "5.1")
        self.assertEqual("resolved", scope["resolution_state"])
        self.assertEqual("reviewed", scope["review_status"])


if __name__ == "__main__":
    unittest.main()
