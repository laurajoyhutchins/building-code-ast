from __future__ import annotations

import unittest

from building_code_ast.ingest.pdf_layout import PdfLine, PdfSpan, _line_evidence_by_block


class _SyntheticPage:
    def get_text(self, kind: str, *, sort: bool = False) -> dict[str, object]:
        self.kind = kind
        self.sort = sort
        return {
            "blocks": [
                {
                    "type": 0,
                    "number": 4,
                    "lines": [
                        {
                            "bbox": (100.0, 80.0, 112.0, 220.0),
                            "dir": (0.0, -1.0),
                            "spans": [
                                {
                                    "bbox": (100.0, 80.0, 112.0, 220.0),
                                    "text": "ROTATED SOURCE LINE",
                                    "font": "Synthetic",
                                    "size": 9.0,
                                    "flags": 0,
                                }
                            ],
                        }
                    ],
                }
            ]
        }


class PdfWritingDirectionTests(unittest.TestCase):
    def test_pdf_line_serializes_nonhorizontal_writing_direction(self) -> None:
        line = PdfLine(
            bbox=(100.0, 80.0, 112.0, 220.0),
            spans=(
                PdfSpan(
                    bbox=(100.0, 80.0, 112.0, 220.0),
                    text="ROTATED SOURCE LINE",
                    font="Synthetic",
                    size=9.0,
                    flags=0,
                ),
            ),
            direction=(0.0, -1.0),
        )

        self.assertEqual(line.direction, (0.0, -1.0))
        self.assertEqual(line.to_dict()["direction"], [0.0, -1.0])

    def test_pdf_extractor_preserves_pymupdf_line_direction(self) -> None:
        page = _SyntheticPage()

        evidence = _line_evidence_by_block(page)

        self.assertEqual(page.kind, "dict")
        self.assertFalse(page.sort)
        self.assertEqual(evidence[4][0].direction, (0.0, -1.0))

    def test_horizontal_line_serialization_remains_legacy_compatible(self) -> None:
        line = PdfLine(
            bbox=(72.0, 100.0, 180.0, 112.0),
            spans=(
                PdfSpan(
                    bbox=(72.0, 100.0, 180.0, 112.0),
                    text="HORIZONTAL SOURCE LINE",
                    font="Synthetic",
                    size=9.0,
                    flags=0,
                ),
            ),
        )

        self.assertNotIn("direction", line.to_dict())


if __name__ == "__main__":
    unittest.main()
