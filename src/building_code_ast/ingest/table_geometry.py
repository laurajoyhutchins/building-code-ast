"""Geometry-backed table candidates for positioned PDF text."""

from __future__ import annotations

from dataclasses import dataclass, replace
import statistics
from typing import Sequence

from .layout_analysis import CleanedPage, PageOrderProfile, ReadingOrderMode, RuleSegment, SourceFragment


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
    if fragment.bbox[2] > fragment.bbox[0]:
        return fragment.bbox[2]
    return fragment.bbox[0] + len(fragment.raw_text) * max(fragment.font_size, 8.0) * 0.45


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


def detect_table_rows(page: CleanedPage, profile: PageOrderProfile) -> tuple[TableRowCandidate, ...]:
    if profile.page_number != page.page_number:
        raise ValueError("page profile does not match cleaned page")
    rule_regions = _rule_regions(page)
    owned: list[tuple[SourceFragment, str]] = []
    for line in page.retained:
        owned.extend((fragment, line.line_id) for fragment in line.fragments)
    owned.sort(key=lambda item: (_center_y(item[0]), item[0].bbox[0]))
    groups: list[list[tuple[SourceFragment, str]]] = []
    for item in owned:
        fragment = item[0]
        chosen = None
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
        row_bbox = _bbox(fragments)
        row_center_x = (row_bbox[0] + row_bbox[2]) / 2.0
        row_center_y = (row_bbox[1] + row_bbox[3]) / 2.0
        matching_rule_regions = tuple(
            (x0, y0, x1, y1)
            for x0, y0, x1, y1 in rule_regions
            if x0 - 3.0 <= row_center_x <= x1 + 3.0 and y0 - 3.0 <= row_center_y <= y1 + 3.0
        )
        inside_rule_region = bool(matching_rule_regions)
        row_font = max(statistics.median([item.font_size for item in fragments if item.font_size > 0.0] or [_height(item) for item in fragments]), 1.0)
        cell_gap = max(18.0, row_font * 1.8)
        cells: list[list[SourceFragment]] = [[]]
        separators: list[tuple[float, float, float]] = []
        previous = None
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
            straddles_split = profile.split_x is not None and gap_left < profile.split_x < gap_right
            page_column_shape = straddles_split or (page.width > 0.0 and largest_gap > page.width * 0.18)
            if page_column_shape and not inside_rule_region:
                continue
        text_cells = [_join_cell(cell) for cell in cells]
        if sum(bool(value) for value in text_cells) < 2:
            continue
        local_cursor = 0
        cell_records = []
        for index, (text, cell_fragments) in enumerate(zip(text_cells, cells, strict=True)):
            if index:
                local_cursor += 1
            start = local_cursor
            local_cursor += len(text)
            cell_records.append(TableCellCandidate(text, tuple(cell_fragments), start, local_cursor))
        source_line_ids = tuple(dict.fromkeys(item[1] for item in group))
        rows.append(
            TableRowCandidate(
                page.page_number,
                source_line_ids,
                tuple(cell_records),
                row_bbox,
                tuple(cell[0].bbox[0] for cell in cells),
                tuple(fragments),
                round(row_font, 3),
                0.82,
                (
                    "geometry_cells",
                    f"cells:{len(cell_records)}",
                    f"fragments:{len(fragments)}",
                    *(
                        f"rule_region:{x0:.3f},{y0:.3f},{x1:.3f},{y1:.3f}"
                        for x0, y0, x1, y1 in matching_rule_regions
                    ),
                ),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.page_number, row.bbox[1], row.bbox[0])))


def _aligned_columns(left: TableRowCandidate, right: TableRowCandidate) -> int:
    tolerance = max(12.0, statistics.median((left.font_size, right.font_size)) * 1.5)
    positional_matches = sum(
        1
        for left_start, right_start in zip(left.cell_starts, right.cell_starts)
        if abs(left_start - right_start) <= tolerance
    )
    if positional_matches >= 2:
        return positional_matches

    left_regions = {item for item in left.evidence if item.startswith("rule_region:")}
    right_regions = {item for item in right.evidence if item.startswith("rule_region:")}
    if not left_regions.intersection(right_regions):
        return positional_matches

    left_starts = sorted(left.cell_starts)
    right_starts = sorted(right.cell_starts)
    left_index = 0
    right_index = 0
    matches = 0
    while left_index < len(left_starts) and right_index < len(right_starts):
        delta = left_starts[left_index] - right_starts[right_index]
        if abs(delta) <= tolerance:
            matches += 1
            left_index += 1
            right_index += 1
        elif delta < 0.0:
            left_index += 1
        else:
            right_index += 1
    return matches


