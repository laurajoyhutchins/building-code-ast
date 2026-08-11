from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.aisc360_image_only_measurement import (
    PageSurfaceObservation,
    summarize_image_only_pages,
)


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "corpora/aisc-scm-15/ansi-aisc-360-16-image-only-pages.json"


class Aisc360ImageOnlyMeasurementTests(unittest.TestCase):
    def test_summary_distinguishes_full_page_image_only_pages_from_text_pages(self) -> None:
        summary = summarize_image_only_pages(
            (
                PageSurfaceObservation(1, True, 1, 1.0),
                PageSurfaceObservation(2, False, 1, 0.99999),
                PageSurfaceObservation(3, False, 1, 1.0),
                PageSurfaceObservation(4, True, 1, 1.0),
                PageSurfaceObservation(5, False, 1, 1.0),
            )
        )

        self.assertEqual(summary["page_count"], 5)
        self.assertEqual(summary["pages_with_embedded_text"], 2)
        self.assertEqual(summary["image_only_page_count"], 3)
        self.assertEqual(summary["image_only_pages"], [2, 3, 5])
        self.assertEqual(summary["image_only_run_count"], 2)
        self.assertEqual(summary["maximum_image_only_run_length"], 2)
        self.assertTrue(summary["all_image_only_pages_are_single_full_page_images"])

    def test_summary_does_not_promote_partial_image_pages_to_full_page_image_family(self) -> None:
        summary = summarize_image_only_pages(
            (
                PageSurfaceObservation(1, False, 1, 0.50),
                PageSurfaceObservation(2, False, 2, 1.0),
            )
        )

        self.assertFalse(summary["all_image_only_pages_are_single_full_page_images"])

    def test_exact_source_receipt_is_source_safe_and_records_measured_denominator(self) -> None:
        payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(payload["component_id"], "ansi-aisc-360-16")
        self.assertEqual(
            payload["derivative_sha256"],
            "6ba073e6549e0c7408909cde2261f2bc393c7e6bfc63392268bd51399338e126",
        )
        self.assertEqual(payload["page_count"], 674)
        self.assertEqual(payload["pages_with_embedded_text"], 561)
        self.assertEqual(payload["image_only_page_count"], 113)
        self.assertEqual(payload["image_only_run_count"], 95)
        self.assertEqual(payload["maximum_image_only_run_length"], 3)
        self.assertTrue(payload["all_image_only_pages_are_single_full_page_images"])
        self.assertEqual(len(payload["image_only_pages"]), 113)

        rendered = json.dumps(payload, sort_keys=True)
        for forbidden in (
            "source_text",
            "page_text",
            "protected_text",
            "drive.google.com",
            "object_id",
            "local_path",
            "ocr_text",
        ):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
