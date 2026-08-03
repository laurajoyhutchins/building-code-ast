from __future__ import annotations

import unittest

from building_code_ast.ingest.ibc2018.vector_regions import (
    cluster_vector_drawings,
    extract_document_vector_evidence,
    extract_page_vector_regions,
    geometry_fingerprint,
    normalize_drawing,
    validate_vector_evidence,
)


class _Rect:
    width = 612.0
    height = 792.0


class _FakePage:
    rect = _Rect()

    def get_cdrawings(self):
        return [
            {"rect": (0.0, 0.0, 612.0, 792.0), "items": (("re",),), "type": "f"},
            {"rect": (100.0, 100.0, 240.0, 220.0), "items": (("c",),) * 9, "type": "s"},
        ]

    def get_text(self, mode):
        if mode != "blocks":
            raise AssertionError(mode)
        return [(40.0, 40.0, 200.0, 60.0, "header", 0, 0)]


class _FakeDocument:
    page_count = 2

    def __getitem__(self, index):
        return _FakePage()


class VectorRegionTests(unittest.TestCase):
    def test_normalize_drawing_rejects_page_background_and_tiny_glyphs(self) -> None:
        self.assertIsNone(
            normalize_drawing(
                {"rect": (0.0, 0.0, 612.0, 792.0), "items": (("re",),), "type": "f"},
                page_width=612.0,
                page_height=792.0,
                text_boxes=(),
            )
        )
        self.assertIsNone(
            normalize_drawing(
                {"rect": (100.0, 100.0, 105.0, 107.0), "items": (("c",),) * 8, "type": "f"},
                page_width=612.0,
                page_height=792.0,
                text_boxes=((90.0, 90.0, 150.0, 120.0),),
            )
        )

    def test_normalize_drawing_keeps_long_rule_and_large_curve(self) -> None:
        rule = normalize_drawing(
            {"rect": (100.0, 200.0, 300.0, 200.5), "items": (("l",),), "type": "s"},
            page_width=612.0,
            page_height=792.0,
            text_boxes=(),
        )
        curve = normalize_drawing(
            {"rect": (120.0, 220.0, 190.0, 310.0), "items": (("c",),) * 12, "type": "s"},
            page_width=612.0,
            page_height=792.0,
            text_boxes=(),
        )
        self.assertIsNotNone(rule)
        self.assertIsNotNone(curve)
        self.assertEqual(rule["line_count"], 1)
        self.assertEqual(curve["curve_count"], 12)

    def test_cluster_vector_drawings_merges_nearby_paths_deterministically(self) -> None:
        drawings = [
            {"bbox": [100.0, 100.0, 180.0, 180.0], "line_count": 2, "curve_count": 4, "rect_count": 0, "fill_count": 0, "stroke_count": 1},
            {"bbox": [184.0, 105.0, 250.0, 175.0], "line_count": 3, "curve_count": 1, "rect_count": 0, "fill_count": 0, "stroke_count": 1},
            {"bbox": [400.0, 400.0, 470.0, 470.0], "line_count": 1, "curve_count": 6, "rect_count": 0, "fill_count": 1, "stroke_count": 0},
        ]
        first = cluster_vector_drawings(drawings, pdf_page=12, gap=8.0)
        second = cluster_vector_drawings(list(reversed(drawings)), pdf_page=12, gap=8.0)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0]["drawing_count"], 2)
        self.assertEqual(first[0]["bbox"], [100.0, 100.0, 250.0, 180.0])

    def test_geometry_fingerprint_is_stable_under_input_order(self) -> None:
        a = {"bbox": [1.0, 2.0, 30.0, 40.0], "line_count": 2, "curve_count": 3, "rect_count": 1}
        b = {"bbox": [4.0, 5.0, 20.0, 25.0], "line_count": 7, "curve_count": 0, "rect_count": 0}
        self.assertEqual(geometry_fingerprint([a, b]), geometry_fingerprint([b, a]))

    def test_extract_page_vector_regions_uses_source_safe_geometry_only(self) -> None:
        payload = extract_page_vector_regions(_FakePage(), pdf_page=4)
        self.assertEqual(payload["pdf_page"], 4)
        self.assertEqual(len(payload["regions"]), 1)
        self.assertNotIn("text", str(payload).lower())

    def test_extract_document_vector_evidence_binds_exact_source_identity(self) -> None:
        payload = extract_document_vector_evidence(
            _FakeDocument(),
            source_sha256="c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d",
            source_size_bytes=32_608_171,
        )
        self.assertEqual(payload["source_page_count"], 2)
        self.assertEqual([item["pdf_page"] for item in payload["pages"]], [1, 2])

    def test_validate_vector_evidence_requires_exact_identity_and_page_coverage(self) -> None:
        evidence = {
            "source_sha256": "c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d",
            "source_size_bytes": 32_608_171,
            "source_page_count": 761,
            "pages": [{"pdf_page": page, "regions": []} for page in range(1, 762)],
        }
        validate_vector_evidence(evidence)
        evidence["pages"] = evidence["pages"][:-1]
        with self.assertRaisesRegex(ValueError, "all 761"):
            validate_vector_evidence(evidence)


if __name__ == "__main__":
    unittest.main()
