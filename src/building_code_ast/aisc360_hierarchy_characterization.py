"""Source-safe hierarchy characterization for ANSI/AISC 360-16.

This module measures structural anchors visible in embedded text and records
explicit raster-page evidence without retaining protected source prose.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence


_CHAPTER_RE = re.compile(r"^CHAPTER\s*([A-N])$")
_APPENDIX_RE = re.compile(r"^APPENDIX\s*([0-9]+)$")


@dataclass(frozen=True, slots=True)
class HierarchyPageObservation:
    """One page's hierarchy-relevant, non-persistent source observation."""

    page_number: int
    embedded_text: str | None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.embedded_text is not None and not self.embedded_text:
            raise ValueError("embedded_text must be non-empty or None")


def characterize_hierarchy(
    observations: Sequence[HierarchyPageObservation],
    *,
    raster_hierarchy_pages: Sequence[int] = (),
) -> dict[str, object]:
    """Return deterministic structural measurements without retaining source prose.

    ``raster_hierarchy_pages`` contains pages independently observed to carry
    hierarchy-bearing raster content. Such pages must be image-only in the
    supplied observations. Their presence makes embedded-text-only hierarchy
    replay explicitly incomplete.
    """

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    expected = tuple(range(1, len(ordered) + 1))
    if tuple(item.page_number for item in ordered) != expected:
        raise ValueError("observations must cover each one-based page exactly once")

    image_only_pages = {
        item.page_number for item in ordered if item.embedded_text is None
    }
    raster_pages = tuple(sorted(set(raster_hierarchy_pages)))
    if any(page not in image_only_pages for page in raster_pages):
        raise ValueError("raster hierarchy evidence must reference image-only pages")

    chapters: list[dict[str, object]] = []
    appendices: list[dict[str, object]] = []
    for item in ordered:
        if item.embedded_text is None:
            continue
        for raw_line in item.embedded_text.splitlines():
            line = " ".join(raw_line.strip().upper().split())
            chapter = _CHAPTER_RE.fullmatch(line)
            if chapter:
                chapters.append({"page": item.page_number, "identifier": chapter.group(1)})
                continue
            appendix = _APPENDIX_RE.fullmatch(line.replace(" ", ""))
            if appendix:
                appendices.append(
                    {"page": item.page_number, "identifier": int(appendix.group(1))}
                )

    return {
        "page_count": len(ordered),
        "embedded_text_page_count": len(ordered) - len(image_only_pages),
        "image_only_page_count": len(image_only_pages),
        "chapter_anchors": chapters,
        "appendix_anchors": appendices,
        "raster_hierarchy_pages": list(raster_pages),
        "embedded_text_only_hierarchy_complete": not bool(raster_pages),
        "next_parser_boundary": (
            "raster_text_recovery_before_hierarchy_parse"
            if raster_pages
            else "embedded_text_hierarchy_parse"
        ),
    }
