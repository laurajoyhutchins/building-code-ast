from __future__ import annotations

import unittest

from building_code_ast.ingest.table_candidate_ownership import (
    TableCandidateEnvelope,
    TableCaptionAnchor,
    associate_table_candidates,
)


class TableCaptionCandidateOwnershipTests(unittest.TestCase):
    def test_parallel_page_anchors_resolve_without_proximity_radius(self) -> None:
        captions = (
            TableCaptionAnchor("left", 1, (48.0, 35.0, 250.0, 44.0)),
            TableCaptionAnchor("right", 1, (313.0, 35.0, 500.0, 44.0)),
        )
        candidates = (
            TableCandidateEnvelope("left-a", 1, (48.0, 67.0, 296.0, 84.0)),
            TableCandidateEnvelope("left-b", 1, (48.0, 181.0, 296.0, 219.0)),
            TableCandidateEnvelope("right-a", 1, (313.0, 67.0, 560.0, 84.0)),
        )

        result = associate_table_candidates(captions, candidates)

        self.assertEqual(result.assigned_to("left"), ("left-a", "left-b"))
        self.assertEqual(result.assigned_to("right"), ("right-a",))
        self.assertEqual(result.unresolved_candidate_ids, ())
        self.assertEqual(result.ambiguous_candidate_ids, ())

    def test_same_anchor_uses_block_flow_to_partition_successive_captions(self) -> None:
        captions = (
            TableCaptionAnchor("first", 2, (313.0, 35.0, 490.0, 44.0)),
            TableCaptionAnchor("second", 2, (313.0, 137.0, 471.0, 145.0)),
        )
        candidates = (
            TableCandidateEnvelope("first-grid", 2, (313.0, 79.0, 561.0, 106.0)),
            TableCandidateEnvelope("second-grid", 2, (313.0, 180.0, 561.0, 207.0)),
        )

        result = associate_table_candidates(captions, candidates)

        self.assertEqual(result.assigned_to("first"), ("first-grid",))
        self.assertEqual(result.assigned_to("second"), ("second-grid",))

    def test_single_rotated_anchor_can_own_overlapping_rule_envelope(self) -> None:
        # Coordinates are already in the caption writing frame. A rotated table
        # may place its caption inside the rule envelope on the block axis, so a
        # unique inline-start anchor must not require downstream distance.
        captions = (
            TableCaptionAnchor("rotated", 3, (-744.25, 192.0, -37.75, 218.0)),
        )
        candidates = (
            TableCandidateEnvelope("rule-frame", 3, (-744.25, 61.5, -34.75, 471.1)),
        )

        result = associate_table_candidates(captions, candidates)

        self.assertEqual(result.assigned_to("rotated"), ("rule-frame",))
        self.assertEqual(result.unresolved_candidate_ids, ())

    def test_off_anchor_candidate_remains_unresolved(self) -> None:
        captions = (
            TableCaptionAnchor("caption", 4, (48.0, 35.0, 250.0, 44.0)),
        )
        candidates = (
            TableCandidateEnvelope("unrelated", 4, (75.0, 67.0, 300.0, 84.0)),
        )

        result = associate_table_candidates(captions, candidates)

        self.assertEqual(result.assigned_to("caption"), ())
        self.assertEqual(result.unresolved_candidate_ids, ("unrelated",))

    def test_equal_block_flow_candidates_are_ambiguous_between_same_anchor_captions(self) -> None:
        captions = (
            TableCaptionAnchor("a", 5, (48.0, 35.0, 250.0, 44.0)),
            TableCaptionAnchor("b", 5, (48.0, 35.0, 260.0, 44.0)),
        )
        candidates = (
            TableCandidateEnvelope("grid", 5, (48.0, 80.0, 500.0, 100.0)),
        )

        result = associate_table_candidates(captions, candidates)

        self.assertEqual(result.ambiguous_candidate_ids, ("grid",))
        self.assertEqual(result.unresolved_candidate_ids, ())


if __name__ == "__main__":
    unittest.main()
