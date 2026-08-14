from __future__ import annotations

import hashlib
import unittest

from building_code_ast.pdf_enrichment import (
    TextOrigin,
    searchable_text_entry_from_recovery,
)
from building_code_ast.recovery_observation import (
    CoordinateSpace,
    RecoveredTextPayloadState,
    RecoveryObservation,
    RecoveryRegion,
    RecoverySourceIdentity,
    RecoverySourceKind,
    RecoveryTool,
)


_PRIVATE_TEXT = "synthetic private recovered text"


def _observation(
    *,
    payload_state: RecoveredTextPayloadState = RecoveredTextPayloadState.PRIVATE_RETRIEVABLE,
    source_kind: RecoverySourceKind = RecoverySourceKind.RASTER_RECOVERY,
    coordinate_space: CoordinateSpace = CoordinateSpace.PDF_POINTS,
    bbox: tuple[float, float, float, float] | None = (10.0, 20.0, 30.0, 40.0),
) -> RecoveryObservation:
    return RecoveryObservation(
        source=RecoverySourceIdentity(
            sha256="a" * 64,
            size_bytes=1234,
            page_count=10,
            media_type="application/pdf",
        ),
        region=RecoveryRegion(
            page_number=3,
            coordinate_space=coordinate_space,
            bbox=bbox,
        ),
        source_kind=source_kind,
        render=RecoveryTool(
            backend="pdftoppm",
            version="25.06.0",
            parameters=(("dpi", "600"),),
            output_sha256="b" * 64,
        ),
        recovery=RecoveryTool(
            backend="tesseract",
            version="5.5.0",
            parameters=(("psm", "6"),),
        ),
        recovered_text_sha256=hashlib.sha256(_PRIVATE_TEXT.encode("utf-8")).hexdigest(),
        payload_state=payload_state,
    )


class PdfEnrichmentRecoveryTests(unittest.TestCase):
    def test_private_digest_bound_raster_payload_becomes_searchable_text(self) -> None:
        entry = searchable_text_entry_from_recovery(_observation(), _PRIVATE_TEXT)

        self.assertEqual(entry.page_number, 3)
        self.assertEqual(entry.text, _PRIVATE_TEXT)
        self.assertEqual(entry.bbox, (10.0, 20.0, 30.0, 40.0))
        self.assertEqual(entry.text_origin, TextOrigin.RASTER_RECOVERY)

    def test_private_ocr_payload_preserves_ocr_origin(self) -> None:
        entry = searchable_text_entry_from_recovery(
            _observation(source_kind=RecoverySourceKind.OCR_RECOVERY),
            _PRIVATE_TEXT,
        )

        self.assertEqual(entry.text_origin, TextOrigin.OCR)

    def test_digest_only_recovery_cannot_feed_enrichment(self) -> None:
        with self.assertRaisesRegex(ValueError, "digest-only"):
            searchable_text_entry_from_recovery(
                _observation(payload_state=RecoveredTextPayloadState.DIGEST_ONLY),
                _PRIVATE_TEXT,
            )

    def test_private_payload_digest_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "digest"):
            searchable_text_entry_from_recovery(_observation(), "different text")

    def test_enrichment_requires_pdf_point_region_bbox(self) -> None:
        with self.assertRaisesRegex(ValueError, "PDF points"):
            searchable_text_entry_from_recovery(
                _observation(coordinate_space=CoordinateSpace.RASTER_PIXELS),
                _PRIVATE_TEXT,
            )
        with self.assertRaisesRegex(ValueError, "bbox"):
            searchable_text_entry_from_recovery(
                _observation(bbox=None),
                _PRIVATE_TEXT,
            )


if __name__ == "__main__":
    unittest.main()
