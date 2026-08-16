from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast.aisc360_hierarchy_characterization import HierarchyPageObservation
from building_code_ast.aisc360_hierarchy_promotion import promote_aisc360_hierarchy
from building_code_ast.aisc360_raster_hierarchy_observation import (
    AISC360_COMPONENT_PAGE_COUNT,
    AISC360_DERIVATIVE_SHA256,
    AISC360_DERIVATIVE_SIZE_BYTES,
    AISC360_REPRESENTATIVE_RENDER_RECIPE,
)


class Aisc360RecoveryBackendProvenanceTests(unittest.TestCase):
    def test_committed_receipt_preserves_legacy_visual_transcription_backend(self) -> None:
        root = Path(__file__).resolve().parents[1]
        receipt = json.loads(
            (root / "corpora" / "aisc-scm-15" / "ansi-aisc-360-16-raster-hierarchy-observations.json").read_text()
        )
        observations = {item["page"]: item for item in receipt["representative_observations"]}

        self.assertEqual(
            {page: observations[page]["recovery_backend"] for page in (243, 285)},
            {243: "visual_transcription_from_exact_render", 285: "visual_transcription_from_exact_render"},
        )
        self.assertEqual(
            {observations[page].get("recovery_backend", receipt["observation_boundary"]["recovery_backend"]) for page in (16, 17, 36, 300, 353, 424, 433, 461)},
            {"tesseract_5.5.0_psm6_from_exact_render"},
        )
        self.assertNotIn("recovered_text", json.dumps(receipt, sort_keys=True))

    def test_durable_receipt_uses_per_observation_backend_when_present(self) -> None:
        receipt = {
            "schema": "aisc360-raster-hierarchy-observation-v1",
            "component": "ansi-aisc-360-16",
            "source_derivative": {
                "sha256": AISC360_DERIVATIVE_SHA256,
                "byte_count": AISC360_DERIVATIVE_SIZE_BYTES,
                "page_count": AISC360_COMPONENT_PAGE_COUNT,
            },
            "observation_boundary": {
                "source_kind": "raster_recovery",
                "render_recipe": AISC360_REPRESENTATIVE_RENDER_RECIPE,
                "recovery_backend": "tesseract_5.5.0_psm6_from_exact_render",
                "protected_source_text_retained": False,
                "parser_promotion_performed": False,
            },
            "representative_observations": [
                {
                    "page": 2,
                    "render_sha256": "a" * 64,
                    "recovered_text_sha256": "b" * 64,
                    "recovery_backend": "visual_transcription_from_exact_render",
                    "dotted_hierarchy_locators": ["4.2"],
                }
            ],
            "claim": "synthetic source-safe mixed-backend receipt",
            "next_boundary": "synthetic-next-boundary",
        }

        result = promote_aisc360_hierarchy(
            [HierarchyPageObservation(1, "CHAPTER A"), HierarchyPageObservation(2, None)],
            raster_summary=receipt,
            expected_page_count=2,
        )
        raster_candidate = next(item for item in result["candidates"] if item["source_kind"] == "raster_recovery")
        self.assertEqual(raster_candidate["recovery_backend"], "visual_transcription_from_exact_render")


if __name__ == "__main__":
    unittest.main()
