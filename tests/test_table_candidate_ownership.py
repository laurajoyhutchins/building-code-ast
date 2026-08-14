from __future__ import annotations

import unittest

from building_code_ast.ingest.table_candidate_ownership import (
    TableCandidateEnvelope,
    TableCaptionAnchor,
    associate_table_candidates,
)


class TableCandidateOwnershipTests(unittest.TestCase):
    def test_rule_backed_candidates_prefer_their_unique_overlapping_caption(self) -> None:
        captions = (
            TableCaptionAnchor("first", 1, (10.0, 10.0, 90.0, 20.0)),
            TableCaptionAnchor("second", 1, (10.0, 100.0, 90.0, 110.0)),
        )
        candidates = (
            TableCandidateEnvelope(
                "first-table",
                1,
                (10.0, 10.0, 90.0, 80.0),
                evidence=("vector_rule_grid",),
            ),
            TableCandidateEnvelope(
                "second-table",
                1,
                (10.0, 100.0, 90.0, 160.0),
                evidence=("vector_rule_grid",),
            ),
        )

        ownership = associate_table_candidates(captions, candidates)

        self.assertEqual(ownership.assigned_to("first"), ("first-table",))
        self.assertEqual(ownership.assigned_to("second"), ("second-table",))
        self.assertEqual(ownership.ambiguous_candidate_ids, ())

    def test_non_rule_backed_overlap_does_not_override_block_flow(self) -> None:
        captions = (
            TableCaptionAnchor("first", 1, (10.0, 10.0, 90.0, 20.0)),
            TableCaptionAnchor("second", 1, (10.0, 100.0, 90.0, 110.0)),
        )
        candidate = TableCandidateEnvelope(
            "geometry",
            1,
            (10.0, 10.0, 90.0, 80.0),
        )

        ownership = associate_table_candidates(captions, (candidate,))

        self.assertEqual(ownership.assigned_to("first"), ())
        self.assertEqual(ownership.assigned_to("second"), ())
        self.assertEqual(ownership.ambiguous_candidate_ids, ("geometry",))

    def test_rule_backed_candidate_overlapping_multiple_captions_stays_ambiguous(self) -> None:
        captions = (
            TableCaptionAnchor("first", 1, (10.0, 10.0, 90.0, 30.0)),
            TableCaptionAnchor("second", 1, (10.0, 25.0, 90.0, 45.0)),
        )
        candidate = TableCandidateEnvelope(
            "shared",
            1,
            (10.0, 10.0, 90.0, 80.0),
            evidence=("vector_rule_grid",),
        )

        ownership = associate_table_candidates(captions, (candidate,))

        self.assertEqual(ownership.assigned_to("first"), ())
        self.assertEqual(ownership.assigned_to("second"), ())
        self.assertEqual(ownership.ambiguous_candidate_ids, ("shared",))


if __name__ == "__main__":
    unittest.main()
