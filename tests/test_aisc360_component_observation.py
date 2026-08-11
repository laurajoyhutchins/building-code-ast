from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "corpora/aisc-scm-15/ansi-aisc-360-16-layout-observation.json"


class Aisc360ComponentObservationTests(unittest.TestCase):
    def test_receipt_binds_verified_derivative_and_parent_range(self) -> None:
        payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(payload["component_id"], "ansi-aisc-360-16")
        self.assertEqual(
            payload["parent_artifact_sha256"],
            "c5fbe648fd81a7ecda10df115393bbb9492924c8ce22167fc6d86c8b87fd8e7f",
        )
        self.assertEqual(payload["parent_pdf_pages"], [1376, 2049])
        self.assertEqual(
            payload["derivative_sha256"],
            "6ba073e6549e0c7408909cde2261f2bc393c7e6bfc63392268bd51399338e126",
        )
        self.assertEqual(payload["derivative_size_bytes"], 64_464_266)
        self.assertEqual(payload["page_count"], 674)

    def test_text_layer_measurement_is_complete_and_exposes_mixed_source(self) -> None:
        payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
        text_layer = payload["text_layer"]

        self.assertEqual(text_layer["pages_with_embedded_text"], 561)
        self.assertEqual(text_layer["pages_without_embedded_text"], 113)
        self.assertEqual(
            text_layer["pages_with_embedded_text"]
            + text_layer["pages_without_embedded_text"],
            payload["page_count"],
        )
        self.assertEqual(text_layer["missing_text_run_count"], 95)
        self.assertEqual(text_layer["maximum_missing_text_run_length"], 3)
        self.assertFalse(text_layer["text_only_replay_complete"])

    def test_receipt_records_derivative_mechanics_without_source_expression(self) -> None:
        payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(payload["rotation_counts"], {"0": 674})
        self.assertEqual(payload["pages_with_one_image_reference"], 674)
        self.assertEqual(payload["outline_entry_count"], 0)
        self.assertEqual(payload["outline_note"], "derivative-production-omits-source-outline")

        rendered = json.dumps(payload, sort_keys=True)
        for forbidden in (
            "source_text",
            "page_text",
            "protected_text",
            "drive.google.com",
            "object_id",
            "local_path",
        ):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
