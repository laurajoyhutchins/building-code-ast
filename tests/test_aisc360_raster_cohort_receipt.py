from __future__ import annotations

import json
import unittest
from pathlib import Path


class Aisc360RasterCohortReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        corpus = root / "corpora" / "aisc-scm-15"
        self.receipt = json.loads(
            (corpus / "ansi-aisc-360-16-raster-hierarchy-observations.json").read_text()
        )
        self.measurement = json.loads(
            (corpus / "ansi-aisc-360-16-hierarchy-promotion-measurement.json").read_text()
        )

    def test_bounded_cohort_expands_exact_image_only_denominator(self) -> None:
        pages = [item["page"] for item in self.receipt["representative_observations"]]
        self.assertEqual(pages, [16, 17, 36, 243, 285, 300, 353, 424, 433, 461])
        measurement = self.measurement["measurement"]
        self.assertEqual(measurement["embedded_text_page_count"], 561)
        self.assertEqual(measurement["image_only_page_count"], 113)
        self.assertEqual(measurement["raster_observed_image_only_page_count"], 10)
        self.assertEqual(measurement["unobserved_image_only_page_count"], 103)
        self.assertEqual(measurement["candidate_count"], 46)
        self.assertEqual(measurement["raster_numbered_hierarchy_candidate_count"], 8)
        self.assertFalse(measurement["combined_hierarchy_complete"])

    def test_new_cohort_is_source_safe_and_spans_declared_layout_strata(self) -> None:
        selection = self.receipt["cohort_selection"]
        self.assertEqual(selection["new_pages"], [36, 300, 353, 424, 433, 461])
        self.assertEqual(
            set(selection["covered_strata"]),
            {
                "zero_overlay/large_image",
                "zero_overlay/small_image",
                "one_overlay/large_image",
                "one_overlay/small_image",
                "two_overlay/large_image",
                "two_overlay/small_image",
            },
        )
        items = {
            item["page"]: item
            for item in self.receipt["representative_observations"]
            if item["page"] in selection["new_pages"]
        }
        self.assertEqual(set(items), set(selection["new_pages"]))
        self.assertTrue(all(item["dotted_hierarchy_locators"] == [] for item in items.values()))
        self.assertEqual(
            {page: item["source_safe_recovery_metrics"]["single_level_line_start_count"] for page, item in items.items()},
            {36: 0, 300: 0, 353: 0, 424: 0, 433: 1, 461: 1},
        )
        self.assertTrue(self.receipt["observation_boundary"]["protected_source_text_retained"] is False)
        self.assertFalse(self.receipt["observation_boundary"]["parser_promotion_performed"])
        self.assertFalse(self.measurement["provenance"]["single_level_raster_numbering_promoted"])
        rendered = json.dumps(self.receipt, sort_keys=True)
        for forbidden in ("recovered_text\"", "private_provider", "source_expression"):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
