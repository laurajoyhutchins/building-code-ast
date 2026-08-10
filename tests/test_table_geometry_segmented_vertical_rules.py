from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    RuleSegment,
    SourceFragment,
    VisualLine,
    visual_line_id,
)
from building_code_ast.ingest.table_geometry import detect_ruled_tables


def _fragment(x0: float, y0: float, x1: float, text: str, block: int) -> SourceFragment:
    return SourceFragment(
        page_number=1,
        bbox=(x0, y0, x1, y0 + 10.0),
        block_number=block,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


def _line(fragment: SourceFragment) -> VisualLine:
    return VisualLine(
        line_id=visual_line_id(1, (fragment,)),
        page_number=1,
        bbox=fragment.bbox,
        text=fragment.raw_text,
        fragments=(fragment,),
        font_size=fragment.font_size,
        font_name=fragment.font_name,
    )


def _page(vertical_rules: tuple[RuleSegment, ...]) -> CleanedPage:
    fragments = (
        _fragment(20.0, 20.0, 50.0, "A", 1),
        _fragment(120.0, 20.0, 150.0, "B", 2),
        _fragment(20.0, 70.0, 50.0, "C", 3),
        _fragment(120.0, 70.0, 150.0, "D", 4),
        _fragment(20.0, 120.0, 50.0, "E", 5),
        _fragment(120.0, 120.0, 150.0, "F", 6),
    )
    horizontal_rules = tuple(
        RuleSegment(1, 10.0, y, 210.0, y)
        for y in (10.0, 60.0, 110.0, 160.0)
    )
    return CleanedPage(
        page_number=1,
        width=220.0,
        height=180.0,
        retained=tuple(_line(fragment) for fragment in fragments),
        removed=(),
        rules=horizontal_rules + vertical_rules,
    )


class TableGeometrySegmentedVerticalRuleTests(unittest.TestCase):
    def test_repeated_rule_aligned_vertical_segments_establish_grid_columns(self) -> None:
        vertical_rules = tuple(
            RuleSegment(1, x, top, x, bottom)
            for x in (10.0, 110.0, 210.0)
            for top, bottom in ((10.0, 60.0), (110.0, 160.0))
        )

        tables = detect_ruled_tables(_page(vertical_rules))

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].normalized_text, "A\tB\nC\tD\nE\tF")
        self.assertIn("vector_rule_grid", tables[0].evidence)

    def test_unaligned_short_vertical_segments_do_not_establish_grid_columns(self) -> None:
        vertical_rules = tuple(
            RuleSegment(1, x, top, x, bottom)
            for x in (10.0, 110.0, 210.0)
            for top, bottom in ((20.0, 40.0), (80.0, 100.0))
        )

        self.assertEqual(detect_ruled_tables(_page(vertical_rules)), ())


if __name__ == "__main__":
    unittest.main()
