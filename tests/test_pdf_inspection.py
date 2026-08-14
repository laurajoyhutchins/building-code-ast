from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from building_code_ast.pdf_inspection import (
    PageSurfaceObservation,
    RetainedPdfInspectionError,
    inspect_retained_pdf,
    summarize_image_only_pages,
)


class PdfInspectionTests(unittest.TestCase):
    def _pdf_observation(self) -> dict[str, object]:
        return {
            "page_count": 3,
            "pdf_version": "1.7",
            "encrypted": False,
            "needs_password": False,
            "permissions_raw": -4,
            "page_label_rules": [],
            "outline": {
                "entry_count": 0,
                "max_depth": 0,
                "valid_target_count": 0,
                "invalid_target_count": 0,
            },
            "text_layer": {"pages_with_text": 2, "pages_without_text": [3]},
            "page_geometry": {"distinct_page_sizes": []},
            "tool": {"name": "fake", "version": "1"},
            "protected_text": "must not survive sanitization",
        }

    def test_generic_inspection_binds_bytes_and_sanitizes_pdf_facts(self) -> None:
        payload = b"abcdef"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "arbitrary.pdf"
            source.write_bytes(payload)
            result = inspect_retained_pdf(
                source,
                expected_size_bytes=len(payload),
                pdf_observer=lambda _path: self._pdf_observation(),
            )

        self.assertEqual(result["size_bytes"], len(payload))
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result["pdf"]["page_count"], 3)
        self.assertNotIn("protected_text", result["pdf"])
        self.assertNotIn("publication", repr(result))

    def test_generic_inspection_rejects_symlink_before_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.pdf"
            target.write_bytes(b"abcdef")
            link = root / "link.pdf"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(RetainedPdfInspectionError, "symlink"):
                inspect_retained_pdf(
                    link,
                    expected_size_bytes=6,
                    pdf_observer=lambda _path: self._pdf_observation(),
                )

    def test_malformed_or_nonserializable_pdf_metadata_fails_closed(self) -> None:
        payload = b"abcdef"
        for observation, message in (
            ({"page_count": True}, "page_count"),
            ({"page_count": 3, "tool": {"value": object()}}, "non-serializable"),
        ):
            with self.subTest(observation=observation):
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "arbitrary.pdf"
                    source.write_bytes(payload)
                    with self.assertRaisesRegex(RetainedPdfInspectionError, message):
                        inspect_retained_pdf(
                            source,
                            expected_size_bytes=len(payload),
                            pdf_observer=lambda _path, value=observation: value,
                        )

    def test_page_surface_summary_is_publication_neutral(self) -> None:
        summary = summarize_image_only_pages(
            (
                PageSurfaceObservation(1, True, 1, 1.0),
                PageSurfaceObservation(2, False, 1, 1.0),
                PageSurfaceObservation(3, False, 1, 0.99999),
            )
        )

        self.assertEqual(summary["image_only_pages"], [2, 3])
        self.assertEqual(summary["image_only_run_count"], 1)
        self.assertTrue(summary["all_image_only_pages_are_single_full_page_images"])

    def test_page_surface_summary_requires_contiguous_component_pages(self) -> None:
        with self.assertRaisesRegex(ValueError, "each one-based component page"):
            summarize_image_only_pages(
                (
                    PageSurfaceObservation(1, True, 0, None),
                    PageSurfaceObservation(3, False, 1, 1.0),
                )
            )


if __name__ == "__main__":
    unittest.main()
