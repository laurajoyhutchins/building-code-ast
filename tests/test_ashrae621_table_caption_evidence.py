from __future__ import annotations

import unittest

from building_code_ast.ingest.ashrae621_table_geometry import measure_ashrae621_table_geometry
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfLine, PdfPage, PdfSpan


def _line(text: str) -> PdfLine:
    return PdfLine(
        bbox=(72.0, 40.0, 320.0, 52.0),
        spans=(
            PdfSpan(
                bbox=(72.0, 40.0, 320.0, 52.0),
                text=text,
                font="Synthetic",
                size=9.0,
                flags=0,
            ),
        ),
    )


class Ashrae621TableCaptionEvidenceTests(unittest.TestCase):
    def test_visual_line_evidence_distinguishes_caption_marker_from_leading_prose_reference(self) -> None:
        document = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=1,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(
                            1,
                            (72.0, 40.0, 320.0, 52.0),
                            "Table C-3 provides synthetic information.",
                            0,
                            lines=(_line("Table C-3 provides synthetic information."),),
                        ),
                        PdfBlock(
                            1,
                            (72.0, 60.0, 320.0, 72.0),
                            "TABLE C-3 Synthetic caption",
                            1,
                            lines=(_line("TABLE C-3 Synthetic caption"),),
                        ),
                    ),
                ),
            ),
            outline=(),
        )

        result = measure_ashrae621_table_geometry(document)

        self.assertEqual(result.caption_occurrence_count, 1)
        self.assertEqual(result.native_identifier_count, 1)
        self.assertEqual(result.occurrences[0].native_locator, "C-3")
        self.assertEqual(result.occurrences[0].block_number, 1)


if __name__ == "__main__":
    unittest.main()
