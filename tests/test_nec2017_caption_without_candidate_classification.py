from __future__ import annotations

import json
from pathlib import Path
import unittest


PROOF_PATH = (
    Path(__file__).parents[1]
    / "corpora"
    / "nec-2017"
    / "nec-2017-caption-without-candidate-classification.json"
)


class Nec2017CaptionWithoutCandidateClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))

    def test_exact_source_and_post_quality_baseline_are_retained(self) -> None:
        self.assertEqual(
            {
                "file_name": "nec-2017.pdf",
                "page_count": 881,
                "private_source_locator_retained": False,
                "protected_source_expression_retained": False,
                "sha256": "603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7",
                "size_bytes": 7422245,
            },
            self.proof["source"],
        )
        self.assertEqual(
            {
                "ambiguous_candidates": 0,
                "assigned_candidates": 318,
                "candidate_envelopes": 1159,
                "captions_with_candidate": 163,
                "captions_with_multiple_candidates": 80,
                "captions_without_candidate": 59,
                "geometry_rows": 9879,
                "grouped_candidates": 939,
                "ruled_candidates": 220,
                "unresolved_candidates": 841,
            },
            self.proof["baseline"]["metrics"],
        )

    def test_all_59_unsupported_captions_are_classified(self) -> None:
        expected_reasons = {
            "inline_anchor_candidates_owned_by_other_caption": 7,
            "nearby_unresolved_candidate_inline_start_mismatch": 41,
            "no_candidate_envelope_nearby_rows_present": 4,
            "no_candidate_envelope_no_nearby_rows": 2,
            "page_candidates_without_nearby_unresolved_or_inline_match": 5,
        }
        cases = self.proof["classification"]["cases"]
        self.assertEqual(59, len(cases))
        self.assertEqual(expected_reasons, self.proof["classification"]["reason_counts"])
        self.assertEqual(59, sum(expected_reasons.values()))
        self.assertTrue(self.proof["classification"]["all_caption_without_candidate_reviewed"])
        self.assertFalse(
            self.proof["conclusion"]["single_publication_neutral_candidate_production_defect_proven"]
        )

    def test_proof_retains_only_source_safe_case_coordinates(self) -> None:
        forbidden_keys = {
            "candidate_id",
            "caption_id",
            "designation",
            "identifier",
            "label",
            "locator",
            "source_text",
            "text",
        }

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.proof)
        for case in self.proof["classification"]["cases"]:
            self.assertGreater(case["page"], 0)
            self.assertEqual(4, len(case["bbox"]))
            self.assertLess(case["bbox"][0], case["bbox"][2])
            self.assertLess(case["bbox"][1], case["bbox"][3])


if __name__ == "__main__":
    unittest.main()
