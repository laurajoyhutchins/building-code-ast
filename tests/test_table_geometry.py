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
from building_code_ast.ingest.table_geometry import (
    TableCellCandidate,
    TableRowCandidate,
    detect_table_rows,
    group_table_candidates,
)


def fragment(
    page: int,
    x0: float,
    y0: float,
    x1: float,
    text: str,
    *,
    font_size: float = 10.0,
    block: int = 1,
) -> SourceFragment:
    return SourceFragment(
        page_number=page,
        bbox=(x0, y0, x1, y0 + font_size),
        block_number=block,
        raw_text=text,
        font_size=font_size,
        font_name="SyntheticBody",
    )


def line_for_fragments(page: int, parts: tuple[SourceFragment, ...]) -> VisualLine:
    return VisualLine(
        line_id=visual_line_id(page, parts),
        page_number=page,
        bbox=(
            min(item.bbox[0] for item in parts),
            min(item.bbox[1] for item in parts),
            max(item.bbox[2] for item in parts),
            max(item.bbox[3] for item in parts),
        ),
        text=" ".join(item.raw_text for item in parts),
        fragments=parts,
        font_size=max(item.font_size for item in parts),
        font_name="SyntheticBody",
    )


def profile(page: int, mode: ReadingOrderMode, split_x: float | None = None) -> PageOrderProfile:
    return PageOrderProfile(
        page_number=page,
        mode=mode,
        split_x=split_x,
        confidence=0.8,
        evidence=(mode.value,),
    )


def synthetic_row(page: int, y: float, values: tuple[str, ...]) -> TableRowCandidate:
    cells: list[TableCellCandidate] = []
    cursor = 0
    all_fragments: list[SourceFragment] = []
    starts: list[float] = []
    for index, value in enumerate(values):
        item = fragment(page, 50.0 + index * 150.0, y, 90.0 + index * 150.0, value, block=index)
        all_fragments.append(item)
        starts.append(item.bbox[0])
        cells.append(
            TableCellCandidate(
                text=value,
                fragments=(item,),
                local_start=cursor,
                local_end=cursor + len(value),
            )
        )
        cursor += len(value) + 1
    return TableRowCandidate(
        page_number=page,
        source_line_ids=(visual_line_id(page, tuple(all_fragments)),),
        cells=tuple(cells),
        bbox=(50.0, y, 90.0 + (len(values) - 1) * 150.0, y + 10.0),
        cell_starts=tuple(starts),
        fragments=tuple(all_fragments),
        font_size=10.0,
        confidence=0.85,
        evidence=("geometry_cells",),
    )


class TableGeometryTests(unittest.TestCase):
    def test_detects_two_cells_and_preserves_all_fragments(self) -> None:
        parts = (
            fragment(1, 50.0, 100.0, 85.0, "Group", block=1),
            fragment(1, 90.0, 100.0, 120.0, "A", block=2),
            fragment(1, 210.0, 100.0, 250.0, "Limit", block=3),
        )
        page = CleanedPage(
            page_number=1,
            width=300.0,
            height=300.0,
            retained=(line_for_fragments(1, parts),),
            removed=(),
        )

        rows = detect_table_rows(page, profile(1, ReadingOrderMode.TOP_TO_BOTTOM))

        self.assertEqual([cell.text for cell in rows[0].cells], ["Group A", "Limit"])
        self.assertEqual(sum(len(cell.fragments) for cell in rows[0].cells), 3)

    def test_does_not_treat_page_columns_as_table_cells(self) -> None:
        parts = (
            fragment(1, 50.0, 100.0, 120.0, "Left paragraph", block=1),
            fragment(1, 360.0, 100.0, 450.0, "Right paragraph", block=2),
        )
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(line_for_fragments(1, parts),),
            removed=(),
        )

        rows = detect_table_rows(page, profile(1, ReadingOrderMode.TWO_COLUMN, 300.0))

        self.assertEqual(rows, ())

    def test_two_compatible_rows_form_one_table_with_exact_text(self) -> None:
        tables = group_table_candidates(
            (
                synthetic_row(1, 100.0, ("Class", "Value")),
                synthetic_row(1, 120.0, ("A", "10")),
            )
        )

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].normalized_text, "Class\tValue\nA\t10")
        self.assertEqual(
            tables[0].normalized_text[
                tables[0].rows[1].cells[1].local_start : tables[0].rows[1].cells[1].local_end
            ],
            "10",
        )

    def test_one_row_does_not_form_a_table(self) -> None:
        self.assertEqual(group_table_candidates((synthetic_row(1, 100.0, ("A", "B")),)), ())


if __name__ == "__main__":
    unittest.main()
