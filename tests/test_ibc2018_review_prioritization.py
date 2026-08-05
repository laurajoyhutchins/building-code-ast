from __future__ import annotations

import unittest

from building_code_ast.ibc2018_review import prioritize_review_queue


class ReviewPrioritizationTests(unittest.TestCase):
    def test_prioritizes_acceptance_blockers_before_routine_records(self) -> None:
        queue = [
            {"record_id": "semantic", "record_type": "semantic_pilot_record", "review_state": "provisional", "reason": "generic"},
            {"record_id": "vector", "record_type": "vector_graphic_region_detection", "review_state": "disputed", "reason": "candidate_vector_region_unclassified"},
            {"record_id": "citation", "record_type": "external_citation_occurrence", "review_state": "disputed", "reason": "generic"},
            {"record_id": "reference", "record_type": "internal_cross_reference", "review_state": "provisional", "reason": "generic"},
            {"record_id": "attachment", "record_type": "attachment_relationship", "review_state": "provisional", "reason": "generic"},
        ]
        records = {
            "semantic": {"id": "semantic", "review_state": "provisional"},
            "vector": {"id": "vector", "review_state": "disputed", "disposition": "candidate_vector_region_unclassified"},
            "citation": {"id": "citation", "review_state": "disputed", "normalized_document_family_id": None},
            "reference": {"id": "reference", "review_state": "provisional", "resolution_state": "unresolved"},
            "attachment": {"id": "attachment", "review_state": "provisional"},
        }

        prioritized, summary = prioritize_review_queue(queue, records)

        self.assertEqual([row["record_id"] for row in prioritized], ["semantic", "vector", "citation", "reference", "attachment"])
        self.assertEqual(prioritized[0]["priority_band"], "P0")
        self.assertEqual(prioritized[1]["priority_band"], "P0")
        self.assertEqual(prioritized[2]["priority_band"], "P1")
        self.assertEqual(prioritized[3]["priority_band"], "P1")
        self.assertEqual(prioritized[4]["priority_band"], "P3")
        self.assertEqual(summary["priority_counts"], {"P0": 2, "P1": 2, "P3": 1})

    def test_uses_current_inventory_state_instead_of_stale_queue_state(self) -> None:
        queue = [
            {"record_id": "citation", "record_type": "external_citation_occurrence", "review_state": "disputed", "reason": "generic"}
        ]
        records = {
            "citation": {
                "id": "citation",
                "review_state": "provisional",
                "normalized_document_family_id": "family-7",
                "normalization_reason": "agency_alias_unique",
            }
        }
        prioritized, summary = prioritize_review_queue(queue, records)
        self.assertEqual(prioritized[0]["review_state"], "provisional")
        self.assertEqual(prioritized[0]["priority_band"], "P3")
        self.assertEqual(prioritized[0]["reason"], "agency_alias_unique")
        self.assertEqual(summary["review_state_counts"], {"provisional": 1})

    def test_preserves_unknown_records_as_explicit_backlog(self) -> None:
        queue = [
            {"record_id": "missing", "record_type": "unknown", "review_state": "provisional", "reason": "generic"}
        ]
        prioritized, _ = prioritize_review_queue(queue, {})
        self.assertEqual(prioritized[0]["priority_band"], "P3")
        self.assertEqual(prioritized[0]["evidence_category"], "unindexed_record")
        self.assertEqual(prioritized[0]["recommended_action"], "locate source-safe inventory record")


if __name__ == "__main__":
    unittest.main()
