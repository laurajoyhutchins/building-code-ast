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
                font="Synthetic-Bold" if bold else "Synthetic-Regular",
                size=9.0,
                flags=16 if bold else 0,
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


class Ashrae621CompoundBlockTests(unittest.TestCase):
    def test_multiple_bold_appendix_headings_in_one_pdf_block_are_recovered(self) -> None:
        appendix = Ashrae621Observation(
            block=PdfBlock(
                page_number=29,
                bbox=(72.0, 70.0, 500.0, 88.0),
                text="NORMATIVE APPENDIX B SYNTHETIC MATERIAL",
                block_number=1,
            ),
            printed_page="27",
        )
        compound = _block(
            (
                _line("B1.1. SYNTHETIC FIRST HEADING", y=120.0, bold=True),
                _line("Synthetic first body.", y=136.0),
                _line("B1.2. SYNTHETIC SECOND HEADING", y=160.0, bold=True),
                _line("Synthetic second body.", y=176.0),
            ),
            page=29,
            number=5,
        )

        ast = parse_ashrae621_2016_observations(
            (appendix, Ashrae621Observation(block=compound, printed_page="27"))
        )

        locators = _locators(ast.root)
        self.assertIn("section:B1.1", locators)
        self.assertIn("section:B1.2", locators)
        self.assertEqual(locators.count("section:B1.1"), 1)
        self.assertEqual(locators.count("section:B1.2"), 1)
        self.assertEqual(
            normalize_block_text(ast.source_text),
            normalize_block_text(f"{appendix.block.text}\n{compound.text}"),
        )

    def test_prefix_prose_before_first_heading_is_preserved_losslessly(self) -> None:
        appendix = Ashrae621Observation(
            block=PdfBlock(
                page_number=47,
                bbox=(72.0, 70.0, 500.0, 88.0),
                text="INFORMATIVE APPENDIX G SYNTHETIC MATERIAL",
                block_number=1,
            ),
            printed_page="45",
        )
        compound = _block(
            (
                _line("Synthetic continuation prose before the first heading.", y=110.0),
                _line("G1.2.4. SYNTHETIC FOURTH HEADING", y=130.0, bold=True),
                _line("Synthetic fourth body.", y=146.0),
                _line("G1.2.5. SYNTHETIC FIFTH HEADING", y=170.0, bold=True),
                _line("Synthetic fifth body.", y=186.0),
            ),
            page=47,
            number=6,
        )

        ast = parse_ashrae621_2016_observations(
            (appendix, Ashrae621Observation(block=compound, printed_page="45"))
        )

        appendix_node = ast.root.children[0]
        self.assertEqual(appendix_node.children[0].node_type, DocumentNodeType.PARAGRAPH)
        locators = _locators(appendix_node)
        self.assertIn("section:G1.2.4", locators)
        self.assertIn("section:G1.2.5", locators)
        self.assertEqual(
            normalize_block_text(ast.source_text),
            normalize_block_text(f"{appendix.block.text}\n{compound.text}"),
        )


if __name__ == "__main__":
    unittest.main()
