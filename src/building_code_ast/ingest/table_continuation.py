"""Publication-neutral classification of explicit table continuation evidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TableCaptionOccurrence:
    occurrence_id: str
    native_locator: str
    page_number: int
    explicit_continuation: bool


@dataclass(frozen=True, slots=True)
class TableContinuationClassification:
    resolved_links: tuple[tuple[str, str], ...]
    unresolved_repeated_occurrence_ids: tuple[str, ...]
    orphan_explicit_continuation_ids: tuple[str, ...]


def classify_table_continuations(
    occurrences: tuple[TableCaptionOccurrence, ...],
) -> TableContinuationClassification:
    """Classify continuation evidence without inferring from repetition alone.

    Within each native locator family, an explicitly marked continuation links
    to the immediately preceding occurrence. A later repeated occurrence with
    no explicit continuation marker remains unresolved. An explicit marker with
    no prior same-locator occurrence is preserved as orphan evidence.
    """

    ids = [occurrence.occurrence_id for occurrence in occurrences]
    if len(ids) != len(set(ids)):
        raise ValueError("occurrence ids must be unique")
    if any(occurrence.page_number < 1 for occurrence in occurrences):
        raise ValueError("page numbers must be positive")
    if any(not occurrence.native_locator for occurrence in occurrences):
        raise ValueError("native locators must be non-empty")

    by_locator: dict[str, list[TableCaptionOccurrence]] = {}
    for occurrence in occurrences:
        by_locator.setdefault(occurrence.native_locator, []).append(occurrence)

    resolved: list[tuple[str, str]] = []
    unresolved: list[str] = []
    orphan: list[str] = []

    for locator in sorted(by_locator):
        family = sorted(
            by_locator[locator],
            key=lambda item: (item.page_number, item.occurrence_id),
        )
        previous: TableCaptionOccurrence | None = None
        for occurrence in family:
            if previous is None:
                if occurrence.explicit_continuation:
                    orphan.append(occurrence.occurrence_id)
            elif occurrence.explicit_continuation:
                resolved.append((previous.occurrence_id, occurrence.occurrence_id))
            else:
                unresolved.append(occurrence.occurrence_id)
            previous = occurrence

    return TableContinuationClassification(
        resolved_links=tuple(resolved),
        unresolved_repeated_occurrence_ids=tuple(unresolved),
        orphan_explicit_continuation_ids=tuple(orphan),
    )
