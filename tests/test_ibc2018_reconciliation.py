from __future__ import annotations

import unittest

from building_code_ast.ibc2018_reconciliation import (
    collect_known_section_targets,
    reconcile_internal_references,
)


class Ibc2018ReconciliationTests(unittest.TestCase):
    def test_collect_known_sections_uses_contexts_parents_and_resolved_targets(self) -> None:
        targets = collect_known_section_targets(
            cross_references=[
                {"source_section": "2702.1", "target_kind": "section", "resolution_state": "resolved", "resolved_target": "403.4"},
            ],
            tables=[{"section_context": "2308.6.1"}],
            figures=[{"section_context": "722.2.1.3.1"}],
            equations=[{"source_section": "1609.3"}],
            exceptions=[{"parent_locator": "907.4.2.5"}],
        )
        self.assertTrue({"2702.1", "403.4", "2308.6.1", "722.2.1.3.1", "1609.3", "907.4.2.5"}.issubset(targets))

    def test_reconcile_resolves_exact_and_top_level_section_targets(self) -> None:
        records = [
            {
                "id": "exact",
                "target_kind": "section",
                "raw_target": "403.4",
                "resolved_target": None,
                "resolution_state": "unresolved",
                "resolution_notes": None,
            },
            {
                "id": "heading",
                "target_kind": "section",
                "raw_target": "2702",
                "resolved_target": None,
                "resolution_state": "unresolved",
                "resolution_notes": None,
            },
        ]
        reconciled = reconcile_internal_references(records, known_section_targets={"403.4", "2702.1"})
        self.assertEqual(reconciled[0]["resolution_state"], "resolved")
        self.assertEqual(reconciled[0]["resolution_reason"], "exact_section_target")
        self.assertEqual(reconciled[1]["resolution_state"], "resolved")
        self.assertEqual(reconciled[1]["resolved_target"], "2702")
        self.assertEqual(reconciled[1]["resolution_reason"], "section_heading_prefix")

    def test_reconcile_preserves_ambiguity_and_nonsection_nonexistence(self) -> None:
        records = [
            {
                "id": "ambiguous",
                "target_kind": "section",
                "raw_target": "11.4",
                "resolved_target": None,
                "resolution_state": "ambiguous",
                "resolution_notes": None,
            },
            {
                "id": "missing-table",
                "target_kind": "table",
                "raw_target": "2308.6",
                "resolved_target": None,
                "resolution_state": "nonexistent",
                "resolution_notes": None,
            },
        ]
        reconciled = reconcile_internal_references(records, known_section_targets={"1104.1"})
        self.assertEqual(reconciled[0]["resolution_state"], "ambiguous")
        self.assertEqual(reconciled[0]["resolution_reason"], "preserved_contextual_ambiguity")
        self.assertEqual(reconciled[1]["resolution_state"], "nonexistent")
        self.assertEqual(reconciled[1]["resolution_reason"], "target_not_in_inventory")

    def test_reconcile_adds_reason_to_every_record_without_mutating_input(self) -> None:
        original = {
            "id": "unresolved",
            "target_kind": "section",
            "raw_target": "9999.1",
            "resolved_target": None,
            "resolution_state": "unresolved",
            "resolution_notes": None,
        }
        reconciled = reconcile_internal_references([original], known_section_targets=set())
        self.assertNotIn("resolution_reason", original)
        self.assertEqual(reconciled[0]["resolution_reason"], "section_target_not_indexed")


if __name__ == "__main__":
    unittest.main()
