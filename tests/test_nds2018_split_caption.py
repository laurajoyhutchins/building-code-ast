from __future__ import annotations

import unittest

import building_code_ast.ingest.nds2018_layout as nds2018_layout
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan


def _styled_block(
    page: int,
    bbox: tuple[float, float, float, float],
    text: str,
    number: int,
    *,
    font: str = "FranklinGothic-Book",
    size: float = 8.0,
) -> PdfBlock:
    line = PdfLine(
        bbox=bbox,
        spans=(PdfSpan(bbox=bbox, text=text, font=font, size=size, flags=0),),
    )
    return PdfBlock(page, bbox, text, number, lines=(line,))


class Nds2018SplitCaptionTests(unittest.TestCase):
    def test_recovers_only_adjacent_same_style_numbered_body_split_caption_locator(self) -> None:
        recover = getattr(nds2018_layout, "recover_nds2018_split_caption_locators", None)
        self.assertIsNotNone(recover)

        blocks = (
            _styled_block(174, (45.4, 69.7, 80.7, 83.9), "Figure", 1),
            _styled_block(174, (87.1, 61.4, 335.2, 85.4), "7 Synthetic caption title", 2),
            _styled_block(175, (106.6, 334.7, 137.2, 348.9), "Table", 3),
            _styled_block(175, (143.5, 334.7, 366.8, 348.9), "8 Synthetic caption title", 4),
            _styled_block(176, (45.0, 100.0, 80.0, 114.0), "Table", 5),
            _styled_block(176, (100.0, 100.0, 300.0, 114.0), "9 Too far away", 6),
            _styled_block(177, (45.0, 100.0, 80.0, 114.0), "Figure", 7),
            _styled_block(
                177,
                (86.0, 100.0, 260.0, 114.0),
                "10 Different observed style",
                8,
                font="Other-Font",
            ),
            _styled_block(10, (45.0, 100.0, 80.0, 114.0), "Table", 9),
            _styled_block(10, (86.0, 100.0, 260.0, 114.0), "11 Front matter listing", 10),
        )

        recoveries = recover(blocks)

        self.assertEqual(
            [(item.kind, item.locator, item.keyword_block_number, item.locator_block_number) for item in recoveries],
            [
                ("figure", "7", 1, 2),
                ("table", "8", 3, 4),
            ],
        )

    def test_does_not_infer_locator_from_private_use_glyphs(self) -> None:
        recover = getattr(nds2018_layout, "recover_nds2018_split_caption_locators", None)
        self.assertIsNotNone(recover)
        blocks = (
            _styled_block(180, (45.0, 100.0, 80.0, 114.0), "Figure", 1),
            _styled_block(180, (86.0, 100.0, 260.0, 114.0), "\ue001 Synthetic glyph-prefixed block", 2),
        )
        self.assertEqual(recover(blocks), ())


if __name__ == "__main__":
    unittest.main()
