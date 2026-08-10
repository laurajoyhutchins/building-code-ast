from __future__ import annotations

import json
import unittest

from building_code_ast.ashrae901_2016_corpus import (
    ASHRAE_90_1_2016_SOURCE_SHA256,
    ASHRAE_90_1_2016_SOURCE_SIZE,
    measure_ashrae901_2016_corpus,
)
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfLine,
    PdfOutlineItem,
    PdfPage,
    PdfSpan,
)


def _block(
    text: str,
    *,
    page: int,
    block_number: int = 1,
    font: str | None = None,
    size: float | None = None,
) -> PdfBlock:
    lines = ()
    if font is not None and size is not None:
        span = PdfSpan(
            bbox=(72.0, 100.0, 540.0, 100.0 + size),
            text=text,
            font=font,
            size=size,
            flags=0,
        )
        lines = (PdfLine(bbox=span.bbox, spans=(span,)),)
    return PdfBlock(
        page_number=page,
        bbox=(72.0, 100.0, 540.0, 118.0),
        text=text,
        block_number=block_number,
        lines=lines,
    )


def _layout(*, page_count: int = 388) -> PdfLayoutDocument:
    blocks = {
        7: (
            _block(
                "1. SYNTHETIC LIST ITEM MUST_NOT_LEAK",
                page=7,
                font="Helvetica",
                size=8.5,
            ),
        ),
        8: (
            _block(
                "1. ANOTHER SYNTHETIC LIST ITEM MUST_NOT_LEAK",
                page=8,
                font="Helvetica",
                size=8.5,
            ),
        ),
        9: (
            _block(
                "1 SYNTHETIC PURPOSE MUST_NOT_LEAK",
                page=9,
                font="Helvetica-Bold",
                size=11.0,
            ),
        ),
        10: (
            _block(
                "1.1 SYNTHETIC SCOPE MUST_NOT_LEAK",
                page=10,
                font="Helvetica-Bold",
                size=10.0,
            ),
        ),
        191: (
            _block(
                "NORMATIVE APPENDIX A SYNTHETIC MATERIAL MUST_NOT_LEAK",
                page=191,
                font="Helvetica-Bold",
                size=11.0,
            ),
        ),
    }
    pages = tuple(
        PdfPage(
            page_number=page,
            width=612.0,
            height=792.0,
            blocks=blocks.get(page, ()),
        )
        for page in range(1, page_count + 1)
    )
    outline = (
        PdfOutlineItem(level=2, title="1. Synthetic Purpose MUST_NOT_LEAK", page_number=9),
        PdfOutlineItem(level=3, title="1.1 Synthetic Scope MUST_NOT_LEAK", page_number=10),
        PdfOutlineItem(level=3, title="1.2 Synthetic Missing MUST_NOT_LEAK", page_number=11),
        PdfOutlineItem(level=2, title="Normative Appendix A Synthetic", page_number=191),
        PdfOutlineItem(level=3, title="A1 Synthetic Appendix Locator MUST_NOT_LEAK", page_number=192),
    )
    return PdfLayoutDocument(
        file_name="synthetic-ashrae901.pdf",
        pages=pages,
        outline=outline,
    )


class Ashrae901CorpusMeasurementTests(unittest.TestCase):
    def test_measurement_tracks_typography_gated_locator_behavior_without_source_expression(self) -> None:
        measurement = measure_ashrae901_2016_corpus(
            _layout(),
            source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
            source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
        )

        self.assertEqual(measurement["source_block_count"], 5)
        self.assertEqual(
            measurement["classifier_counts"],
            {
                "appendix": 1,
                "equation": 0,
                "figure": 0,
                "paragraph": 2,
                "section": 1,
                "subsection": 1,
                "table": 0,
            },
        )
        self.assertEqual(
            measurement["numeric_hierarchy"],
            {
                "outline_unique_locators": 3,
                "candidate_occurrences": 2,
                "candidate_unique_locators": 2,
                "duplicate_candidate_occurrences": 0,
                "matched_unique_locators": 2,
                "missing_outline_locators": 1,
                "unexpected_candidate_locators": 0,
                "exact_outline_page_matches": 2,
                "near_outline_page_matches": 0,
                "far_only_outline_matches": 0,
                "first_duplicate": None,
            },
        )
        self.assertEqual(
            measurement["appendix_hierarchy"],
            {
                "outline_top_level_appendices": 1,
                "recognized_top_level_appendices": 1,
                "outline_native_sublocators": 1,
                "current_appendix_sublocator_candidates": 0,
            },
        )
        self.assertEqual(
            measurement["whole_document_status"],
            {
                "validatable": True,
                "blocker": None,
                "locator": None,
            },
        )
        self.assertNotIn("MUST_NOT_LEAK", json.dumps(measurement, sort_keys=True))

    def test_measurement_fails_closed_on_wrong_exact_source_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact retained ASHRAE 90.1-2016 SHA-256"):
            measure_ashrae901_2016_corpus(
                _layout(),
                source_sha256="0" * 64,
                source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
            )
        with self.assertRaisesRegex(ValueError, "exact retained ASHRAE 90.1-2016 size"):
            measure_ashrae901_2016_corpus(
                _layout(),
                source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
                source_size=1,
            )
        with self.assertRaisesRegex(ValueError, "388 PDF pages"):
            measure_ashrae901_2016_corpus(
                _layout(page_count=387),
                source_sha256=ASHRAE_90_1_2016_SOURCE_SHA256,
                source_size=ASHRAE_90_1_2016_SOURCE_SIZE,
            )


if __name__ == "__main__":
    unittest.main()
