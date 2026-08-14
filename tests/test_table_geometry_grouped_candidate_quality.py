from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import SourceFragment
from building_code_ast.ingest.table_geometry import (
    TableCellCandidate,
    TableRowCandidate,
    group_table_candidates,
)


def _fragment(*, x0: float, x1: float, y0: float, text: str, block: int) -> SourceFragment:
    return SourceFragment(
        page_number=1,
        bbox=(x0, y0, x1, y0 + 10.0),
        block_number=block,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


def _row(
    index: int,
    *,
    left_block: int,
    right_block: int,
    x0: float = 10.0,
    x1: float = 210.0,
) -> TableRowCandidate:
    y0 = 10.0 + index * 12.0
    split = (x0 + x1) / 2.0
    left = _fragment(x0=x0, x1=split - 5.0, y0=y0, text=f"L{index}", block=left_block)
    right = _fragment(x0=split + 5.0, x1=x1, y0=y0, text=f"R{index}", block=right_block)
    return TableRowCandidate(
        page_number=1,
        source_line_ids=(f"line-{index}",),
        cells=(
            TableCellCandidate(left.raw_text, (left,), 0, len(left.raw_text)),
            TableCellCandidate(right.raw_text, (right,), len(left.raw_text) + 1, len(left.raw_text) + 1 + len(right.raw_text)),
        ),
        bbox=(x0, y0, x1, y0 + 10.0),
        cell_starts=(x0, split + 5.0),
        fragments=(left, right),
        font_size=10.0,
        confidence=0.82,
        evidence=("geometry_cells", "cells:2", "fragments:2"),
    )


class GroupedCandidateQualityTests(unittest.TestCase):
    def test_page_spanning_two_cell_parallel_source_blocks_are_rejected(self) -> None:
        rows = tuple(
            _row(index, left_block=left_block, right_block=100 + index)
            for index, left_block in enumerate((7, 7, 8, 9, 9))
        )

        self.assertEqual(group_table_candidates(rows, page_width=220.0), ())

    def test_page_spanning_two_cell_rows_without_repeated_source_flow_are_preserved(self) -> None:
        rows = tuple(
            _row(index, left_block=10 + index, right_block=100 + index)
            for index in range(5)
        )

        self.assertEqual(len(group_table_candidates(rows, page_width=220.0)), 1)

    def test_narrow_two_cell_candidate_is_preserved_even_with_repeated_source_blocks(self) -> None:
        rows = tuple(
            _row(index, left_block=7, right_block=100 + index, x0=30.0, x1=190.0)
            for index in range(3)
        )

        self.assertEqual(len(group_table_candidates(rows, page_width=220.0)), 1)


if __name__ == "__main__":
    unittest.main()
