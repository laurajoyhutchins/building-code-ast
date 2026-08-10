from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.ingest.ashrae621_2016 import (
    Ashrae621Observation,
    parse_ashrae621_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock


def _observation(text: str, *, page: int, block_number: int, y: float) -> Ashrae621Observation:
    return Ashrae621Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(312.0, y, 500.0, y + 24.0),
            text=text,
            block_number=block_number,
        ),
        printed_page=str(page - 2),
    )


class Ashrae621AppendixHeadingDisambiguationTests(unittest.TestCase):
    def test_displayed_math_starting_with_appendix_locator_is_not_a_duplicate_heading(self) -> None:
        ast = parse_ashrae621_2016_observations(
            (
                _observation(
                    "INFORMATIVE APPENDIX C SYNTHETIC GUIDELINES",
                    page=31,
                    block_number=1,
                    y=80,
                ),
                _observation(
                    "C1. SYNTHETIC GUIDELINE VALUES",
                    page=31,
                    block_number=2,
                    y=120,
                ),
                _observation(
                    "C1 T 1 ----- C2 T 2 ----- Cn T n ----- + + +",
                    page=31,
                    block_number=3,
                    y=160,
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertEqual(
            [child.locator for child in appendix.children],
            ["section:C1", appendix.children[1].locator],
        )
        self.assertEqual(appendix.children[0].node_type, DocumentNodeType.SUBSECTION)
        self.assertEqual(appendix.children[1].node_type, DocumentNodeType.PARAGRAPH)
        self.assertTrue(appendix.children[1].locator.startswith("paragraph:"))

    def test_numbered_reference_entry_is_not_promoted_to_top_level_appendix_section(self) -> None:
        ast = parse_ashrae621_2016_observations(
            (
                _observation(
                    "INFORMATIVE APPENDIX J SYNTHETIC REFERENCES",
                    page=53,
                    block_number=1,
                    y=80,
                ),
                _observation(
                    "J1. Synthetic Reference Title, 2020. Synthetic Publisher.",
                    page=53,
                    block_number=2,
                    y=120,
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertEqual(len(appendix.children), 1)
        self.assertEqual(appendix.children[0].node_type, DocumentNodeType.PARAGRAPH)
        self.assertTrue(appendix.children[0].locator.startswith("paragraph:"))


if __name__ == "__main__":
    unittest.main()
