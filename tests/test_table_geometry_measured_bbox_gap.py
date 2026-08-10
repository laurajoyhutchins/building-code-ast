from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    SourceFragment,
    VisualLine,
    visual_line_id,
)
from building_code_ast.ingest.table_geometry import detect_table_rows


def _fragment(x0: float, x1: float, text: str, block: int) -> SourceFragment:
    return SourceFragment(
        page_number=1,
        bbox=(x0, 100.0, x1, 110.0),
        block_number=block,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


def _page(parts: tuple[SourceFragment, ...]) -> CleanedPage:
    line = VisualLine(
        line_id=visual_line_id(1, parts),
        page_number=1,
        bbox=(
            min(item.bbox[0] for item in parts),
            100.0,
            max(item.bbox[2] for item in parts),
            110.0,
        ),
        text=" ".join(item.raw_text for item in parts),
        fragments=parts,
        font_size=10.0,
        font_name="SyntheticBody",
    )
    return CleanedPage(1, 600.0, 300.0, (line,), ())


_PROFILE = PageOrderProfile(
    page_number=1,
    mode=ReadingOrderMode.TOP_TO_BOTTOM,
    split_x=None,
    confidence=0.8,
    evidence=("top_to_bottom",),
)


class TableGeometryMeasuredBboxGapTests(unittest.TestCase):
    def test_valid_measured_bbox_gap_is_not_erased_by_character_width_estimate(self) -> None:
        left = _fragment(
            50.0,
            200.0,
            "A deliberately long wrapped-cell source line whose measured right edge is authoritative",
            1,
        )
        right = _fragment(220.0, 270.0, "Annual", 2)

        rows = detect_table_rows(_page((left, right)), _PROFILE)

        self.assertEqual(len(rows), 1)
        self.assertEqual([cell.text for cell in rows[0].cells], [left.raw_text, "Annual"])

    def test_small_measured_gap_does_not_create_a_cell_boundary(self) -> None:
        left = _fragment(50.0, 200.0, "Long source text", 1)
        right = _fragment(210.0, 250.0, "continuation", 2)

        self.assertEqual(detect_table_rows(_page((left, right)), _PROFILE), ())


if __name__ == "__main__":
    unittest.main()
