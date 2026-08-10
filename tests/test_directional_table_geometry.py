from __future__ import annotations

import unittest

from building_code_ast.ingest.directional_table_geometry import detect_table_rows_in_writing_frame
from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    RuleSegment,
    SourceFragment,
    VisualLine,
    visual_line_id,
)


def _fragment(y0: float, y1: float, text: str, block: int) -> SourceFragment:
    return SourceFragment(
        page_number=1,
        bbox=(100.0, y0, 110.0, y1),
        block_number=block,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


class DirectionalTableGeometryTests(unittest.TestCase):
    def test_rotated_rule_bounded_row_is_detected_in_writing_frame_without_rewriting_source_bbox(self) -> None:
        first = _fragment(300.0, 350.0, "Alpha", 1)
        second = _fragment(100.0, 150.0, "Beta", 2)
        parts = (first, second)
        line = VisualLine(
            line_id=visual_line_id(1, parts),
            page_number=1,
            bbox=(100.0, 100.0, 110.0, 350.0),
            text="Alpha Beta",
            fragments=parts,
            font_size=10.0,
            font_name="SyntheticBody",
        )
        rules = (
            RuleSegment(1, 90.0, 80.0, 90.0, 370.0),
            RuleSegment(1, 120.0, 80.0, 120.0, 370.0),
            RuleSegment(1, 150.0, 80.0, 150.0, 370.0),
        )
        page = CleanedPage(1, 600.0, 800.0, (line,), (), rules)
        profile = PageOrderProfile(1, ReadingOrderMode.TOP_TO_BOTTOM, None, 0.8, ("top_to_bottom",))

        rows = detect_table_rows_in_writing_frame(page, profile, (0.0, -1.0))

        self.assertEqual(len(rows), 1)
        self.assertEqual([cell.text for cell in rows[0].cells], ["Alpha", "Beta"])
        self.assertEqual(rows[0].bbox, (-350.0, 100.0, -100.0, 110.0))
        self.assertEqual(rows[0].cell_starts, (-350.0, -150.0))
        self.assertEqual(rows[0].fragments[0].bbox, first.bbox)
        self.assertEqual(rows[0].fragments[1].bbox, second.bbox)
        self.assertIn("writing_direction:0.000,-1.000", rows[0].evidence)

    def test_zero_direction_fails_closed(self) -> None:
        page = CleanedPage(1, 600.0, 800.0, (), ())
        profile = PageOrderProfile(1, ReadingOrderMode.TOP_TO_BOTTOM, None, 0.8, ("top_to_bottom",))

        with self.assertRaisesRegex(ValueError, "writing direction"):
            detect_table_rows_in_writing_frame(page, profile, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
