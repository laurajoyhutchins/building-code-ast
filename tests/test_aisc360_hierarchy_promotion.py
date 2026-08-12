from __future__ import annotations

import unittest

from building_code_ast.aisc360_hierarchy_characterization import HierarchyPageObservation
from building_code_ast.aisc360_hierarchy_promotion import promote_aisc360_hierarchy
from building_code_ast.aisc360_raster_hierarchy_observation import (
    AISC360_DERIVATIVE_SHA256,
    AISC360_REPRESENTATIVE_RENDER_RECIPE,
    RasterHierarchyPageObservation,
    summarize_raster_hierarchy_observations,
)


def _raster_summary(*, page: int, text: str) -> dict[str, object]:
    return summarize_raster_hierarchy_observations(
        [
            RasterHierarchyPageObservation(
                page_number=page,
                source_derivative_sha256=AISC360_DERIVATIVE_SHA256,
                render_sha256="a" * 64,
                render_dpi=600,
                render_renderer="pdftoppm",
                render_renderer_version="25.06.0",
                render_output_format="png",
                recovery_backend="source-safe-test",
                recovered_text=text,
            )
        ]
    )


def _durable_raster_receipt(*, page: int, locator: str) -> dict[str, object]:
    return {
        "schema": "aisc360-raster-hierarchy-observation-v1",
        "component": "ansi-aisc-360-16",
        "source_derivative": {
            "sha256": AISC360_DERIVATIVE_SHA256,
            "byte_count": 1,
            "page_count": 2,
        },
        "observation_boundary": {
            "source_kind": "raster_recovery",
            "render_recipe": AISC360_REPRESENTATIVE_RENDER_RECIPE,
            "recovery_backend": "source-safe-test",
            "protected_source_text_retained": False,
            "parser_promotion_performed": False,
        },
        "representative_observations": [
            {
                "page": page,
                "render_sha256": "a" * 64,
                "recovered_text_sha256": "b" * 64,
                "dotted_hierarchy_locators": [locator],
            }
        ],
        "claim": "synthetic source-safe receipt",
        "next_boundary": "synthetic-next-boundary",
    }


class Aisc360HierarchyPromotionTests(unittest.TestCase):
    def test_promotes_raster_candidates_alongside_embedded_anchors_without_source_prose(self) -> None:
        raster_summary = _raster_summary(page=2, text="1.3. SYNTHETIC RASTER HEADING")

        result = promote_aisc360_hierarchy(
            [
                HierarchyPageObservation(1, "CHAPTER A\nsynthetic embedded body"),
                HierarchyPageObservation(2, None),
                HierarchyPageObservation(3, "APPENDIX 1\nsynthetic appendix body"),
                HierarchyPageObservation(4, "synthetic ordinary page"),
            ],
            raster_summary=raster_summary,
            expected_page_count=4,
        )

        self.assertEqual(result["source_derivative_sha256"], AISC360_DERIVATIVE_SHA256)
        self.assertEqual(
            result["page_measurement"],
            {
                "page_count": 4,
                "embedded_text_page_count": 3,
                "image_only_page_count": 1,
                "raster_observed_image_only_page_count": 1,
                "unobserved_image_only_page_count": 0,
            },
        )
        self.assertEqual(
            result["candidates"],
            [
                {
                    "page": 1,
                    "kind": "chapter",
                    "locator": "A",
                    "source_kind": "embedded_text",
                },
                {
                    "page": 2,
                    "kind": "numbered_hierarchy",
                    "locator": "1.3",
                    "source_kind": "raster_recovery",
                    "render_sha256": "a" * 64,
                    "recovered_text_sha256": raster_summary["observations"][0]["recovered_text_sha256"],
                    "recovery_backend": "source-safe-test",
                },
                {
                    "page": 3,
                    "kind": "appendix",
                    "locator": "1",
                    "source_kind": "embedded_text",
                },
            ],
        )
        self.assertTrue(result["combined_hierarchy_complete"])
        self.assertFalse(result["document_ast_promotion_performed"])
        rendered = repr(result)
        self.assertNotIn("SYNTHETIC RASTER HEADING", rendered)
        self.assertNotIn("synthetic embedded body", rendered)
        self.assertNotIn("synthetic appendix body", rendered)

    def test_promotes_the_durable_raster_receipt_shape_used_by_the_repository(self) -> None:
        receipt = _durable_raster_receipt(page=2, locator="1.3")

        result = promote_aisc360_hierarchy(
            [
                HierarchyPageObservation(1, "CHAPTER A"),
                HierarchyPageObservation(2, None),
            ],
            raster_summary=receipt,
            expected_page_count=2,
        )

        self.assertEqual(
            result["candidates"],
            [
                {
                    "page": 1,
                    "kind": "chapter",
                    "locator": "A",
                    "source_kind": "embedded_text",
                },
                {
                    "page": 2,
                    "kind": "numbered_hierarchy",
                    "locator": "1.3",
                    "source_kind": "raster_recovery",
                    "render_sha256": "a" * 64,
                    "recovered_text_sha256": "b" * 64,
                    "recovery_backend": "source-safe-test",
                },
            ],
        )
        self.assertNotIn("claim", repr(result))
        self.assertNotIn("next_boundary", repr(result))

    def test_raster_candidate_must_reference_an_image_only_page(self) -> None:
        raster_summary = _raster_summary(page=1, text="1.3. SYNTHETIC")

        with self.assertRaisesRegex(ValueError, "image-only"):
            promote_aisc360_hierarchy(
                [HierarchyPageObservation(1, "CHAPTER A")],
                raster_summary=raster_summary,
                expected_page_count=1,
            )

    def test_wrong_raster_derivative_identity_is_rejected(self) -> None:
        raster_summary = _raster_summary(page=2, text="1.3. SYNTHETIC")
        raster_summary["source_derivative_sha256"] = "b" * 64

        with self.assertRaisesRegex(ValueError, "source derivative"):
            promote_aisc360_hierarchy(
                [
                    HierarchyPageObservation(1, "CHAPTER A"),
                    HierarchyPageObservation(2, None),
                ],
                raster_summary=raster_summary,
                expected_page_count=2,
            )


if __name__ == "__main__":
    unittest.main()
