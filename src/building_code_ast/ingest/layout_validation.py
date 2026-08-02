"""Fail-closed invariants for analyzed PDF layout projections."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from .layout_analysis import CleanedPage, PageOrderProfile, RemovedLine, VisualLine
from .table_geometry import TableCandidate


def validate_line_coverage(
    retained_lines: Sequence[VisualLine],
    removed_lines: Sequence[RemovedLine],
    blocks: Sequence[Any],
) -> None:
    retained_ids = [line.line_id for line in retained_lines]
    retained_counts = Counter(retained_ids)
    duplicate_retained = sorted(
        line_id for line_id, count in retained_counts.items() if count > 1
    )
    if duplicate_retained:
        raise ValueError(
            "duplicate retained line ID: " + ", ".join(duplicate_retained)
        )

    removed_ids: list[str] = []
    for removed in removed_lines:
        if not removed.reason.strip():
            raise ValueError("removed line must have a nonempty reason")
        removed_ids.append(removed.line.line_id)
    overlap = sorted(set(retained_ids) & set(removed_ids))
    if overlap:
        raise ValueError(
            "line cannot be retained and removed: " + ", ".join(overlap)
        )

    consumed: Counter[str] = Counter()
    for block in blocks:
        line_ids = tuple(getattr(block, "source_line_ids", ()))
        for line_id in line_ids:
            if line_id not in retained_counts:
                raise ValueError(f"block references unknown line ID: {line_id}")
            consumed[line_id] += 1

    missing = sorted(line_id for line_id in retained_ids if consumed[line_id] == 0)
    if missing:
        raise ValueError("missing retained line: " + ", ".join(missing))
    duplicate = sorted(line_id for line_id, count in consumed.items() if count > 1)
    if duplicate:
        raise ValueError("line consumed more than once: " + ", ".join(duplicate))


def validate_page_profiles(
    pages: Sequence[CleanedPage],
    profiles: Sequence[PageOrderProfile],
) -> None:
    page_numbers = [page.page_number for page in pages]
    if len(page_numbers) != len(set(page_numbers)):
        raise ValueError("cleaned pages contain duplicate page numbers")
    profile_numbers = [profile.page_number for profile in profiles]
    if len(profile_numbers) != len(set(profile_numbers)):
        raise ValueError("duplicate page profile")
    if set(page_numbers) != set(profile_numbers):
        raise ValueError("page profile set does not match cleaned pages")


def validate_table_candidate(table: TableCandidate) -> None:
    for row in table.rows:
        if row.page_number != table.page_number:
            raise ValueError("table row references another page")
        row_fragments = set(row.fragments)
        for cell in row.cells:
            foreign = [fragment for fragment in cell.fragments if fragment not in row_fragments]
            if foreign:
                raise ValueError("table cell fragment is outside its parent row")
            if not 0 <= cell.local_start <= cell.local_end <= len(table.normalized_text):
                raise ValueError("table cell span is outside normalized table text")
            if table.normalized_text[cell.local_start : cell.local_end] != cell.text:
                raise ValueError("table cell span does not round-trip")


def validate_layout_projection(chapter: Any) -> None:
    """Validate a chapter-like projection without importing publication code."""

    pages = tuple(getattr(chapter, "cleaned_pages", ()))
    profiles = tuple(getattr(chapter, "page_profiles", ()))
    retained = tuple(
        line for page in pages for line in getattr(page, "retained", ())
    )
    removed = tuple(
        item for page in pages for item in getattr(page, "removed", ())
    )
    blocks = tuple(getattr(chapter, "blocks", ()))
    if pages or profiles:
        validate_page_profiles(pages, profiles)
    if retained or removed or blocks:
        validate_line_coverage(retained, removed, blocks)
    for block in blocks:
        table = getattr(block, "table", None)
        if table is not None:
            validate_table_candidate(table)