def _compatible(left: TableRowCandidate, right: TableRowCandidate) -> bool:
    if left.page_number != right.page_number or len(left.cells) < 2 or len(right.cells) < 2:
        return False
    median_height = statistics.median((max(0.1, left.bbox[3] - left.bbox[1]), max(0.1, right.bbox[3] - right.bbox[1])))
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
        new_cells = []
        for cell_index, value in enumerate(values):
            if cell_index:
                chunks.append("\t")
                cursor += 1
            start = cursor
            chunks.append(value)
            cursor += len(value)
            source_cell = row.cells[cell_index] if cell_index < len(row.cells) else None
            new_cells.append(TableCellCandidate(value, source_cell.fragments if source_cell else (), start, cursor))
        normalized_rows.append(replace(row, cells=tuple(new_cells)))
    return "".join(chunks), tuple(normalized_rows)


def _cluster_positions(values: Sequence[float], tolerance: float = 2.0) -> tuple[float, ...]:
    if not values:
        return ()
    groups: list[list[float]] = []
    for value in sorted(values):
        if not groups or abs(value - statistics.mean(groups[-1])) > tolerance:
            groups.append([value])
        else:
            groups[-1].append(value)
    return tuple(round(statistics.mean(group), 3) for group in groups)


def _rule_regions(page: CleanedPage) -> tuple[tuple[float, float, float, float], ...]:
    horizontal = [
        rule
        for rule in page.rules
        if rule.horizontal and abs(rule.x1 - rule.x0) >= max(40.0, page.width * 0.20)
    ]
    if len(horizontal) < 3:
        return ()
    groups: list[list[RuleSegment]] = []
    for rule in sorted(horizontal, key=lambda item: (min(item.x0, item.x1), max(item.x0, item.x1), item.y0)):
        x0, x1 = sorted((rule.x0, rule.x1))
        matched: list[RuleSegment] | None = None
        for group in groups:
            gx0 = statistics.median(min(item.x0, item.x1) for item in group)
            gx1 = statistics.median(max(item.x0, item.x1) for item in group)
            if abs(x0 - gx0) <= 4.0 and abs(x1 - gx1) <= 4.0:
                matched = group
                break
        if matched is None:
            matched = []
            groups.append(matched)
        matched.append(rule)
    regions: list[tuple[float, float, float, float]] = []
    for group in groups:
        ys = _cluster_positions([(item.y0 + item.y1) / 2.0 for item in group])
        if len(ys) < 3:
            continue
        x0 = statistics.median(min(item.x0, item.x1) for item in group)
        x1 = statistics.median(max(item.x0, item.x1) for item in group)
        regions.append((round(x0, 3), ys[0], round(x1, 3), ys[-1]))
    return tuple(regions)


def _line_for_fragment(page: CleanedPage) -> dict[SourceFragment, str]:
    return {
        fragment: line.line_id
        for line in page.retained
        for fragment in line.fragments
    }


def _cell_text(parts: Sequence[SourceFragment]) -> str:
    ordered = sorted(parts, key=lambda item: (item.bbox[1], item.bbox[0], item.block_number))
    rows: list[list[SourceFragment]] = []
    for fragment in ordered:
        center = _center_y(fragment)
        matched: list[SourceFragment] | None = None
        for row in rows:
            tolerance = max(2.5, statistics.median([item.font_size or _height(item) for item in row]) * 0.35)
            if abs(_center_y(row[0]) - center) <= tolerance:
                matched = row
                break
        if matched is None:
            matched = []
            rows.append(matched)
        matched.append(fragment)
    text_rows = [_join_cell(sorted(row, key=lambda item: item.bbox[0])) for row in rows]
    return " ".join(value for value in text_rows if value).strip()


