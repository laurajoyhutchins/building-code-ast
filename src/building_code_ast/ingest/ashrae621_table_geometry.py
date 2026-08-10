"""Source-safe ASHRAE 62.1 table-geometry conformance measurement.

This module measures the geometric candidate evidence already retained by the
shared PDF layout adapter. It deliberately does not choose a candidate region,
reconstruct table cells, or assign table semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .pdf_layout import PdfLayoutDocument, normalize_block_text


_TABLE_RE = re.compile(
    r"^Table\s+(?P<locator>[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Ashrae621TableGeometryOccurrence:
    native_locator: str
    page_number: int
    block_number: int
    page_region_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "native_locator": self.native_locator,
            "page_number": self.page_number,
            "block_number": self.block_number,
            "page_region_count": self.page_region_count,
        }


@dataclass(frozen=True, slots=True)
class Ashrae621TableGeometryMeasurement:
    occurrences: tuple[Ashrae621TableGeometryOccurrence, ...]
    caption_occurrence_count: int
    native_identifier_count: int
    caption_page_count: int
    pages_with_region_evidence: int
    pages_without_region_evidence: tuple[int, ...]
    retained_region_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "caption_occurrence_count": self.caption_occurrence_count,
            "native_identifier_count": self.native_identifier_count,
            "caption_page_count": self.caption_page_count,
            "pages_with_region_evidence": self.pages_with_region_evidence,
            "pages_without_region_evidence": list(self.pages_without_region_evidence),
            "retained_region_count": self.retained_region_count,
            "occurrences": [occurrence.to_dict() for occurrence in self.occurrences],
        }


def measure_ashrae621_table_geometry(
    document: PdfLayoutDocument,
) -> Ashrae621TableGeometryMeasurement:
    """Measure retained table-region evidence without selecting table meaning."""

    caption_records: list[tuple[str, int, int]] = []
    page_region_counts: dict[int, int] = {}

    for page in document.pages:
        region_ids = {
            block.table_region_id
            for block in page.blocks
            if block.table_region_id is not None
        }
        page_region_counts[page.page_number] = len(region_ids)
        for block in page.blocks:
            match = _TABLE_RE.match(normalize_block_text(block.text))
            if match is None:
                continue
            caption_records.append(
                (match.group("locator"), page.page_number, block.block_number)
            )

    caption_records.sort(key=lambda item: (item[1], item[2], item[0]))
    caption_pages = tuple(sorted({item[1] for item in caption_records}))
    occurrences = tuple(
        Ashrae621TableGeometryOccurrence(
            native_locator=locator,
            page_number=page_number,
            block_number=block_number,
            page_region_count=page_region_counts.get(page_number, 0),
        )
        for locator, page_number, block_number in caption_records
    )
    pages_without = tuple(
        page_number
        for page_number in caption_pages
        if page_region_counts.get(page_number, 0) == 0
    )

    return Ashrae621TableGeometryMeasurement(
        occurrences=occurrences,
        caption_occurrence_count=len(occurrences),
        native_identifier_count=len({item.native_locator for item in occurrences}),
        caption_page_count=len(caption_pages),
        pages_with_region_evidence=len(caption_pages) - len(pages_without),
        pages_without_region_evidence=pages_without,
        retained_region_count=sum(page_region_counts.get(page_number, 0) for page_number in caption_pages),
    )
