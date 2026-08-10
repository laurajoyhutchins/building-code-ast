"""Writing-frame adapter for the shared table-row geometry detector."""

from __future__ import annotations

from dataclasses import replace

from .layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    RuleSegment,
    SourceFragment,
    VisualLine,
)
from .table_geometry import TableCellCandidate, TableRowCandidate, detect_table_rows
from .writing_frame import project_bbox_to_writing_frame


Direction = tuple[float, float]


def _project_point(x: float, y: float, direction: Direction) -> tuple[float, float]:
    inline0, block0, _inline1, _block1 = project_bbox_to_writing_frame(
        (x, y, x, y), direction
    )
    return inline0, block0


def _project_rule(rule: RuleSegment, direction: Direction) -> RuleSegment:
    x0, y0 = _project_point(rule.x0, rule.y0, direction)
    x1, y1 = _project_point(rule.x1, rule.y1, direction)
    return RuleSegment(rule.page_number, x0, y0, x1, y1)


def _project_page(
    page: CleanedPage,
    direction: Direction,
) -> tuple[CleanedPage, dict[int, SourceFragment]]:
    frame = project_bbox_to_writing_frame(
        (0.0, 0.0, page.width, page.height), direction
    )
    frame_width = frame[2] - frame[0]
    frame_height = frame[3] - frame[1]
    original_by_projected_id: dict[int, SourceFragment] = {}
    lines: list[VisualLine] = []

    for line in page.retained:
        projected_fragments: list[SourceFragment] = []
        for fragment in line.fragments:
            projected = replace(
                fragment,
                bbox=project_bbox_to_writing_frame(fragment.bbox, direction),
            )
            original_by_projected_id[id(projected)] = fragment
            projected_fragments.append(projected)
        lines.append(
            replace(
                line,
                bbox=project_bbox_to_writing_frame(line.bbox, direction),
                fragments=tuple(projected_fragments),
            )
        )

    return (
        CleanedPage(
            page_number=page.page_number,
            width=frame_width,
            height=frame_height,
            retained=tuple(lines),
            removed=(),
            rules=tuple(_project_rule(rule, direction) for rule in page.rules),
        ),
        original_by_projected_id,
    )


def _restore_row_fragments(
    row: TableRowCandidate,
    originals: dict[int, SourceFragment],
    direction: Direction,
) -> TableRowCandidate:
    cells = tuple(
        replace(
            cell,
            fragments=tuple(originals[id(fragment)] for fragment in cell.fragments),
        )
        for cell in row.cells
    )
    fragments = tuple(originals[id(fragment)] for fragment in row.fragments)
    evidence = row.evidence + (
        f"writing_direction:{direction[0]:.3f},{direction[1]:.3f}",
        "geometry_frame:writing",
        "source_fragments:native_page",
    )
    return replace(row, cells=cells, fragments=fragments, evidence=evidence)


def detect_table_rows_in_writing_frame(
    page: CleanedPage,
    profile: PageOrderProfile,
    direction: Direction,
) -> tuple[TableRowCandidate, ...]:
    """Detect table rows after projecting geometry into a writing-aligned frame.

    Candidate bbox and cell-start coordinates are expressed in the writing
    frame. Source fragments inside the candidate remain in native page
    coordinates. Semantic table roles and caption ownership remain unresolved.
    """

    if profile.page_number != page.page_number:
        raise ValueError("page profile does not match cleaned page")
    normalized_probe = project_bbox_to_writing_frame((0.0, 0.0, 1.0, 1.0), direction)
    del normalized_probe
    horizontal = abs(float(direction[1])) <= 1e-9 and float(direction[0]) > 0.0
    if not horizontal and profile.mode is ReadingOrderMode.TWO_COLUMN:
        raise ValueError(
            "two-column profile must already be expressed in the writing frame"
        )

    projected_page, originals = _project_page(page, direction)
    projected_profile = PageOrderProfile(
        page_number=profile.page_number,
        mode=profile.mode,
        split_x=profile.split_x if horizontal else None,
        confidence=profile.confidence,
        evidence=profile.evidence + ("geometry_frame:writing",),
    )
    rows = detect_table_rows(projected_page, projected_profile)
    return tuple(
        _restore_row_fragments(row, originals, direction)
        for row in rows
    )
