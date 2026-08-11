from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AiscScm15SourceVerificationTests(unittest.TestCase):
    def _module(self):
        try:
            return importlib.import_module(
                "building_code_ast.aisc_scm15_source_verification"
            )
        except ModuleNotFoundError:
            self.fail("AISC SCM 15 exact-source verifier is not implemented")

    def _pdf_observation(self) -> dict[str, object]:
        return {
            "page_count": 3,
            "pdf_version": "1.7",
            "encrypted": False,
            "needs_password": False,
            "permissions_raw": -4,
            "page_label_rules": [
                {
                    "pdf_page_start": 1,
                    "style": "r",
                    "prefix": "",
                    "first_page_number": 1,
                }
            ],
            "outline": {
                "entry_count": 4,
                "max_depth": 2,
                "valid_target_count": 3,
                "invalid_target_count": 1,
            },
            "text_layer": {
                "pages_with_text": 2,
                "pages_without_text": [3],
            },
            "page_geometry": {
                "distinct_page_sizes": [
                    {
                        "width_points": 612.0,
                        "height_points": 792.0,
                        "page_count": 3,
                    }
                ]
            },
            "tool": {"name": "fake-pdf-observer", "version": "1"},
            "text": "protected source prose must never enter the receipt",
            "bookmark_titles": ["protected heading"],
        }

    def test_receipt_binds_exact_bytes_without_leaking_source_content_or_path(self) -> None:
        module = self._module()
        payload = b"abcdef"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "private-copy.pdf"
            source.write_bytes(payload)

            receipt = module.inspect_source(
                source,
                expected_size_bytes=len(payload),
                pdf_observer=lambda _path: self._pdf_observation(),
                component_ranges=(
                    module.ComponentRange("ansi-aisc-360-16", 1, 2),
                    module.ComponentRange("manual-part-17", 3, 3),
                ),
                verified_at_utc="2026-08-09T17:45:00Z",
            )

        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["publication_key"], "aisc-scm-15")
        self.assertEqual(receipt["artifact"]["filename"], "scm-15.pdf")
        self.assertEqual(receipt["artifact"]["size_bytes"], len(payload))
        self.assertEqual(
            receipt["artifact"]["sha256"], hashlib.sha256(payload).hexdigest()
        )
        self.assertEqual(receipt["pdf"]["page_count"], 3)
        self.assertEqual(
            receipt["component_ranges"],
            [
                {
                    "component_id": "ansi-aisc-360-16",
                    "first_pdf_page": 1,
                    "last_pdf_page": 2,
                },
                {
                    "component_id": "manual-part-17",
                    "first_pdf_page": 3,
                    "last_pdf_page": 3,
                },
            ],
        )
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn(str(source.parent), serialized)
        self.assertNotIn("protected source prose", serialized)
        self.assertNotIn("protected heading", serialized)
        self.assertNotIn('"text"', serialized)
        self.assertNotIn("bookmark_titles", serialized)

    def test_size_mismatch_fails_before_pdf_inspection(self) -> None:
        module = self._module()
        observer_called = False

        def observer(_path: Path) -> dict[str, object]:
            nonlocal observer_called
            observer_called = True
            return self._pdf_observation()

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"abcdef")
            with self.assertRaisesRegex(module.SourceVerificationError, "byte size"):
                module.inspect_source(
                    source,
                    expected_size_bytes=7,
                    pdf_observer=observer,
                )

        self.assertFalse(observer_called)

    def test_component_range_must_fit_inside_observed_pdf(self) -> None:
        module = self._module()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"abcdef")
            with self.assertRaisesRegex(module.SourceVerificationError, "page count"):
                module.inspect_source(
                    source,
                    expected_size_bytes=6,
                    pdf_observer=lambda _path: self._pdf_observation(),
                    component_ranges=(
                        module.ComponentRange("ansi-aisc-360-16", 2, 4),
                    ),
                )

    def test_component_range_parser_rejects_invalid_coordinates(self) -> None:
        module = self._module()
        self.assertEqual(
            module.parse_component_range("ansi-aisc-360-16=101-250"),
            module.ComponentRange("ansi-aisc-360-16", 101, 250),
        )
        for value in ("=1-2", "a=0-2", "a=3-2", "a=one-two", "a=1"):
            with self.subTest(value=value):
                with self.assertRaises(module.SourceVerificationError):
                    module.parse_component_range(value)

    def test_module_help_exposes_local_verification_entrypoint(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "building_code_ast.aisc_scm15_source_verification",
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--component-range", completed.stdout)
        self.assertIn("--output", completed.stdout)
        self.assertIn("scm-15.pdf", completed.stdout)


if __name__ == "__main__":
    unittest.main()
