from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    RuleSegment,
    SourceFragment,
    VisualLine,
    visual_line_id,
)
from building_code_ast.ingest.table_geometry import detect_table_rows


def _fragment(x0: float, x1: float, text: str) -> SourceFragment:
    return SourceFragment(
        page_number=1,
        bbox=(x0, 100.0, x1, 110.0),
        block_number=1,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


class TableGeometryRuleRegionTests(unittest.TestCase):
    def test_rule_bounded_table_row_can_cross_two_column_gutter(self) -> None:
        parts = (
            _fragment(50.0, 170.0, "Table row label"),
            _fragment(390.0, 450.0, "Value"),
        )
        line = VisualLine(
            line_id=visual_line_id(1, parts),
            page_number=1,
            bbox=(50.0, 100.0, 450.0, 110.0),
            text="Table row label Value",
            fragments=parts,
            font_size=10.0,
            font_name="SyntheticBody",
        )
        rules = (
            RuleSegment(1, 40.0, 80.0, 560.0, 80.0),
            RuleSegment(1, 40.0, 90.0, 560.0, 90.0),
            RuleSegment(1, 40.0, 130.0, 560.0, 130.0),
        )
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(line,),
            removed=(),
            rules=rules,
        )
        profile = PageOrderProfile(
            page_number=1,
            mode=ReadingOrderMode.TWO_COLUMN,
            split_x=300.0,
            confidence=0.9,
            evidence=("two_column",),
        )

        rows = detect_table_rows(page, profile)

        self.assertEqual(len(rows), 1)
        self.assertEqual([cell.text for cell in rows[0].cells], ["Table row label", "Value"])

    def test_unruled_page_columns_still_do_not_become_table_cells(self) -> None:
        parts = (
            _fragment(50.0, 170.0, "Left paragraph"),
            _fragment(390.0, 480.0, "Right paragraph"),
        )
        line = VisualLine(
            line_id=visual_line_id(1, parts),
            page_number=1,
            bbox=(50.0, 100.0, 480.0, 110.0),
            text="Left paragraph Right paragraph",
            fragments=parts,
            font_size=10.0,
            font_name="SyntheticBody",
        )
        page = CleanedPage(1, 600.0, 300.0, (line,), ())
        profile = PageOrderProfile(1, ReadingOrderMode.TWO_COLUMN, 300.0, 0.9, ("two_column",))

        self.assertEqual(detect_table_rows(page, profile), ())


if __name__ == "__main__":
    unittest.main()
