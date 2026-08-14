from __future__ import annotations

import unittest

from building_code_ast.pdf_observation import observe_pymupdf_page


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _Rect:
    width = 612.0
    height = 792.0
    x0 = 20.0
    y0 = 30.0
    x1 = 120.0
    y1 = 130.0


class _SyntheticPage:
    rect = _Rect()

    def get_text(self, kind: str, *, sort: bool = False) -> dict[str, object]:
        self.kind = kind
        self.sort = sort
        return {
            "blocks": [
                {
                    "type": 0,
                    "number": 4,
                    "bbox": (100.0, 80.0, 220.0, 240.0),
                    "lines": [
                        {
                            "bbox": (100.0, 80.0, 112.0, 220.0),
                            "dir": (0.0, -1.0),
                            "spans": [
                                {
                                    "bbox": (100.0, 80.0, 112.0, 220.0),
                                    "text": "ROTATED SOURCE LINE",
                                    "font": "Synthetic-Bold",
                                    "size": 9.0,
                                    "flags": 16,
                                }
                            ],
                        }
                    ],
                },
                {"type": 1, "number": 5, "bbox": (0.0, 0.0, 10.0, 10.0)},
            ]
        }

    def get_drawings(self) -> list[dict[str, object]]:
        return [
            {"items": [("l", _Point(10.0, 20.0), _Point(110.0, 20.0))]},
            {"items": [("re", _Rect())]},
        ]


class PdfObservationTests(unittest.TestCase):
    def test_page_observation_preserves_positioned_text_direction_and_vector_rules(self) -> None:
        source = _SyntheticPage()

        page = observe_pymupdf_page(source, page_number=3)

        self.assertEqual(source.kind, "dict")
        self.assertFalse(source.sort)
        self.assertEqual(page.page_number, 3)
        self.assertEqual((page.width, page.height), (612.0, 792.0))
        self.assertEqual(len(page.blocks), 1)
        block = page.blocks[0]
        self.assertEqual(block.block_number, 4)
        self.assertEqual(block.block_id, "p3:b4")
        self.assertEqual(block.text, "ROTATED SOURCE LINE")
        line = block.lines[0]
        self.assertEqual(line.line_id, "p3:b4:l0")
        self.assertEqual(line.direction, (0.0, -1.0))
        span = line.spans[0]
        self.assertEqual(span.span_id, "p3:b4:l0:s0")
        self.assertEqual(span.font_name, "Synthetic-Bold")
        self.assertEqual(span.font_size, 9.0)
        self.assertEqual(span.flags, 16)

        self.assertEqual(len(page.rules), 5)
        self.assertTrue(page.rules[0].horizontal)
        self.assertEqual(
            (page.rules[0].x0, page.rules[0].y0, page.rules[0].x1, page.rules[0].y1),
            (10.0, 20.0, 110.0, 20.0),
        )

        layout_page = page.to_page_lines()
        self.assertEqual(layout_page.page_number, 3)
        self.assertEqual(layout_page.lines[0].text, "ROTATED SOURCE LINE")
        self.assertEqual(layout_page.lines[0].fragments[0].font_name, "Synthetic-Bold")
        self.assertEqual(layout_page.rules, page.rules)

    def test_observation_model_contains_no_publication_or_source_identity(self) -> None:
        page = observe_pymupdf_page(_SyntheticPage(), page_number=1)

        rendered = repr(page).casefold()
        for forbidden in ("publication", "edition", "source_sha", "artifact_id"):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
