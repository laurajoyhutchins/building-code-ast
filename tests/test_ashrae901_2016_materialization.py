from __future__ import annotations

import json
import unittest

from building_code_ast.ashrae901_2016_corpus import (
    ASHRAE_90_1_2016_SOURCE_SHA256,
    ASHRAE_90_1_2016_SOURCE_SIZE,
    materialize_ashrae901_2016_document_receipt,
)
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfLine,
    PdfPage,
    PdfSpan,
)


def _block(
    text: str,
    *,
    page: int,
    y: float,
    block_number: int,
    font: str | None = None,
    size: float | None = None,
    direction: tuple[float, float] = (1.0, 0.0),
    bbox: tuple[float, float, float, float] | None = None,
) -> PdfBlock:
    block_bbox = bbox or (72.0, y, 540.0, y + 18.0)
    lines = ()
    if font is not None and size is not None:
        span = PdfSpan(
            bbox=block_bbox,
            text=text,
            font=font,
            size=size,
            flags=0,
        )
        lines = (PdfLine(bbox=span.bbox, spans=(span,), direction=direction),)
    return PdfBlock(
        page_number=page,
        bbox=block_bbox,
        text=text,
        block_number=block_number,
        lines=lines,
    )


def _layout(*, page_count: int = 388, include_rotated_annex_caption: bool = False) -> PdfLayoutDocument:
    blocks = {
        9: (
            _block(
                "1 SYNTHETIC PURPOSE MUST_NOT_LEAK",
                page=9,
                y=80.0,
                block_number=1,
                font="Helvetica-Bold",
                size=11.0,
            ),
            _block(
                "1.1 SYNTHETIC SCOPE MUST_NOT_LEAK",
                page=9,
                y=110.0,
                block_number=2,
                font="Helvetica-Bold",
                size=10.0,
            ),
            _block(
                "SYNTHETIC BODY MUST_NOT_LEAK",
                page=9,
                y=140.0,
                block_number=3,
            ),
        ),
        191: (
            _block(
                "NORMATIVE APPENDIX A SYNTHETIC MUST_NOT_LEAK",
                page=191,
                y=80.0,
                block_number=1,
                font="Helvetica-Bold",
                size=11.0,
            ),
            _block(
                "Figure Annex1-2 SYNTHETIC LISTING MUST_NOT_LEAK",
                page=191,
                y=110.0,
                block_number=2,
                font="Helvetica",
                size=8.5,
            ),
            _block(
                "Figure Annex1-2 SYNTHETIC CAPTION MUST_NOT_LEAK",
                page=191,
                y=140.0,
                block_number=3,
                font="Helvetica-Bold",
                size=8.5,
            ),
        ),
    }
    if include_rotated_annex_caption:
        blocks[334] = (
            _block(
                "Figure Annex1-1 SYNTHETIC ROTATED CAPTION MUST_NOT_LEAK",
                page=334,
                y=336.0,
                block_number=1,
                font="Helvetica-Bold",
                size=8.5,
                direction=(0.0, -1.0),
                bbox=(533.85, 336.55, 542.35, 744.17),
            ),
        )
    return PdfLayoutDocument(
        file_name="synthetic-ashrae901.pdf",
        pages=tuple(
            PdfPage(
                page_number=page,
                width=612.0,
                height=792.0,
                blocks=blocks.get(page, ()),
            )
            for page in range(1, page_count + 1)
        ),
        outline=(),
    )


class Ashrae901MaterializationTests(unittest.TestCase):
    def test_receipt_proves_generic_validation_without_serializing_private_ast(self) -> None:
        receipt = materialize_ashrae901_2016_document_receipt(
            _layout(),
            source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
            source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
        )

        self.assertEqual(receipt["receipt_version"], "0.1.0")
        self.assertEqual(receipt["status"], "validated")
        self.assertEqual(receipt["source_block_count"], 6)
        self.assertEqual(receipt["node_count"], 7)
        self.assertEqual(
            receipt["node_type_counts"],
            {
                "document": 1,
                "figure": 1,
                "paragraph": 2,
                "section": 2,
                "subsection": 1,
            },
        )
        self.assertEqual(receipt["diagnostic_counts"], {})
        self.assertNotIn("source_text", receipt)
        self.assertNotIn("root", receipt)
        self.assertNotIn("MUST_NOT_LEAK", json.dumps(receipt, sort_keys=True))

    def test_receipt_includes_bounded_rotated_annex_caption_and_stays_valid(self) -> None:
        receipt = materialize_ashrae901_2016_document_receipt(
            _layout(include_rotated_annex_caption=True),
            source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
            source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
        )

        self.assertEqual(receipt["status"], "validated")
        self.assertEqual(receipt["source_block_count"], 7)
        self.assertEqual(receipt["node_count"], 8)
        self.assertEqual(receipt["node_type_counts"]["figure"], 2)
        self.assertEqual(receipt["diagnostic_counts"], {})
        self.assertNotIn("MUST_NOT_LEAK", json.dumps(receipt, sort_keys=True))

    def test_receipt_fails_closed_on_wrong_exact_source_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact retained ASHRAE 90.1-2016 SHA-256"):
            materialize_ashrae901_2016_document_receipt(
                _layout(),
                source_sha256="0" * 64,
                source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
            )
        with self.assertRaisesRegex(ValueError, "exact retained ASHRAE 90.1-2016 size"):
            materialize_ashrae901_2016_document_receipt(
                _layout(),
                source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
                source_size=1,
            )
        with self.assertRaisesRegex(ValueError, "388 PDF pages"):
            materialize_ashrae901_2016_document_receipt(
                _layout(page_count=387),
                source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
                source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
            )


if __name__ == "__main__":
    unittest.main()
