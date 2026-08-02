"""Geometry-backed table candidates for positioned PDF text."""

from __future__ import annotations

from dataclasses import dataclass, replace
import statistics
from typing import Sequence

from .layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    ReadingOrderMode,
    SourceFragment,
)


@dataclass(frozen=True, slots=True)
class TableCellCandidate:
    text: str
    fragments: tuple[SourceFragment, ...]
    local_start: int
    local_end: int


@dataclass(frozen=True, slots=True)
class TableRowCandidate:
    page_number: int
    source_line_ids: tuple[str, ...]
    cells: tuple[TableCellCandidate, ...]
    bbox: tuple[float, float, float, float]
    cell_starts: tuple[float, ...]
    fragments: tuple[SourceFragment, ...]
    font_size: float
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TableCandidate:
    page_number: int
    rows: tuple[TableRowCandidate, ...]
    normalized_text: str
    confidence: float
    evidence: tuple[str, ...]


def _height(fragment: SourceFragment) -> float:
    return max(0.1, fragment.bbox[3] - fragment.bbox[1])


def _center_y(fragment: SourceFragment) -> float:
    return (fragment.bbox[1] + fragment.bbox[3]) / 2.0


def _estimated_end(fragment: SourceFragment) -> float:
    return max(
        fragment.bbox[2],
        fragment.bbox[0]
        + len(fragment.raw_text) * max(fragment.font_size, 8.0) * 0.45,
    )


def _join_cell(parts: Sequence[SourceFragment]) -> str:
    output = ""
    previous: SourceFragment | None = None
    for part in parts:
        if previous is None:
            output = part.raw_text.strip()
        else:
            gap = part.bbox[0] - _estimated_end(previous)
            separator = " " if gap > max(1.5, part.font_size * 0.12) else ""
            output += separator + part.raw_text.strip()
        previous = part
    return output.strip()


def _bbox(fragments: Sequence[SourceFragment]) -> tuple[float, float, float, float]:
    return (
        min(item.bbox[0] for item in fragments),
        min(item.bbox[1] for item in fragments),
        max(item.bbox[2] for item in fragments),
        max(item.bbox[3] for item in fragments),
    )


def detect_table_rows(
    page: CleanedPage,
    profile: PageOrderProfile,
) -> tuple[TableRowCandidate, ...]:
    """Return multi-cell rows supported by positioned fragment gaps."""

    if profile.page_number != page.page_number:
        raise ValueError("page profile does not match cleaned page")

    owned: list[tuple[SourceFragment, str]] = []
    for line in page.retained:
        owned.extend((fragment, line.line_id) for fragment in line.fragments)
    owned.sort(key=lambda item: (_center_y(item[0]), item[0].bbox[0]))

    groups: list[list[tuple[SourceFragment, str]]] = []
    for item in owned:
        fragment = item[0]
        chosen: list[tuple[SourceFragment, str]] | None = None
        for group in groups:
            sizes = [member[0].font_size or _height(member[0]) for member in group]
            tolerance = max(2.5, statistics.median(sizes) * 0.25)
            if abs(_center_y(group[0][0]) - _center_y(fragment)) <= tolerance:
                chosen = group
                break
        if chosen is None:
            chosen = []
            groups.append(chosen)
        chosen.append(item)

    rows: list[TableRowCandidate] = []
    for group in groups:
        group.sort(key=lambda item: item[0].bbox[0])
        fragments = [item[0] for item in group]
        if len(fragments) < 2:
            continue
        row_font = max(
            statistics.median(
                [item.font_size for item in fragments if item.font_size > 0.0]
                or [_height(item) for item in fragments]
            ),
            1.0,
        )
        cell_gap = max(18.0, row_font * 1.8)
        cells: list[list[SourceFragment]] = [[]]
        separators: list[tuple[float, float, float]] = []
        previous: SourceFragment | None = None
        for fragment in fragments:
            gap = fragment.bbox[0] - _estimated_end(previous) if previous else 0.0
            if previous is not None and gap > cell_gap:
                separators.append((gap, _estimated_end(previous), fragment.bbox[0]))
                cells.append([])
            cells[-1].append(fragment)
            previous = fragment
        if len(cells) < 2:
            continue

        largest_gap, gap_left, gap_right = max(separators, key=lambda item: item[0])
        if profile.mode is ReadingOrderMode.TWO_COLUMN:
            straddles_split = (
                profile.split_x is not None
                and gap_left < profile.split_x < gap_right
            )
            if straddles_split or (
                page.width > 0.0 and largest_gap > page.width * 0.18
            ):
                continue

        text_cells = [_join_cell(cell) for cell in cells]
        if sum(bool(value) for value in text_cells) < 2:
            continue
        local_cursor = 0
        cell_records: list[TableCellCandidate] = []
        for index, (text, cell_fragments) in enumerate(zip(text_cells, cells, strict=True)):
            if index:
                local_cursor += 1
            start = local_cursor
            local_cursor += len(text)
            cell_records.append(
                TableCellCandidate(
                    text=text,
                    fragments=tuple(cell_fragments),
                    local_start=start,
                    local_end=local_cursor,
                )
            )
        source_line_ids = tuple(dict.fromkeys(item[1] for item in group))
        rows.append(
            TableRowCandidate(
                page_number=page.page_number,
                source_line_ids=source_line_ids,
                cells=tuple(cell_records),
                bbox=_bbox(fragments),
                cell_starts=tuple(cell[0].bbox[0] for cell in cells),
                fragments=tuple(fragments),
                font_size=round(row_font, 3),
                confidence=0.82,
                evidence=(
                    "geometry_cells",
                    f"cells:{len(cell_records)}",
                    f"fragments:{len(fragments)}",
                ),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.page_number, row.bbox[1], row.bbox[0])))


