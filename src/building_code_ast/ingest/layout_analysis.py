"""Publication-neutral analysis for positioned PDF text.

The records in this module describe geometry and extraction evidence only. They
contain no publication-specific chapter boundaries, headings, or semantic
interpretation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import math
import re
import statistics
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class SourceFragment:
    page_number: int
    bbox: tuple[float, float, float, float]
    block_number: int
    raw_text: str
    font_size: float = 0.0
    font_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "page_number": self.page_number,
            "bbox": [round(value, 3) for value in self.bbox],
            "block_number": self.block_number,
            "raw_text": self.raw_text,
            "font_size": round(self.font_size, 3),
        }
        if self.font_name is not None:
            payload["font_name"] = self.font_name
        return payload


@dataclass(frozen=True, slots=True)
class VisualLine:
    page_number: int
    bbox: tuple[float, float, float, float]
    text: str
    fragments: tuple[SourceFragment, ...]
    line_id: str = ""
    font_size: float = 0.0
    font_name: str | None = None

    def __post_init__(self) -> None:
        if not self.line_id:
            object.__setattr__(
                self,
                "line_id",
                visual_line_id(self.page_number, self.fragments),
            )


@dataclass(frozen=True, slots=True)
class RuleSegment:
    page_number: int
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def horizontal(self) -> bool:
        return abs(self.y1 - self.y0) <= 1.0 and abs(self.x1 - self.x0) > 0.0

    @property
    def vertical(self) -> bool:
        return abs(self.x1 - self.x0) <= 1.0 and abs(self.y1 - self.y0) > 0.0


@dataclass(frozen=True, slots=True)
class PageLines:
    page_number: int
    width: float
    height: float
    lines: tuple[VisualLine, ...]
    rules: tuple[RuleSegment, ...] = ()


@dataclass(frozen=True, slots=True)
class RecurringMargins:
    header_keys: frozenset[str]
    footer_keys: frozenset[str]
    minimum_occurrences: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "header_keys": sorted(self.header_keys),
            "footer_keys": sorted(self.footer_keys),
            "minimum_occurrences": self.minimum_occurrences,
        }


@dataclass(frozen=True, slots=True)
class RemovedLine:
    line: VisualLine
    reason: str


@dataclass(frozen=True, slots=True)
class CleanedPage:
    page_number: int
    width: float
    height: float
    retained: tuple[VisualLine, ...]
    removed: tuple[RemovedLine, ...]
    rules: tuple[RuleSegment, ...] = ()


@dataclass(frozen=True, slots=True)
class BodyFontProfile:
    body_font_size: float | None
    heading_threshold: float | None
    confidence: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "body_font_size": self.body_font_size,
            "heading_threshold": self.heading_threshold,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
        }


class ReadingOrderMode(StrEnum):
    TOP_TO_BOTTOM = "top_to_bottom"
    TWO_COLUMN = "two_column"


@dataclass(frozen=True, slots=True)
class PageOrderProfile:
    page_number: int
    mode: ReadingOrderMode
    split_x: float | None
    confidence: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "mode": self.mode.value,
            "split_x": self.split_x,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
        }


def _rounded_bbox(bbox: tuple[float, float, float, float]) -> list[float]:
    return [round(value, 3) for value in bbox]


def visual_line_id(page_number: int, fragments: Sequence[SourceFragment]) -> str:
    canonical = json.dumps(
        {
            "page_number": page_number,
            "fragments": [
                {
                    "bbox": _rounded_bbox(fragment.bbox),
                    "block_number": fragment.block_number,
                    "raw_text": fragment.raw_text,
                }
                for fragment in fragments
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "pdfline:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def structural_margin_key(text: str) -> str:
    normalized = re.sub(r"\d+", "#", text.casefold())
    normalized = re.sub(r"[^a-z#]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _is_top(line: VisualLine, height: float, fraction: float) -> bool:
    return height > 0.0 and line.bbox[1] <= height * fraction


def _is_bottom(line: VisualLine, height: float, fraction: float) -> bool:
    return height > 0.0 and line.bbox[3] >= height * (1.0 - fraction)


def detect_recurring_margins(
    pages: Sequence[PageLines],
    *,
    top_fraction: float = 0.10,
    bottom_fraction: float = 0.10,
    minimum_fraction: float = 0.40,
    minimum_pages: int = 2,
) -> RecurringMargins:
    if not 0.0 < top_fraction <= 0.5:
        raise ValueError("top_fraction must be within 0.0..0.5")
    if not 0.0 < bottom_fraction <= 0.5:
        raise ValueError("bottom_fraction must be within 0.0..0.5")
    if not 0.0 < minimum_fraction <= 1.0:
        raise ValueError("minimum_fraction must be within 0.0..1.0")
    if minimum_pages < 1:
        raise ValueError("minimum_pages must be positive")
    threshold = max(minimum_pages, math.ceil(len(pages) * minimum_fraction))
    header_counts: Counter[str] = Counter()
    footer_counts: Counter[str] = Counter()
    for page in pages:
        header_keys = {
            structural_margin_key(line.text)
            for line in page.lines
            if _is_top(line, page.height, top_fraction) and structural_margin_key(line.text)
        }
        footer_keys = {
            structural_margin_key(line.text)
            for line in page.lines
            if _is_bottom(line, page.height, bottom_fraction) and structural_margin_key(line.text)
        }
        header_counts.update(header_keys)
        footer_counts.update(footer_keys)
    return RecurringMargins(
        header_keys=frozenset(key for key, count in header_counts.items() if count >= threshold),
        footer_keys=frozenset(key for key, count in footer_counts.items() if count >= threshold),
        minimum_occurrences=threshold,
    )


def clean_recurring_margins(
    pages: Sequence[PageLines],
    margins: RecurringMargins,
    *,
    top_fraction: float = 0.10,
    bottom_fraction: float = 0.10,
) -> tuple[CleanedPage, ...]:
    cleaned: list[CleanedPage] = []
    for page in pages:
        retained: list[VisualLine] = []
        removed: list[RemovedLine] = []
        for line in page.lines:
            key = structural_margin_key(line.text)
            if key and _is_top(line, page.height, top_fraction) and key in margins.header_keys:
                removed.append(RemovedLine(line, "recurring_header"))
            elif key and _is_bottom(line, page.height, bottom_fraction) and key in margins.footer_keys:
                removed.append(RemovedLine(line, "recurring_footer"))
            else:
                retained.append(line)
        cleaned.append(CleanedPage(page.page_number, page.width, page.height, tuple(retained), tuple(removed), page.rules))
    return tuple(cleaned)


def estimate_body_font(pages: Sequence[CleanedPage]) -> BodyFontProfile:
    weighted: list[float] = []
    usable_lines = 0
    for page in pages:
        for line in page.retained:
            if line.font_size <= 0.0 or len(line.text.strip()) < 20:
                continue
            usable_lines += 1
            weighted.extend([line.font_size] * min(len(line.text), 200))
    if not weighted:
        return BodyFontProfile(None, None, 0.0, ("body_font_unknown",))
    body = round(float(statistics.median(weighted)), 3)
    threshold = round(body * 1.15, 3)
    confidence = round(min(0.95, 0.55 + min(usable_lines, 20) * 0.02), 3)
    return BodyFontProfile(body, threshold, confidence, (f"body_font:{body:.1f}", f"sample_lines:{usable_lines}"))


def _line_width(line: VisualLine) -> float:
    return max(0.0, line.bbox[2] - line.bbox[0])


def _is_full_width(line: VisualLine, page_width: float) -> bool:
    if page_width <= 0.0:
        return False
    center = page_width / 2.0
    return _line_width(line) >= page_width * 0.65 or (
        line.bbox[0] <= center - page_width * 0.10 and line.bbox[2] >= center + page_width * 0.10
    )


def _positive_start_gaps(lines: Sequence[VisualLine]) -> list[float]:
    starts = sorted({round(line.bbox[0], 3) for line in lines})
    return [right - left for left, right in zip(starts, starts[1:]) if right > left]


def infer_page_order(page: CleanedPage) -> PageOrderProfile:
    """Infer a conservative page-local reading-order mode."""

    geometric = [
        line
        for line in page.retained
        if line.text.strip() and _line_width(line) > 0.0
    ]
    sample = [line for line in geometric if not _is_full_width(line, page.width)]
    fallback = PageOrderProfile(
        page_number=page.page_number,
        mode=ReadingOrderMode.TOP_TO_BOTTOM,
        split_x=None,
        confidence=0.5 if geometric else 0.25,
        evidence=("top_to_bottom", f"sample_lines:{len(sample)}"),
    )
    if len(sample) < 4 or page.width <= 0.0:
        return fallback

    starts = sorted({round(line.bbox[0], 3) for line in sample})
    if len(starts) < 2:
        return fallback

    candidates: list[tuple[float, float, list[VisualLine], list[VisualLine], float]] = []
    for left_start, right_start in zip(starts, starts[1:]):
        start_gap = right_start - left_start
        if start_gap < max(60.0, page.width * 0.12):
            continue
        split = (left_start + right_start) / 2.0
        left = [line for line in sample if line.bbox[0] < split]
        right = [line for line in sample if line.bbox[0] >= split]
        if len(left) < 2 or len(right) < 2:
            continue

        left_min = min(line.bbox[1] for line in left)
        left_max = max(line.bbox[3] for line in left)
        right_min = min(line.bbox[1] for line in right)
        right_max = max(line.bbox[3] for line in right)
        heights = [max(0.1, line.bbox[3] - line.bbox[1]) for line in left + right]
        vertical_overlap = min(left_max, right_max) - max(left_min, right_min)
        if vertical_overlap < statistics.median(heights):
            continue

        left_center = statistics.median(line.bbox[0] for line in left)
        right_center = statistics.median(line.bbox[0] for line in right)
        if left_center >= page.width * 0.50 or right_center <= page.width * 0.45:
            continue

        internal_gaps = _positive_start_gaps(left) + _positive_start_gaps(right)
        ordinary_gap = statistics.median(internal_gaps) if internal_gaps else 0.0
        if ordinary_gap > 0.0 and start_gap <= ordinary_gap * 1.5:
            continue

        balance = min(len(left), len(right)) / max(len(left), len(right))
        score = start_gap / page.width + balance * 0.15
        candidates.append((score, split, left, right, start_gap))

    if not candidates:
        return fallback

    score, split, left, right, start_gap = max(candidates, key=lambda item: item[0])
    confidence = round(min(0.95, 0.62 + score), 3)
    rounded_split = round(split, 3)
    return PageOrderProfile(
        page_number=page.page_number,
        mode=ReadingOrderMode.TWO_COLUMN,
        split_x=rounded_split,
        confidence=confidence,
        evidence=(
            "two_column",
            f"left_lines:{len(left)}",
            f"right_lines:{len(right)}",
            f"start_gap:{start_gap:.1f}",
            f"split_x:{rounded_split:.1f}",
        ),
    )


def _top_sort(lines: Sequence[VisualLine]) -> list[VisualLine]:
    return sorted(lines, key=lambda line: (line.bbox[1], line.bbox[0], line.line_id))


def order_page_lines(page: CleanedPage, profile: PageOrderProfile) -> tuple[VisualLine, ...]:
    if profile.page_number != page.page_number:
        raise ValueError("page profile does not match cleaned page")
    if profile.mode is ReadingOrderMode.TOP_TO_BOTTOM:
        return tuple(_top_sort(page.retained))
    if profile.split_x is None:
        raise ValueError("two-column page profile requires split_x")
    split = profile.split_x
    full_width = [line for line in page.retained if _is_full_width(line, page.width)]
    left = [line for line in page.retained if line not in full_width and line.bbox[0] < split]
    right = [line for line in page.retained if line not in full_width and line.bbox[0] >= split]

    def center_y(line: VisualLine) -> float:
        return (line.bbox[1] + line.bbox[3]) / 2.0

    ordered: list[VisualLine] = []
    remaining_left = set(line.line_id for line in left)
    remaining_right = set(line.line_id for line in right)
    for separator in _top_sort(full_width):
        boundary = center_y(separator)
        left_band = [
            line
            for line in left
            if line.line_id in remaining_left and center_y(line) < boundary
        ]
        right_band = [
            line
            for line in right
            if line.line_id in remaining_right and center_y(line) < boundary
        ]
        ordered.extend(_top_sort(left_band))
        ordered.extend(_top_sort(right_band))
        remaining_left.difference_update(line.line_id for line in left_band)
        remaining_right.difference_update(line.line_id for line in right_band)
        ordered.append(separator)

    ordered.extend(
        _top_sort([line for line in left if line.line_id in remaining_left])
    )
    ordered.extend(
        _top_sort([line for line in right if line.line_id in remaining_right])
    )
    return tuple(ordered)
