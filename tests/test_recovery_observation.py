from __future__ import annotations

import hashlib
import unittest

from building_code_ast.recovery_observation import (
    CoordinateSpace,
    RecoveredTextPayloadState,
    RecoveryObservation,
    RecoveryRegion,
    RecoverySourceIdentity,
    RecoverySourceKind,
    RecoveryTool,
)


class RecoveryObservationContractTests(unittest.TestCase):
    def _observation(
        self,
        *,
        payload_state: RecoveredTextPayloadState = RecoveredTextPayloadState.DIGEST_ONLY,
    ) -> RecoveryObservation:
        text = "synthetic private recovered text"
        return RecoveryObservation(
            source=RecoverySourceIdentity(
                sha256="a" * 64,
                size_bytes=1234,
                page_count=10,
                media_type="application/pdf",
            ),
            region=RecoveryRegion(
                page_number=3,
                coordinate_space=CoordinateSpace.PDF_POINTS,
                bbox=(10.0, 20.0, 30.0, 40.0),
            ),
            source_kind=RecoverySourceKind.RASTER_RECOVERY,
            render=RecoveryTool(
                backend="pdftoppm",
                version="25.06.0",
                parameters=(("dpi", "600"), ("output_format", "png")),
                output_sha256="b" * 64,
            ),
            recovery=RecoveryTool(
                backend="tesseract",
                version="5.5.0",
                parameters=(("psm", "6"),),
            ),
            recovered_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            payload_state=payload_state,
            performed_operations=("render", "ocr"),
            omitted_operations=("semantic_promotion",),
            warnings=("synthetic warning",),
        )

    def test_durable_projection_is_source_safe_and_closed(self) -> None:
        durable = self._observation().to_dict()

        self.assertEqual(durable["schema"], "recovery-observation-v1")
        self.assertEqual(durable["payload_state"], "digest_only")
        self.assertEqual(durable["source_kind"], "raster_recovery")
        self.assertEqual(durable["region"]["coordinate_space"], "pdf_points")
        self.assertNotIn("recovered_text", repr(durable))
        self.assertNotIn("locator", repr(durable))
        self.assertNotIn("source_role", repr(durable))

    def test_digest_only_observation_cannot_authorize_downstream_payload_use(self) -> None:
        with self.assertRaisesRegex(ValueError, "digest-only"):
            self._observation().verify_private_payload("synthetic private recovered text")

    def test_private_payload_binding_requires_exact_recovered_text_digest(self) -> None:
        observation = self._observation(
            payload_state=RecoveredTextPayloadState.PRIVATE_RETRIEVABLE,
        )

        observation.verify_private_payload("synthetic private recovered text")
        with self.assertRaisesRegex(ValueError, "digest"):
            observation.verify_private_payload("different text")

    def test_invalid_identity_region_and_tool_provenance_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            RecoverySourceIdentity(
                sha256="bad",
                size_bytes=1234,
                page_count=10,
                media_type="application/pdf",
            )
        with self.assertRaisesRegex(ValueError, "ordered"):
            RecoveryRegion(
                page_number=1,
                coordinate_space=CoordinateSpace.PDF_POINTS,
                bbox=(30.0, 20.0, 10.0, 40.0),
            )
        with self.assertRaisesRegex(ValueError, "backend"):
            RecoveryTool(backend="", version="1", parameters=())


if __name__ == "__main__":
    unittest.main()
