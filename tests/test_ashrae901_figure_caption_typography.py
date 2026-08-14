from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.ingest.ashrae901_2016 import (
    Ashrae901Observation,
    parse_ashrae901_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan


def _observation(
    text: str,
    *,
    page: int,
    y: float,
    font: str | None = None,
    size: float | None = None,
    hint: str | None = None,
    locator: str | None = None,
) -> Ashrae901Observation:
    lines = ()
    if font is not None and size is not None:
        span = PdfSpan(
            bbox=(72.0, y, 540.0, y + size),
            text=text,
            font=font,
            size=size,
            flags=0,
        )
        lines = (PdfLine(bbox=span.bbox, spans=(span,)),)
    return Ashrae901Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(72.0, y, 540.0, y + 18.0),
            text=text,
            block_number=1,
            lines=lines,
        ),
        structure_hint=hint,
        native_locator=locator,
    )


class Ashrae901FigureCaptionTypographyTests(unittest.TestCase):
    def test_regular_font_annex_listing_does_not_collide_with_bold_caption(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "NORMATIVE APPENDIX A SYNTHETIC",
                    page=191,
                    y=80.0,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation(
                    "Figure Annex1-2 SYNTHETIC LISTING",
                    page=192,
                    y=110.0,
                    font="Helvetica",
                    size=8.5,
                ),
                _observation(
                    "Figure Annex1-2 SYNTHETIC CAPTION",
                    page=193,
                    y=140.0,
                    font="Helvetica-Bold",
                    size=8.5,
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertEqual(
            [child.node_type for child in appendix.children],
            [DocumentNodeType.PARAGRAPH, DocumentNodeType.FIGURE],
        )
        self.assertEqual(appendix.children[1].locator, "figure:Annex1-2")

    def test_automatic_figure_without_visual_font_evidence_remains_prose(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "Figure 6-1 SYNTHETIC TEXT ONLY",
                    page=100,
                    y=100.0,
                ),
            )
        )

        self.assertEqual(ast.root.children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_explicit_figure_hint_remains_authoritative_without_typography(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "SYNTHETIC GRAPHICAL CAPTION",
                    page=100,
                    y=100.0,
                    hint="figure",
                    locator="6-1",
                ),
            )
        )

        self.assertEqual(ast.root.children[0].node_type, DocumentNodeType.FIGURE)
        self.assertEqual(ast.root.children[0].locator, "figure:6-1")


if __name__ == "__main__":
    unittest.main()
