from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import SourceFragment, visual_line_id
from building_code_ast.ingest.table_geometry import (
    TableCellCandidate,
    TableRowCandidate,
    group_table_candidates,
)


def _row(page: int, y: float, starts: tuple[float, ...]) -> TableRowCandidate:
    fragments: list[SourceFragment] = []
    cells: list[TableCellCandidate] = []
    cursor = 0
    for index, start in enumerate(starts):
        text = f"cell-{index}"
        fragment = SourceFragment(
            page_number=page,
            bbox=(start, y, start + 20.0, y + 10.0),
            block_number=index,
            raw_text=text,
            font_size=10.0,
            font_name="SyntheticBody",
        )
        fragments.append(fragment)
        cells.append(
            TableCellCandidate(
                text=text,
                fragments=(fragment,),
                local_start=cursor,
                local_end=cursor + len(text),
            )
        )
        cursor += len(text) + 1
    return TableRowCandidate(
        page_number=page,
        source_line_ids=(visual_line_id(page, tuple(fragments)),),
        cells=tuple(cells),
        bbox=(min(starts), y, max(starts) + 20.0, y + 10.0),
        cell_starts=starts,
        fragments=tuple(fragments),
        font_size=10.0,
        confidence=0.82,
        evidence=("geometry_cells",),
    )


class SparseColumnAlignmentTests(unittest.TestCase):
    def test_sparse_row_aligns_by_observed_column_anchors_not_tuple_ordinal(self) -> None:
        full = _row(1, 100.0, (50.0, 100.0, 200.0, 300.0))
        sparse = _row(1, 120.0, (100.0, 200.0))

        tables = group_table_candidates((full, sparse))

        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0].rows), 2)

    def test_sparse_row_with_only_one_matching_anchor_remains_ungrouped(self) -> None:
        full = _row(1, 100.0, (50.0, 100.0, 200.0, 300.0))
        shifted = _row(1, 120.0, (100.0, 230.0))

        self.assertEqual(group_table_candidates((full, shifted)), ())


if __name__ == "__main__":
    unittest.main()
