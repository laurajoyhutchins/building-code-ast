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
    font: str | None,
    size: float | None,
    y: float = 100.0,
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
        lines = (
            PdfLine(
                bbox=span.bbox,
                spans=(span,),
            ),
        )
    return Ashrae901Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(72.0, y, 540.0, y + 18.0),
            text=text,
            block_number=1,
            lines=lines,
        )
    )


class Ashrae901NumericHeadingTypographyTests(unittest.TestCase):
    def test_top_level_heading_uses_observed_bold_11_point_typography(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "12 SYNTHETIC REFERENCES",
                    page=187,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
            )
        )

        self.assertEqual(ast.root.children[0].locator, "section:12")
        self.assertEqual(ast.root.children[0].label, "SYNTHETIC REFERENCES")

    def test_regular_numbered_prose_is_not_promoted_to_top_level_section(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "1. SYNTHETIC LIST ITEM",
                    page=7,
                    font="Helvetica",
                    size=8.5,
                ),
            )
        )

        self.assertEqual(ast.root.children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_subsection_requires_observed_bold_10_point_typography(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "6.1 SYNTHETIC TRUE HEADING",
                    page=75,
                    font="Helvetica-Bold",
                    size=10.0,
                ),
                _observation(
                    "6.2 SYNTHETIC NUMBERED PROSE",
                    page=75,
                    font="Helvetica",
                    size=8.5,
                    y=140.0,
                ),
            )
        )

        section = ast.root.children[0]
        self.assertEqual(section.locator, "section:6.1")
        self.assertEqual(section.children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_locator_only_bold_subsection_is_preserved_without_invented_label(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "6.5.5.2.1",
                    page=105,
                    font="Helvetica-Bold",
                    size=10.0,
                ),
            )
        )

        heading = ast.root.children[0]
        self.assertEqual(heading.locator, "section:6.5.5.2.1")
        self.assertIsNone(heading.label)

    def test_numeric_material_after_appendix_start_is_not_body_hierarchy(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "NORMATIVE APPENDIX A SYNTHETIC",
                    page=191,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation(
                    "4. SYNTHETIC REPRODUCED MATERIAL",
                    page=192,
                    font="Helvetica-Bold",
                    size=11.0,
                    y=140.0,
                ),
            )
        )

        self.assertEqual(len(ast.root.children), 1)
        appendix = ast.root.children[0]
        self.assertEqual(appendix.locator, "appendix:A")
        self.assertEqual(appendix.children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_numeric_text_without_visual_font_evidence_fails_conservatively(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "6. SYNTHETIC TEXT ONLY",
                    page=75,
                    font=None,
                    size=None,
                ),
            )
        )

        self.assertEqual(ast.root.children[0].node_type, DocumentNodeType.PARAGRAPH)


if __name__ == "__main__":
    unittest.main()
