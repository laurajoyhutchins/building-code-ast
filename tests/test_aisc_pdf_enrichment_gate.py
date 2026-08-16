from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

try:
    import fitz
except ImportError:  # optional PDF enrichment dependency
    fitz = None

from building_code_ast.aisc360_raster_hierarchy_observation import (
    AISC360_COMPONENT_PAGE_COUNT,
    AISC360_DERIVATIVE_SHA256,
    AISC360_DERIVATIVE_SIZE_BYTES,
    AISC360_REPRESENTATIVE_RENDER_RECIPE,
    recovery_observation_from_source_safe_fields,
)
from building_code_ast.pdf_enrichment import (
    EvidenceOrigin,
    PdfEnrichmentPlan,
    PdfSourceIdentity,
    SearchableTextEntry,
    SearchableTextOperation,
    TextOrigin,
    enrich_pdf,
)
from building_code_ast.recovery_observation import RecoveredTextPayloadState


class AiscPrivateRecoveryGateTests(unittest.TestCase):
    def test_source_safe_bridge_binds_private_payload_to_explicit_pdf_point_bbox(self) -> None:
        bbox = (0.0, 0.0, 130.348999, 195.302994)
        observation = recovery_observation_from_source_safe_fields(
            page_number=16,
            source_derivative_sha256=AISC360_DERIVATIVE_SHA256,
            source_size_bytes=AISC360_DERIVATIVE_SIZE_BYTES,
            source_page_count=AISC360_COMPONENT_PAGE_COUNT,
            render_sha256="a" * 64,
            render_recipe=AISC360_REPRESENTATIVE_RENDER_RECIPE,
            recovery_backend="tesseract_5.5.0_psm6_from_exact_render",
            recovered_text_sha256="b" * 64,
            bbox=bbox,
            payload_state=RecoveredTextPayloadState.PRIVATE_RETRIEVABLE,
        )

        self.assertEqual(observation.region.bbox, bbox)
        self.assertTrue(observation.downstream_payload_available)
        self.assertIn("protected_text_retention", observation.performed_operations)
        self.assertNotIn("protected_text_retention", observation.omitted_operations)


@unittest.skipUnless(
    fitz is not None and importlib.util.find_spec("pypdf") is not None,
    "PDF enrichment runtime dependencies are not installed",
)
class BoundedSearchableTextTests(unittest.TestCase):
    def test_searchable_text_autofits_bounded_region_without_visible_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            output = Path(directory) / "enriched.pdf"

            document = fitz.open()
            page = document.new_page(width=130.349, height=195.303)
            page.draw_rect(fitz.Rect(5, 5, 125, 190), color=(0, 0, 0), width=1)
            document.save(source)
            document.close()

            original_bytes = source.read_bytes()
            recovered_text = ("synthetic recovered text " * 120).strip()
            plan = PdfEnrichmentPlan(
                source=PdfSourceIdentity(
                    source_id="source:synthetic:bounded-searchable-text",
                    sha256=hashlib.sha256(original_bytes).hexdigest(),
                    size=len(original_bytes),
                    media_type="application/pdf",
                    page_count=1,
                ),
                operations=(
                    SearchableTextOperation(
                        evidence_origin=EvidenceOrigin.REVIEWED_SOURCE_OBSERVATION,
                        entries=(
                            SearchableTextEntry(
                                page_number=1,
                                text=recovered_text,
                                bbox=(0.0, 0.0, 130.349, 195.303),
                                text_origin=TextOrigin.RASTER_RECOVERY,
                            ),
                        ),
                    ),
                ),
            )

            receipt = enrich_pdf(source, output, plan)

            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertTrue(receipt.verification.visual_pages_identical)
            self.assertEqual(receipt.verification.searchable_text_target_pages, (1,))
            with fitz.open(output) as enriched:
                self.assertIn("synthetic recovered text", enriched[0].get_text("text"))


if __name__ == "__main__":
    unittest.main()