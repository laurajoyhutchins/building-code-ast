from __future__ import annotations

import json
import unittest
from pathlib import Path


class Nec2017UnresolvedCandidateClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.payload = json.loads(
            (root / "corpora" / "nec-2017" / "nec-2017-unresolved-candidate-classification.json").read_text()
        )

    def test_exact_post_quality_denominator_is_classified_once(self) -> None:
        payload = self.payload
        self.assertEqual(payload["source"]["sha256"], "603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7")
        self.assertEqual(payload["source"]["size_bytes"], 7_422_245)
        self.assertEqual(payload["source"]["page_count"], 881)
        self.assertEqual(payload["baseline"]["candidate_envelopes"], 1_159)
        self.assertEqual(payload["baseline"]["assigned"], 318)
        self.assertEqual(payload["baseline"]["unresolved"], 841)
        self.assertEqual(payload["baseline"]["ambiguous"], 0)
        self.assertEqual(payload["baseline"]["captions_with_candidate"], 163)
        self.assertEqual(payload["baseline"]["captions_without"], 59)
        classification = payload["classification"]
        self.assertTrue(classification["all_unresolved_candidates_classified_once"])
        self.assertEqual(classification["total"], 841)
        self.assertEqual(classification["fine_partition_total"], 841)
        self.assertEqual(sum(classification["primary_partition"].values()), 841)
        self.assertEqual(sum(classification["fine_partition"].values()), 841)
        self.assertEqual(
            classification["primary_partition"],
            {
                "grouped_geometry/caption_page_inline_mismatch": 244,
                "grouped_geometry/page_without_caption": 487,
                "vector_rule/caption_page_inline_mismatch": 10,
                "vector_rule/page_without_caption": 100,
            },
        )

    def test_source_safe_dimensions_preserve_heterogeneity_without_parser_promotion(self) -> None:
        classification = self.payload["classification"]
        dimensions = classification["structural_dimensions"]
        self.assertEqual(sum(dimensions["width_band"].values()), 841)
        self.assertEqual(sum(dimensions["row_band"].values()), 841)
        self.assertEqual(sum(dimensions["topology"].values()), 841)
        self.assertEqual(sum(dimensions["grouped_source_block_composition"].values()), 731)
        self.assertFalse(self.payload["conclusion"]["bounded_correction_proven"])
        self.assertFalse(self.payload["conclusion"]["recognized_caption_coverage_reduced"])
        self.assertFalse(self.payload["conclusion"]["parser_promotion_performed"])
        self.assertTrue(self.payload["conclusion"]["unsupported_families_remain_explicit"])

        forbidden = {
            "text", "caption_text", "source_text", "candidate_id", "caption_id",
            "private_locator", "source_locator", "cell_text", "header_text",
            "lookup_semantics", "compliance_semantics",
        }

        def walk(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(self.payload)
        self.assertFalse(self.payload["source"]["protected_source_expression_retained"])
        self.assertFalse(self.payload["source"]["private_source_locator_retained"])


if __name__ == "__main__":
    unittest.main()
