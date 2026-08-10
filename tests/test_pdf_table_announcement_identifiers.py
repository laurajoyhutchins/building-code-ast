from __future__ import annotations

import unittest
from unittest.mock import Mock

from building_code_ast.ingest.pdf_layout import _table_region_bboxes


class PdfTableAnnouncementIdentifierTests(unittest.TestCase):
    def test_alphanumeric_table_locator_enables_bounded_geometry(self) -> None:
        page = Mock()
        table = Mock(bbox=(10.0, 20.0, 30.0, 40.0))
        page.find_tables.return_value = Mock(tables=(table,))

        self.assertEqual(
            _table_region_bboxes(page, ("TABLE C-3 Concentrations of Interest",)),
            ((10.0, 20.0, 30.0, 40.0),),
        )
        page.find_tables.assert_called_once_with()

    def test_unannounced_prose_does_not_enable_geometry(self) -> None:
        page = Mock()

        self.assertEqual(
            _table_region_bboxes(page, ("See Table C-3 for additional information.",)),
            (),
        )
        page.find_tables.assert_not_called()


if __name__ == "__main__":
    unittest.main()
