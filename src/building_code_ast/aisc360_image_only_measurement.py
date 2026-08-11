"""Source-safe classification of pages that have no embedded text layer.

This module deliberately classifies page-surface observations only. It does not
perform OCR, infer document hierarchy, or interpret source content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


_FULL_PAGE_IMAGE_COVERAGE = 0.999


@dataclass(frozen=True, slots=True)
class PageSurfaceObservation:
    """Non-reconstructive page facts used to classify image-only pages."""

    page_number: int
    has_embedded_text: bool
    image_placement_count: int
    maximum_image_coverage_ratio: float

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.image_placement_count < 0:
            raise ValueError("image_placement_count must be non-negative")
        if not 0.0 <= self.maximum_image_coverage_ratio <= 1.0001:
            raise ValueError("maximum_image_coverage_ratio must be a page-area ratio")


def _contiguous_runs(page_numbers: Sequence[int]) -> list[list[int]]:
    if not page_numbers:
        return []
    runs: list[list[int]] = []
    first = previous = page_numbers[0]
    for page_number in page_numbers[1:]:
        if page_number == previous + 1:
            previous = page_number
            continue
        runs.append([first, previous])
        first = previous = page_number
    runs.append([first, previous])
    return runs


def summarize_image_only_pages(
    observations: Sequence[PageSurfaceObservation],
) -> dict[str, object]:
    """Return deterministic source-safe facts about pages without embedded text.

    Observations must cover one contiguous one-based page sequence exactly once.
    A page is part of the image-only family whenever it has no embedded text.
    The aggregate ``all_image_only_pages_are_single_full_page_images`` claim is
    true only when every such page has exactly one image placement whose area is
    at least 99.9% of the page area.
    """

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    expected_pages = tuple(range(1, len(ordered) + 1))
    observed_pages = tuple(item.page_number for item in ordered)
    if observed_pages != expected_pages:
        raise ValueError("observations must cover each one-based page exactly once")

    image_only = tuple(item for item in ordered if not item.has_embedded_text)
    image_only_pages = [item.page_number for item in image_only]
    runs = _contiguous_runs(image_only_pages)
    maximum_run_length = max((last - first + 1 for first, last in runs), default=0)

    all_single_full_page = all(
        item.image_placement_count == 1
        and item.maximum_image_coverage_ratio >= _FULL_PAGE_IMAGE_COVERAGE
        for item in image_only
    )

    return {
        "page_count": len(ordered),
        "pages_with_embedded_text": len(ordered) - len(image_only),
        "image_only_page_count": len(image_only),
        "image_only_pages": image_only_pages,
        "image_only_run_count": len(runs),
        "maximum_image_only_run_length": maximum_run_length,
        "all_image_only_pages_are_single_full_page_images": all_single_full_page,
        "full_page_image_minimum_coverage_ratio": _FULL_PAGE_IMAGE_COVERAGE,
        "image_only_runs": runs,
    }
