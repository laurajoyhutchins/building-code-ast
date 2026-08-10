from __future__ import annotations

import unittest

from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan


class PdfLineSpanEvidenceTests(unittest.TestCase):
    def test_block_preserves_optional_line_and_span_source_evidence(self) -> None:
        span = PdfSpan(
            bbox=(72.0, 100.0, 180.0, 112.0),
            text="G1.2.4. SYNTHETIC HEADING",
            font="Synthetic-Bold",
            size=9.0,
            flags=16,
        )
        line = PdfLine(
            bbox=(72.0, 100.0, 180.0, 112.0),
            spans=(span,),
        )
        block = PdfBlock(
            page_number=47,
            bbox=(72.0, 100.0, 300.0, 140.0),
            text="G1.2.4. SYNTHETIC HEADING\nSynthetic body.\n",
            block_number=6,
            lines=(line,),
        )

        self.assertEqual(line.text, "G1.2.4. SYNTHETIC HEADING")
        self.assertEqual(block.lines, (line,))
        self.assertEqual(
            block.to_dict()["lines"],
            [
                {
                    "bbox": [72.0, 100.0, 180.0, 112.0],
                    "spans": [
                        {
                            "bbox": [72.0, 100.0, 180.0, 112.0],
                            "text": "G1.2.4. SYNTHETIC HEADING",
                            "font": "Synthetic-Bold",
                            "size": 9.0,
                            "flags": 16,
                        }
                    ],
                }
            ],
        )

    def test_legacy_block_serialization_is_unchanged_without_line_evidence(self) -> None:
        block = PdfBlock(
            page_number=1,
            bbox=(10.0, 20.0, 30.0, 40.0),
            text="Legacy text",
            block_number=3,
        )
        self.assertEqual(
            block.to_dict(),
            {
                "page_number": 1,
                "bbox": [10.0, 20.0, 30.0, 40.0],
                "text": "Legacy text",
                "block_number": 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
