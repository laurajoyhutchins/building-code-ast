from __future__ import annotations

from dataclasses import dataclass
import unittest

from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    RemovedLine,
    SourceFragment,
    VisualLine,
)
from building_code_ast.ingest.layout_validation import (
    validate_line_coverage,
    validate_page_profiles,
    validate_table_candidate,
)
from building_code_ast.ingest.table_geometry import (
    TableCandidate,
    TableCellCandidate,
    TableRowCandidate,
)


@dataclass(frozen=True, slots=True)
class Block:
    source_line_ids: tuple[str, ...]


def source_fragment(page: int, text: str, block: int = 1) -> SourceFragment:
    return SourceFragment(
        page_number=page,
        bbox=(10.0, 10.0, 40.0, 20.0),
        block_number=block,
        raw_text=text,
        font_size=10.0,
        font_name="SyntheticBody",
    )


def source_line(line_id: str, page: int = 1) -> VisualLine:
    item = source_fragment(page, line_id)
    return VisualLine(
        line_id=line_id,
        page_number=page,
        bbox=item.bbox,
        text=line_id,
        fragments=(item,),
        font_size=10.0,
        font_name="SyntheticBody",
    )


class LayoutValidationTests(unittest.TestCase):
    def test_missing_retained_line_fails(self) -> None:
        retained = (source_line("line:a"), source_line("line:b"))
        with self.assertRaisesRegex(ValueError, "missing retained line"):
            validate_line_coverage(retained, (), (Block(("line:a",)),))

    def test_duplicate_line_consumption_fails(self) -> None:
        retained = (source_line("line:a"),)
        blocks = (Block(("line:a",)), Block(("line:a",)))
        with self.assertRaisesRegex(ValueError, "consumed more than once"):
            validate_line_coverage(retained, (), blocks)

    def test_line_cannot_be_retained_and_removed(self) -> None:
        line = source_line("line:a")
        with self.assertRaisesRegex(ValueError, "retained and removed"):
            validate_line_coverage(
                (line,),
                (RemovedLine(line=line, reason="recurring_header"),),
                (Block(("line:a",)),),
            )

    def test_page_profile_must_match_cleaned_page(self) -> None:
        page = CleanedPage(1, 100.0, 100.0, (source_line("line:a"),), ())
        profile = PageOrderProfile(
            page_number=2,
            mode=ReadingOrderMode.TOP_TO_BOTTOM,
            split_x=None,
            confidence=0.5,
            evidence=("fallback",),
        )
        with self.assertRaisesRegex(ValueError, "page profile"):
            validate_page_profiles((page,), (profile,))

    def test_table_cell_fragment_must_belong_to_parent_row(self) -> None:
        row_fragment = source_fragment(1, "A", block=1)
        foreign = source_fragment(1, "B", block=2)
        row = TableRowCandidate(
            page_number=1,
            source_line_ids=("line:a",),
            cells=(TableCellCandidate("B", (foreign,), 0, 1),),
            bbox=(10.0, 10.0, 40.0, 20.0),
            cell_starts=(10.0,),
            fragments=(row_fragment,),
            font_size=10.0,
            confidence=0.7,
            evidence=("geometry_cells",),
        )
        table = TableCandidate(
            page_number=1,
            rows=(row,),
            normalized_text="B",
            confidence=0.7,
            evidence=("rows:1",),
        )

        with self.assertRaisesRegex(ValueError, "outside its parent row"):
            validate_table_candidate(table)

    def test_table_cell_span_must_round_trip(self) -> None:
        item = source_fragment(1, "A")
        row = TableRowCandidate(
            page_number=1,
            source_line_ids=("line:a",),
            cells=(TableCellCandidate("A", (item,), 1, 2),),
            bbox=(10.0, 10.0, 40.0, 20.0),
            cell_starts=(10.0,),
            fragments=(item,),
            font_size=10.0,
            confidence=0.7,
            evidence=("geometry_cells",),
        )
        table = TableCandidate(
            page_number=1,
            rows=(row,),
            normalized_text="A",
            confidence=0.7,
            evidence=("rows:1",),
        )

        with self.assertRaisesRegex(ValueError, "does not round-trip"):
            validate_table_candidate(table)


if __name__ == "__main__":
    unittest.main()
