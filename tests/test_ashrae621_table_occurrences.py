from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.ingest.ashrae621_2016 import (
    Ashrae621Observation,
    parse_ashrae621_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock


def _table(text: str, *, page: int, block_number: int, y: float) -> Ashrae621Observation:
    return Ashrae621Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(72.0, y, 540.0, y + 18.0),
            text=text,
            block_number=block_number,
        ),
        printed_page=str(page - 2),
    )


class Ashrae621TableOccurrenceTests(unittest.TestCase):
    def test_adjacent_repeated_table_locator_preserves_primary_and_page_occurrences(self) -> None:
        ast = parse_ashrae621_2016_observations(
            (
                _table("Table 6.2.2.1 SYNTHETIC TABLE", page=15, block_number=1, y=100),
                _table("Table 6.2.2.1 SYNTHETIC TABLE (Continued)", page=16, block_number=1, y=100),
                _table("Table 6.2.2.1 SYNTHETIC TABLE (Continued)", page=17, block_number=1, y=100),
            )
        )

        self.assertEqual(
            [node.node_type for node in ast.root.children],
            [DocumentNodeType.TABLE, DocumentNodeType.TABLE_HEADING, DocumentNodeType.TABLE_HEADING],
        )
        self.assertEqual(ast.root.children[0].locator, "table:6.2.2.1")
        self.assertEqual(
            [node.locator for node in ast.root.children[1:]],
            [
                "table-heading:6.2.2.1:pdf-page-16:occurrence-1",
                "table-heading:6.2.2.1:pdf-page-17:occurrence-1",
            ],
        )
        self.assertEqual(
            dict(ast.root.children[0].attributes)["occurrence_pattern"],
            "adjacent_pages",
        )
        self.assertEqual(
            {diagnostic.code for diagnostic in ast.diagnostics},
            {"ashrae621-repeated-table-structure-deferred"},
        )

    def test_same_page_duplicate_table_observation_is_preserved_without_locator_collision(self) -> None:
        ast = parse_ashrae621_2016_observations(
            (
                _table("Table C-3 SYNTHETIC TABLE", page=40, block_number=1, y=100),
                _table("Table C-3 SYNTHETIC TABLE FRAGMENT", page=40, block_number=2, y=130),
                _table("Table C-3 SYNTHETIC TABLE (Continued)", page=41, block_number=1, y=100),
            )
        )

        self.assertEqual(len(ast.root.children), 3)
        self.assertEqual(ast.root.children[0].locator, "table:C-3")
        self.assertEqual(ast.root.children[1].locator, "table-heading:C-3:pdf-page-40:occurrence-2")
        self.assertEqual(ast.root.children[2].locator, "table-heading:C-3:pdf-page-41:occurrence-1")
        self.assertEqual(
            dict(ast.root.children[0].attributes)["occurrence_pattern"],
            "same_page_duplicate",
        )
        self.assertEqual(
            dict(ast.root.children[1].attributes)["native_locator"],
            "C-3",
        )


if __name__ == "__main__":
    unittest.main()