def detect_ruled_tables(page: CleanedPage) -> tuple[TableCandidate, ...]:
    """Reconstruct base-grid cells from vector rule boundaries.

    Merged source cells are represented by the finest stable boundary grid. This
    preserves positioned text without inferring semantic spans or headers.
    """

    fragment_lines = _line_for_fragment(page)
    tables: list[TableCandidate] = []
    for x0, y0, x1, y1 in _rule_regions(page):
        vertical = [
            rule
            for rule in page.rules
            if rule.vertical
            and x0 - 3.0 <= (rule.x0 + rule.x1) / 2.0 <= x1 + 3.0
            and (
                min(max(rule.y0, rule.y1), y1)
                - max(min(rule.y0, rule.y1), y0)
            ) >= (y1 - y0) * 0.50
        ]
        xs = _cluster_positions(
            [x0, x1] + [(rule.x0 + rule.x1) / 2.0 for rule in vertical]
        )
        horizontal = [
            rule
            for rule in page.rules
            if rule.horizontal
            and (
                min(max(rule.x0, rule.x1), x1)
                - max(min(rule.x0, rule.x1), x0)
            ) >= (x1 - x0) * 0.50
            and y0 - 3.0 <= (rule.y0 + rule.y1) / 2.0 <= y1 + 3.0
        ]
        ys = _cluster_positions(
            [y0, y1] + [(rule.y0 + rule.y1) / 2.0 for rule in horizontal]
        )
        if len(xs) < 3 or len(ys) < 3:
            continue

        region_fragments = [
            fragment
            for line in page.retained
            for fragment in line.fragments
            if x0 <= (fragment.bbox[0] + fragment.bbox[2]) / 2.0 <= x1
            and y0 <= _center_y(fragment) <= y1
        ]
        rows: list[TableRowCandidate] = []
        for row_index, (top, bottom) in enumerate(zip(ys, ys[1:])):
            cells: list[TableCellCandidate] = []
            row_fragments: list[SourceFragment] = []
            starts: list[float] = []
            for left, right in zip(xs, xs[1:]):
                parts = [
                    fragment
                    for fragment in region_fragments
                    if top <= _center_y(fragment) < bottom
                    and left <= (fragment.bbox[0] + fragment.bbox[2]) / 2.0 < right
                ]
                row_fragments.extend(parts)
                starts.append(left)
                cells.append(TableCellCandidate(_cell_text(parts), tuple(parts), 0, 0))
            if not any(cell.text for cell in cells):
                continue
            source_ids = tuple(
                dict.fromkeys(
                    fragment_lines[fragment]
                    for fragment in row_fragments
                    if fragment in fragment_lines
                )
            )
            rows.append(
                TableRowCandidate(
                    page_number=page.page_number,
                    source_line_ids=source_ids,
                    cells=tuple(cells),
                    bbox=(x0, top, x1, bottom),
                    cell_starts=tuple(starts),
                    fragments=tuple(row_fragments),
                    font_size=statistics.median(
                        [fragment.font_size for fragment in row_fragments if fragment.font_size > 0.0]
                        or [10.0]
                    ),
                    confidence=0.96,
                    evidence=(
                        "vector_rule_grid",
                        f"row_index:{row_index}",
                        f"columns:{len(cells)}",
                    ),
                )
            )
        if len(rows) < 2:
            continue
        normalized_text, normalized_rows = _normalize_rows(rows)
        tables.append(
            TableCandidate(
                page_number=page.page_number,
                rows=normalized_rows,
                normalized_text=normalized_text,
                confidence=0.97,
                evidence=(
                    "vector_rule_grid",
                    f"rows:{len(normalized_rows)}",
                    f"columns:{len(xs) - 1}",
                ),
            )
        )
    return tuple(tables)


def group_table_candidates(rows: Sequence[TableRowCandidate]) -> tuple[TableCandidate, ...]:
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
    tables = []
    for group in groups:
        normalized_text, normalized_rows = _normalize_rows(group)
        alignment = min(_aligned_columns(left, right) for left, right in zip(group, group[1:]))
        confidence = round(min(0.96, 0.72 + len(group) * 0.04 + alignment * 0.03), 3)
        tables.append(TableCandidate(group[0].page_number, normalized_rows, normalized_text, confidence, ("compatible_geometry_rows", f"rows:{len(group)}", f"aligned_columns:{alignment}")))
    return tuple(tables)