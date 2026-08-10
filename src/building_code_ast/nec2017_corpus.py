"""Source-safe whole-publication measurement for the retained NEC 2017 artifact.

This module measures the behavior of the existing NEC structural classifier. It
does not add recognition rules or claim semantic, reviewed, or structural
completeness.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .ingest.nec2017 import (
    _announced_table_regions,
    _classify_block,
    discover_article_ranges,
    select_article_blocks,
)
from .ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfOutlineItem, normalize_block_text


MEASUREMENT_VERSION = "0.1.0"
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_NUMERIC_ARTICLE_RE = re.compile(r"^\s*(?P<number>\d{2,3})\s+\S")
_CHAPTER_RE = re.compile(r"^Chapter\s+\d+\b", re.IGNORECASE)
_ANNEX_RE = re.compile(r"^Informative\s+Annex\s+[A-Z]\b", re.IGNORECASE)
_INDEX_RE = re.compile(r"^Index\s*$", re.IGNORECASE)


def _outline_kind(title: str) -> str | None:
    normalized = " ".join(title.split())
    if _CHAPTER_RE.match(normalized):
        return "chapter"
    if _ANNEX_RE.match(normalized):
        return "informative_annex"
    if _INDEX_RE.match(normalized):
        return "index"
    return None


def _article_outline_positions(layout: PdfLayoutDocument) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, item in enumerate(layout.outline):
        match = _NUMERIC_ARTICLE_RE.match(" ".join(item.title.split()))
        if match is not None and match.group("number") not in result:
            result[match.group("number")] = index
    return result


def _next_structural_outline(
    layout: PdfLayoutDocument,
    *,
    article_number: str,
    article_positions: dict[str, int],
) -> PdfOutlineItem | None:
    position = article_positions.get(article_number)
    if position is None:
        return None
    article_item = layout.outline[position]
    for item in layout.outline[position + 1 :]:
        if item.level > article_item.level:
            continue
        if _NUMERIC_ARTICLE_RE.match(" ".join(item.title.split())) is not None:
            return None
        if _outline_kind(item.title) is not None:
            return item
    return None


def _successor_anchor(kind: str, text: str) -> bool:
    if kind == "chapter":
        return _CHAPTER_RE.match(text) is not None
    if kind == "informative_annex":
        return _ANNEX_RE.match(text) is not None
    if kind == "index":
        return _INDEX_RE.match(text) is not None
    return False


def _contains_successor_material(
    blocks: tuple[PdfBlock, ...],
    successor: PdfOutlineItem,
    kind: str,
) -> bool:
    for block in blocks:
        if block.page_number > successor.page_number:
            return True
        if (
            block.page_number == successor.page_number
            and _successor_anchor(kind, normalize_block_text(block.text))
        ):
            return True
    return False


def _trim_at_successor(
    blocks: tuple[PdfBlock, ...],
    successor: PdfOutlineItem,
    kind: str,
) -> tuple[PdfBlock, ...]:
    retained: list[PdfBlock] = []
    for block in blocks:
        if block.page_number > successor.page_number:
            break
        text = normalize_block_text(block.text)
        if block.page_number == successor.page_number and _successor_anchor(kind, text):
            break
        retained.append(block)
    return tuple(retained)


def measure_nec2017_corpus(
    layout: PdfLayoutDocument,
    *,
    source_sha256: str,
    source_size: int,
) -> dict[str, Any]:
    """Measure current NEC structural behavior without retaining source expression."""

    digest = source_sha256.lower()
    if _HEX_64_RE.fullmatch(digest) is None:
        raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
    if source_size <= 0:
        raise ValueError("source_size must be positive")

    ranges = discover_article_ranges(layout)
    positions = _article_outline_positions(layout)
    classifier_counts: Counter[str] = Counter()
    boundary_issues: list[dict[str, Any]] = []
    selection_failures = 0
    retained_blocks = 0

    for article_range in ranges:
        try:
            blocks = select_article_blocks(layout, article_range.number)
        except ValueError:
            selection_failures += 1
            continue

        successor = _next_structural_outline(
            layout,
            article_number=article_range.number,
            article_positions=positions,
        )
        if successor is not None and successor.page_number <= article_range.scan_end_page:
            kind = _outline_kind(successor.title)
            if kind is not None and _contains_successor_material(blocks, successor, kind):
                boundary_issues.append(
                    {
                        "article_number": article_range.number,
                        "current_scan_end_page": article_range.scan_end_page,
                        "next_outline_page": successor.page_number,
                        "next_outline_kind": kind,
                    }
                )
                blocks = _trim_at_successor(blocks, successor, kind)

        announced = _announced_table_regions(blocks)
        for block in blocks:
            text = normalize_block_text(block.text)
            region_key = (
                None
                if block.table_region_id is None
                else (block.page_number, block.table_region_id)
            )
            node_type, _, _, _ = _classify_block(
                article_range.number,
                text,
                block,
                announced_table_region=region_key in announced,
            )
            classifier_counts[node_type.value] += 1
            retained_blocks += 1

    chapter_count = sum(1 for item in layout.outline if _outline_kind(item.title) == "chapter")
    annex_count = sum(
        1 for item in layout.outline if _outline_kind(item.title) == "informative_annex"
    )
    unsupported = classifier_counts.get("unsupported", 0)
    serialized_counts = dict(sorted(classifier_counts.items()))
    serialized_counts.setdefault("unsupported", 0)

    return {
        "measurement_version": MEASUREMENT_VERSION,
        "source": {
            "file_name": layout.file_name,
            "sha256": digest,
            "size_bytes": source_size,
            "page_count": layout.page_count,
        },
        "outline_counts": {
            "numeric_articles": len(ranges),
            "chapters": chapter_count,
            "informative_annexes": annex_count,
        },
        "article_counts": {
            "observed": len(ranges),
            "selection_failures": selection_failures,
            "boundary_issues": len(boundary_issues),
        },
        "source_block_count": retained_blocks,
        "classifier_counts": serialized_counts,
        "status_counts": {
            "recognized": retained_blocks - unsupported,
            "unsupported": unsupported,
            "ambiguous": None,
        },
        "boundary_issues": boundary_issues,
        "limitations": [
            "ambiguous structural state is not exposed by the current NEC block classifier",
            "counts describe structural observations and classifier behavior, not semantic or reviewed coverage",
        ],
    }
