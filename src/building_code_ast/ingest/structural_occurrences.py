"""Publication-neutral classification of repeated native structural locators.

This module classifies source observations only. It does not decide whether
repetition means a semantic continuation, duplicate extraction, or equivalent
publication-specific meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class LocatorOccurrencePattern(StrEnum):
    SINGLE = "single"
    ADJACENT_PAGES = "adjacent_pages"
    SAME_PAGE_DUPLICATE = "same_page_duplicate"
    DISCONTIGUOUS_PAGES = "discontiguous_pages"


@dataclass(frozen=True, slots=True)
class LocatorOccurrence:
    native_locator: str
    pdf_page: int
    source_order: int

    def __post_init__(self) -> None:
        if not self.native_locator.strip():
            raise ValueError("native_locator must not be empty")
        if self.pdf_page < 1:
            raise ValueError("pdf_page must be positive")
        if self.source_order < 0:
            raise ValueError("source_order must not be negative")


@dataclass(frozen=True, slots=True)
class LocatorOccurrenceGroup:
    native_locator: str
    occurrences: tuple[LocatorOccurrence, ...]
    pattern: LocatorOccurrencePattern

    @property
    def pages(self) -> tuple[int, ...]:
        return tuple(item.pdf_page for item in self.occurrences)


def group_locator_occurrences(
    occurrences: Iterable[LocatorOccurrence],
) -> tuple[LocatorOccurrenceGroup, ...]:
    """Group native locators without collapsing repeated source evidence.

    ``source_order`` is the caller's deterministic source coordinate. Input
    discovery order is ignored. Same-page duplicates and page gaps remain
    explicit classifications instead of being normalized into continuations.
    """

    material = tuple(occurrences)
    if len({item.source_order for item in material}) != len(material):
        raise ValueError("source_order values must be unique")

    grouped: dict[str, list[LocatorOccurrence]] = {}
    for occurrence in material:
        grouped.setdefault(occurrence.native_locator, []).append(occurrence)

    result: list[LocatorOccurrenceGroup] = []
    for native_locator, items in grouped.items():
        ordered = tuple(
            sorted(
                items,
                key=lambda item: (
                    item.source_order,
                    item.pdf_page,
                    item.native_locator,
                ),
            )
        )
        pages = tuple(item.pdf_page for item in ordered)
        if len(ordered) == 1:
            pattern = LocatorOccurrencePattern.SINGLE
        elif len(set(pages)) != len(pages):
            pattern = LocatorOccurrencePattern.SAME_PAGE_DUPLICATE
        elif all(right == left + 1 for left, right in zip(pages, pages[1:])):
            pattern = LocatorOccurrencePattern.ADJACENT_PAGES
        else:
            pattern = LocatorOccurrencePattern.DISCONTIGUOUS_PAGES
        result.append(
            LocatorOccurrenceGroup(
                native_locator=native_locator,
                occurrences=ordered,
                pattern=pattern,
            )
        )

    return tuple(
        sorted(
            result,
            key=lambda group: (
                group.occurrences[0].source_order,
                group.native_locator,
            ),
        )
    )
