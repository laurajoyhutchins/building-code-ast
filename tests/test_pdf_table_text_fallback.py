from __future__ import annotations

import unittest
from unittest.mock import Mock, call

from building_code_ast.ingest.pdf_layout import _table_region_bboxes


class PdfTableTextFallbackTests(unittest.TestCase):
    def test_announced_table_uses_text_fallback_when_line_geometry_is_empty(self) -> None:
        page = Mock()
        table = Mock(bbox=(45.5, 33.2, 551.9, 772.6))
        page.find_tables.side_effect = (Mock(tables=()), Mock(tables=(table,)))

        self.assertEqual(
            _table_region_bboxes(page, ("TABLE C-2 Concentration of Interest",)),
            ((45.5, 33.2, 551.9, 772.6),),
        )
        self.assertEqual(page.find_tables.call_args_list, [call(), call(strategy="text")])

    def test_existing_line_candidate_does_not_run_text_fallback(self) -> None:
        page = Mock()
        table = Mock(bbox=(10.0, 20.0, 30.0, 40.0))
        page.find_tables.return_value = Mock(tables=(table,))

        self.assertEqual(
            _table_region_bboxes(page, ("TABLE C-1 Example",)),
            ((10.0, 20.0, 30.0, 40.0),),
        )
        page.find_tables.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
