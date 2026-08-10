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


class Ashrae621SingleEmbeddedHeadingTests(unittest.TestCase):
    def test_single_bold_appendix_heading_after_prefix_prose_is_recovered_losslessly(self) -> None:
        appendix = Ashrae621Observation(
            block=PdfBlock(
                page_number=27,
                bbox=(72.0, 40.0, 500.0, 58.0),
                text="NORMATIVE APPENDIX A SYNTHETIC MATERIAL",
                block_number=0,
            ),
            printed_page="25",
        )
        embedded = _block(
            (
                _line("Synthetic prefix line one.", y=60.0),
                _line("Synthetic prefix line two.", y=74.0),
                _line("A1.2.2. Synthetic Embedded Heading", y=90.0, bold=True),
                _line("Synthetic body after the heading.", y=106.0),
            ),
            page=27,
            number=1,
        )

        ast = parse_ashrae621_2016_observations(
            (appendix, Ashrae621Observation(block=embedded, printed_page="25"))
        )

        locators = _locators(ast.root)
        self.assertIn("section:A1.2.2", locators)
        appendix_node = ast.root.children[0]
        self.assertEqual(appendix_node.children[0].node_type, DocumentNodeType.PARAGRAPH)
        self.assertEqual(
            normalize_block_text(ast.source_text),
            normalize_block_text(f"{appendix.block.text}\n{embedded.text}"),
        )

    def test_nonbold_locator_like_line_after_prefix_is_not_promoted(self) -> None:
        appendix = Ashrae621Observation(
            block=PdfBlock(
                page_number=31,
                bbox=(72.0, 40.0, 500.0, 58.0),
                text="INFORMATIVE APPENDIX C SYNTHETIC MATERIAL",
                block_number=0,
            ),
            printed_page="29",
        )
        ordinary = _block(
            (
                _line("Synthetic prefix prose.", y=60.0),
                _line("C1.2.3. Synthetic locator-like ordinary text", y=76.0, bold=False),
            ),
            page=31,
            number=1,
        )

        ast = parse_ashrae621_2016_observations(
            (appendix, Ashrae621Observation(block=ordinary, printed_page="29"))
        )

        self.assertNotIn("section:C1.2.3", _locators(ast.root))


if __name__ == "__main__":
    unittest.main()