def _aligned_columns(left: TableRowCandidate, right: TableRowCandidate) -> int:
    tolerance = max(12.0, statistics.median((left.font_size, right.font_size)) * 1.5)
    return sum(
        1
        for left_start, right_start in zip(left.cell_starts, right.cell_starts)
        if abs(left_start - right_start) <= tolerance
    )


def _compatible(left: TableRowCandidate, right: TableRowCandidate) -> bool:
    if left.page_number != right.page_number:
        return False
    if len(left.cells) < 2 or len(right.cells) < 2:
        return False
    median_height = statistics.median(
        (
            max(0.1, left.bbox[3] - left.bbox[1]),
            max(0.1, right.bbox[3] - right.bbox[1]),
        )
    )
    vertical_gap = right.bbox[1] - left.bbox[3]
    return vertical_gap <= median_height * 3.0 and _aligned_columns(left, right) >= 2


def _normalize_rows(rows: Sequence[TableRowCandidate]) -> tuple[str, tuple[TableRowCandidate, ...]]:
    column_count = max(len(row.cells) for row in rows)
    chunks: list[str] = []
    normalized_rows: list[TableRowCandidate] = []
    cursor = 0
    for row_index, row in enumerate(rows):
        if row_index:
            chunks.append("\n")
            cursor += 1
        values = [cell.text for cell in row.cells]
        values.extend([""] * (column_count - len(values)))
        new_cells: list[TableCellCandidate] = []
        for cell_index, value in enumerate(values):
            if cell_index:
                chunks.append("\t")
                cursor += 1
            start = cursor
            chunks.append(value)
            cursor += len(value)
            source_cell = row.cells[cell_index] if cell_index < len(row.cells) else None
            new_cells.append(
                TableCellCandidate(
                    text=value,
                    fragments=source_cell.fragments if source_cell else (),
                    local_start=start,
                    local_end=cursor,
                )
            )
        normalized_rows.append(replace(row, cells=tuple(new_cells)))
    return "".join(chunks), tuple(normalized_rows)


def group_table_candidates(
    rows: Sequence[TableRowCandidate],
) -> tuple[TableCandidate, ...]:
    """Group consecutive aligned rows into deterministic table candidates."""

    ordered = sorted(rows, key=lambda row: (row.page_number, row.bbox[1], row.bbox[0]))
    groups: list[list[TableRowCandidate]] = []
    current: list[TableRowCandidate] = []
    for row in ordered:
        if current and not _compatible(current[-1], row):
            if len(current) >= 2:
                groups.append(current)
            current = []
        current.append(row)
    if len(current) >= 2:
        groups.append(current)

    tables: list[TableCandidate] = []
    for group in groups:
        normalized_text, normalized_rows = _normalize_rows(group)
        alignment = min(
            _aligned_columns(left, right)
            for left, right in zip(group, group[1:])
        )
        confidence = round(
            min(0.96, 0.72 + len(group) * 0.04 + alignment * 0.03),
            3,
        )
        tables.append(
            TableCandidate(
                page_number=group[0].page_number,
                rows=normalized_rows,
                normalized_text=normalized_text,
                confidence=confidence,
                evidence=(
                    "compatible_geometry_rows",
                    f"rows:{len(group)}",
                    f"aligned_columns:{alignment}",
                ),
            )
        )
    return tuple(tables)
