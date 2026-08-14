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
    direction: tuple[float, float] = (1.0, 0.0),
    block_bbox: tuple[float, float, float, float] | None = None,
) -> Ashrae901Observation:
    bbox = block_bbox or (72.0, y, 540.0, y + 18.0)
    lines = ()
    if font is not None and size is not None:
        span = PdfSpan(
            bbox=bbox,
            text=text,
            font=font,
            size=size,
            flags=0,
        )
        lines = (PdfLine(bbox=span.bbox, spans=(span,), direction=direction),)
    return Ashrae901Observation(
        block=PdfBlock(
            page_number=page,
            bbox=bbox,
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

    def test_rotated_annex_caption_outside_body_content_is_recovered(self) -> None:
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
                    "Figure Annex1-1 SYNTHETIC ROTATED CAPTION",
                    page=334,
                    y=336.0,
                    font="Helvetica-Bold",
                    size=8.5,
                    direction=(0.0, -1.0),
                    block_bbox=(533.85, 336.55, 542.35, 744.17),
                ),
            )
        )

        appendix = ast.root.children[0]
        figures = [
            child for child in appendix.children if child.node_type is DocumentNodeType.FIGURE
        ]
        self.assertEqual([figure.locator for figure in figures], ["figure:Annex1-1"])

    def test_horizontal_annex_caption_outside_body_content_stays_unpromoted(self) -> None:
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
                    "Figure Annex1-1 SYNTHETIC HORIZONTAL FURNITURE",
                    page=334,
                    y=736.0,
                    font="Helvetica-Bold",
                    size=8.5,
                    direction=(1.0, 0.0),
                    block_bbox=(72.0, 736.0, 300.0, 744.5),
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertFalse(
            any(child.node_type is DocumentNodeType.FIGURE for child in appendix.children)
        )

    def test_rotated_non_annex_figure_outside_body_content_stays_unpromoted(self) -> None:
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
                    "Figure 6-1 SYNTHETIC ROTATED FURNITURE",
                    page=334,
                    y=736.0,
                    font="Helvetica-Bold",
                    size=8.5,
                    direction=(0.0, -1.0),
                    block_bbox=(533.0, 336.0, 542.0, 744.5),
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertFalse(
            any(child.node_type is DocumentNodeType.FIGURE for child in appendix.children)
        )

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
