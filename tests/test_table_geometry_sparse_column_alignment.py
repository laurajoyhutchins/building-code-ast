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
from building_code_ast.ingest.table_geometry import (
    TableCellCandidate,
    TableRowCandidate,
    detect_table_rows,
    group_table_candidates,
)


def _row(
    page: int,
    y: float,
    starts: tuple[float, ...],
    *,
    rule_region: str | None = None,
) -> TableRowCandidate:
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
    evidence = ["geometry_cells"]
    if rule_region is not None:
        evidence.append(f"rule_region:{rule_region}")
    return TableRowCandidate(
        page_number=page,
        source_line_ids=(visual_line_id(page, tuple(fragments)),),
        cells=tuple(cells),
        bbox=(min(starts), y, max(starts) + 20.0, y + 10.0),
        cell_starts=starts,
        fragments=tuple(fragments),
        font_size=10.0,
        confidence=0.82,
        evidence=tuple(evidence),
    )


def _line(page: int, parts: tuple[SourceFragment, ...]) -> VisualLine:
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
        font_size=10.0,
        font_name="SyntheticBody",
    )


class SparseColumnAlignmentTests(unittest.TestCase):
    def test_rule_bounded_sparse_row_aligns_by_observed_column_anchors(self) -> None:
        region = "50.000,90.000,320.000,150.000"
        full = _row(1, 100.0, (50.0, 100.0, 200.0, 300.0), rule_region=region)
        sparse = _row(1, 120.0, (100.0, 200.0), rule_region=region)

        tables = group_table_candidates((full, sparse))

        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0].rows), 2)

    def test_rule_bounded_sparse_row_with_only_one_matching_anchor_remains_ungrouped(self) -> None:
        region = "50.000,90.000,320.000,150.000"
        full = _row(1, 100.0, (50.0, 100.0, 200.0, 300.0), rule_region=region)
        shifted = _row(1, 120.0, (100.0, 230.0), rule_region=region)

        self.assertEqual(group_table_candidates((full, shifted)), ())

    def test_unbounded_sparse_rows_do_not_gain_nonordinal_alignment(self) -> None:
        full = _row(1, 100.0, (50.0, 100.0, 200.0, 300.0))
        sparse = _row(1, 120.0, (100.0, 200.0))

        self.assertEqual(group_table_candidates((full, sparse)), ())

    def test_fallback_rows_preserve_matching_measured_rule_region_evidence(self) -> None:
        first = (
            SourceFragment(1, (50.0, 100.0, 70.0, 110.0), 1, "A", 10.0, "SyntheticBody"),
            SourceFragment(1, (200.0, 100.0, 220.0, 110.0), 2, "B", 10.0, "SyntheticBody"),
        )
        second = (
            SourceFragment(1, (50.0, 120.0, 70.0, 130.0), 3, "C", 10.0, "SyntheticBody"),
            SourceFragment(1, (200.0, 120.0, 220.0, 130.0), 4, "D", 10.0, "SyntheticBody"),
        )
        page = CleanedPage(
            page_number=1,
            width=300.0,
            height=200.0,
            retained=(_line(1, first), _line(1, second)),
            removed=(),
            rules=(
                RuleSegment(1, 40.0, 90.0, 240.0, 90.0),
                RuleSegment(1, 40.0, 115.0, 240.0, 115.0),
                RuleSegment(1, 40.0, 140.0, 240.0, 140.0),
            ),
        )
        profile = PageOrderProfile(1, ReadingOrderMode.TOP_TO_BOTTOM, None, 0.8, ("top_to_bottom",))

        rows = detect_table_rows(page, profile)
        region_keys = [
            {item for item in row.evidence if item.startswith("rule_region:")}
            for row in rows
        ]

        self.assertEqual(len(rows), 2)
        self.assertTrue(region_keys[0])
        self.assertEqual(region_keys[0], region_keys[1])


if __name__ == "__main__":
    unittest.main()
