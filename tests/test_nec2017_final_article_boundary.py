from __future__ import annotations

import unittest

from building_code_ast.ingest.nec2017 import select_article_blocks
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfOutlineItem, PdfPage, normalize_block_text


class Nec2017FinalArticleBoundaryTests(unittest.TestCase):
    def test_final_numeric_article_stops_at_following_chapter_root(self) -> None:
        layout = PdfLayoutDocument(
            file_name="synthetic-nec.pdf",
            outline=(
                PdfOutlineItem(2, "840 Premises-Powered Broadband Communications Systems", 1),
                PdfOutlineItem(1, "Chapter 9 Tables", 2),
                PdfOutlineItem(1, "Informative Annex A Product Safety Standards", 3),
            ),
            pages=(
                PdfPage(
                    page_number=1,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(1, (54.0, 100.0, 303.0, 130.0), "ARTICLE 840\nPremises-Powered Broadband Communications Systems"),
                        PdfBlock(1, (54.0, 150.0, 303.0, 180.0), "840.1 Scope. Synthetic article content."),
                    ),
                ),
                PdfPage(
                    page_number=2,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(2, (54.0, 100.0, 303.0, 130.0), "Chapter 9 Tables"),
                        PdfBlock(2, (54.0, 150.0, 303.0, 180.0), "Table 1 Synthetic chapter content"),
                    ),
                ),
                PdfPage(
                    page_number=3,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(3, (54.0, 100.0, 303.0, 130.0), "Informative Annex A Product Safety Standards"),
                    ),
                ),
            ),
        )

        selected = select_article_blocks(layout, "840")

        self.assertEqual(
            [normalize_block_text(block.text) for block in selected],
            [
                "ARTICLE 840 Premises-Powered Broadband Communications Systems",
                "840.1 Scope. Synthetic article content.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
