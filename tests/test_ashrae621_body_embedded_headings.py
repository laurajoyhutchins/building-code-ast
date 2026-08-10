from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.ingest.ashrae621_2016 import (
    Ashrae621Observation,
    parse_ashrae621_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan, normalize_block_text


def _line(text: str, *, y: float, bold: bool = False) -> PdfLine:
    return PdfLine(
        bbox=(72.0, y, 500.0, y + 12.0),
        spans=(
            PdfSpan(
                bbox=(72.0, y, 500.0, y + 12.0),
                text=text,
                font="TimesNewRomanPS-BoldMT" if bold else "TimesNewRomanPSMT",
                size=10.0,
                flags=20 if bold else 4,
            ),
        ),
    )


def _block(lines: tuple[PdfLine, ...], *, page: int, number: int) -> PdfBlock:
    return PdfBlock(
        page_number=page,
        bbox=(
            min(line.bbox[0] for line in lines),
            min(line.bbox[1] for line in lines),
            max(line.bbox[2] for line in lines),
            max(line.bbox[3] for line in lines),
        ),
        text="\n".join(line.text for line in lines),
        block_number=number,
        lines=lines,
    )


def _locators(node) -> list[str]:
    result = [node.locator]
    for child in node.children:
        result.extend(_locators(child))
    return result


class Ashrae621BodyEmbeddedHeadingTests(unittest.TestCase):
    def test_multiple_bold_body_subsections_inside_one_pdf_block_are_recovered_losslessly(self) -> None:
        section = Ashrae621Observation(
            block=PdfBlock(
                page_number=9,
                bbox=(72.0, 40.0, 500.0, 58.0),
                text="5. SYNTHETIC BODY SECTION",
                block_number=0,
            ),
            printed_page="7",
        )
        compound = _block(
            (
                _line("Synthetic prefix prose.", y=60.0),
                _line("5.9.1 Synthetic First Heading", y=76.0, bold=True),
                _line("Synthetic body under first heading.", y=92.0),
                _line("5.9.2 Synthetic Second Heading", y=108.0, bold=True),
                _line("Synthetic body under second heading.", y=124.0),
            ),
            page=9,
            number=1,
        )

        ast = parse_ashrae621_2016_observations(
            (section, Ashrae621Observation(block=compound, printed_page="7"))
        )

        locators = _locators(ast.root)
        self.assertIn("section:5.9.1", locators)
        self.assertIn("section:5.9.2", locators)
        self.assertEqual(ast.root.children[0].children[0].node_type, DocumentNodeType.PARAGRAPH)
        self.assertEqual(
            normalize_block_text(ast.source_text),
            normalize_block_text(f"{section.block.text}\n{compound.text}"),
        )

    def test_single_bold_body_subsection_after_prefix_prose_is_recovered_losslessly(self) -> None:
        section = Ashrae621Observation(
            block=PdfBlock(
                page_number=11,
                bbox=(72.0, 40.0, 500.0, 58.0),
                text="5. SYNTHETIC BODY SECTION",
                block_number=0,
            ),
            printed_page="9",
        )
        embedded = _block(
            (
                _line("Synthetic prefix line one.", y=60.0),
                _line("Synthetic prefix line two.", y=74.0),
                _line("5.14.2 Synthetic Embedded Heading", y=90.0, bold=True),
                _line("Synthetic body after the heading.", y=106.0),
            ),
            page=11,
            number=1,
        )

        ast = parse_ashrae621_2016_observations(
            (section, Ashrae621Observation(block=embedded, printed_page="9"))
        )

        self.assertIn("section:5.14.2", _locators(ast.root))
        self.assertEqual(
            normalize_block_text(ast.source_text),
            normalize_block_text(f"{section.block.text}\n{embedded.text}"),
        )

    def test_nonbold_numeric_locator_like_line_after_prefix_is_not_promoted(self) -> None:
        section = Ashrae621Observation(
            block=PdfBlock(
                page_number=13,
                bbox=(72.0, 40.0, 500.0, 58.0),
                text="6. SYNTHETIC BODY SECTION",
                block_number=0,
            ),
            printed_page="11",
        )
        ordinary = _block(
            (
                _line("Synthetic prefix prose.", y=60.0),
                _line("6.4.3 Synthetic locator-like ordinary text", y=76.0, bold=False),
            ),
            page=13,
            number=1,
        )

        ast = parse_ashrae621_2016_observations(
            (section, Ashrae621Observation(block=ordinary, printed_page="11"))
        )

        self.assertNotIn("section:6.4.3", _locators(ast.root))


if __name__ == "__main__":
    unittest.main()
