"""NDS 2018 exact-source layout evidence before publication-structure parsing.

This module binds the characterized NDS artifact to positioned PDF evidence,
coarse page roles, printed-page provenance, artifact/page-furniture removal, and
publication-neutral reading-order analysis. It deliberately does not recognize
chapters, sections, appendices, equations, tables, figures, or semantics.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Sequence

from ..evidence import AstSourceIdentity
from .layout_analysis import (
    CleanedPage,
    PageOrderProfile,
    SourceFragment,
    VisualLine,
    infer_page_order,
    order_page_lines,
    structural_margin_key,
)
from .pdf_layout import PdfBlock, PdfLayoutDocument, PdfPage, normalize_block_text


NDS_2018_SHA256 = "581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4"
NDS_2018_ARTIFACT_ID = "awc:nds"
NDS_2018_EDITION_ID = f"2018:pdf:sha256:{NDS_2018_SHA256}"
_NDS_PAGE_COUNT = 206
_NDS_PAGE_WIDTH = 612.0
_NDS_PAGE_HEIGHT = 783.0


class NdsPageRole(StrEnum):
    FRONT_UNNUMBERED = "front_unnumbered"
    FRONT_MATTER = "front_matter"
    NUMBERED_BODY = "numbered_body"
    TRAILING_MATTER = "trailing_matter"


@dataclass(frozen=True, slots=True)
class NdsRemovedBlock:
    block: PdfBlock
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"block": self.block.to_dict(), "reason": self.reason}


@dataclass(frozen=True, slots=True)
class NdsLayoutPage:
    page_number: int
    width: float
    height: float
    printed_page: str | None
    page_role: NdsPageRole
    reading_order: PageOrderProfile
    ordered_blocks: tuple[PdfBlock, ...]
    removed_blocks: tuple[NdsRemovedBlock, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "page_number": self.page_number,
            "width": round(self.width, 3),
            "height": round(self.height, 3),
            "printed_page": self.printed_page,
            "page_role": self.page_role.value,
            "reading_order": self.reading_order.to_dict(),
            "ordered_blocks": [block.to_dict() for block in self.ordered_blocks],
            "removed_blocks": [removed.to_dict() for removed in self.removed_blocks],
        }


@dataclass(frozen=True, slots=True)
class NdsLayoutDiagnostic:
    code: str
    message: str
    page_number: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "page_number": self.page_number,
        }


@dataclass(frozen=True, slots=True)
class NdsLayoutEvidence:
    ast_source: AstSourceIdentity
    file_name: str
    pages: tuple[NdsLayoutPage, ...]
    diagnostics: tuple[NdsLayoutDiagnostic, ...] = ()

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def to_dict(self) -> dict[str, object]:
        return {
            "ast_source": self.ast_source.to_dict(),
            "file_name": self.file_name,
            "page_count": self.page_count,
            "pages": [page.to_dict() for page in self.pages],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def _validate_page_number(page_number: int) -> None:
    if page_number < 1 or page_number > _NDS_PAGE_COUNT:
        raise ValueError(f"page number {page_number} is outside NDS 2018")


def nds2018_page_role(page_number: int) -> NdsPageRole:
    _validate_page_number(page_number)
    if page_number <= 3:
        return NdsPageRole.FRONT_UNNUMBERED
    if page_number <= 12:
        return NdsPageRole.FRONT_MATTER
    if page_number <= 204:
        return NdsPageRole.NUMBERED_BODY
    return NdsPageRole.TRAILING_MATTER


def nds2018_printed_page(page_number: int) -> str | None:
    _validate_page_number(page_number)
    front_labels = {
        4: "ii",
        5: "iii",
        6: "iv",
        7: "v",
        8: "vi",
        9: "vii",
        10: "viii",
        11: "ix",
        12: "x",
    }
    if page_number in front_labels:
        return front_labels[page_number]
    if 13 <= page_number <= 204:
        return str(page_number - 12)
    return None


def _margin_region(block: PdfBlock, page: PdfPage) -> str | None:
    x0, y0, x1, y1 = block.bbox
    if y1 <= page.height * 0.10:
        return "top"
    if y0 >= page.height * 0.90:
        return "bottom"
    if x1 <= page.width * 0.08:
        return "left"
    if x0 >= page.width * 0.92:
        return "right"
    return None


def _furniture_key(block: PdfBlock, page: PdfPage) -> str | None:
    region = _margin_region(block, page)
    key = structural_margin_key(block.text)
    if region is None or not key:
        return None
    return f"{region}:{key}"


def _recurring_furniture_keys(pages: Sequence[PdfPage]) -> frozenset[str]:
    if not pages:
        return frozenset()
    counts: Counter[str] = Counter()
    for page in pages:
        page_keys = {
            key
            for block in page.blocks
            if (key := _furniture_key(block, page)) is not None
        }
        counts.update(page_keys)
    threshold = max(2, math.ceil(len(pages) * 0.04))
    return frozenset(key for key, count in counts.items() if count >= threshold)


def _block_sort_key(block: PdfBlock) -> tuple[object, ...]:
    return (
        block.page_number,
        round(block.bbox[1], 3),
        round(block.bbox[0], 3),
        round(block.bbox[3], 3),
        round(block.bbox[2], 3),
        normalize_block_text(block.text),
        block.block_number,
    )


def _visual_line(block: PdfBlock) -> VisualLine:
    fragment = SourceFragment(
        page_number=block.page_number,
        bbox=block.bbox,
        block_number=block.block_number,
        raw_text=block.text,
    )
    return VisualLine(
        page_number=block.page_number,
        bbox=block.bbox,
        text=normalize_block_text(block.text),
        fragments=(fragment,),
    )


def _line_to_block(line: VisualLine) -> PdfBlock:
    fragment = line.fragments[0]
    return PdfBlock(
        page_number=fragment.page_number,
        bbox=fragment.bbox,
        text=fragment.raw_text,
        block_number=fragment.block_number,
    )


def analyze_nds2018_pages(pages: Sequence[PdfPage]) -> tuple[NdsLayoutPage, ...]:
    """Return deterministic page-local layout evidence without structural parsing."""

    ordered_pages = tuple(sorted(pages, key=lambda page: page.page_number))
    if len({page.page_number for page in ordered_pages}) != len(ordered_pages):
        raise ValueError("NDS 2018 page observations contain duplicate page numbers")
    for page in ordered_pages:
        _validate_page_number(page.page_number)

    furniture_keys = _recurring_furniture_keys(ordered_pages)
    result: list[NdsLayoutPage] = []
    for page in ordered_pages:
        retained: list[PdfBlock] = []
        removed: list[NdsRemovedBlock] = []
        for block in sorted(page.blocks, key=_block_sort_key):
            if not normalize_block_text(block.text):
                removed.append(NdsRemovedBlock(block, "empty_text"))
                continue
            key = _furniture_key(block, page)
            if key is not None and key in furniture_keys:
                region = key.split(":", 1)[0]
                removed.append(NdsRemovedBlock(block, f"recurring_{region}_furniture"))
            else:
                retained.append(block)

        lines = tuple(_visual_line(block) for block in retained)
        cleaned = CleanedPage(
            page_number=page.page_number,
            width=page.width,
            height=page.height,
            retained=lines,
            removed=(),
        )
        profile = infer_page_order(cleaned)
        ordered_blocks = tuple(_line_to_block(line) for line in order_page_lines(cleaned, profile))
        result.append(
            NdsLayoutPage(
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                printed_page=nds2018_printed_page(page.page_number),
                page_role=nds2018_page_role(page.page_number),
                reading_order=profile,
                ordered_blocks=ordered_blocks,
                removed_blocks=tuple(sorted(removed, key=lambda item: _block_sort_key(item.block))),
            )
        )
    return tuple(result)


def _validate_exact_layout_document(document: PdfLayoutDocument, ast_source: AstSourceIdentity) -> None:
    if ast_source.artifact_id != NDS_2018_ARTIFACT_ID or ast_source.edition_id != NDS_2018_EDITION_ID:
        raise ValueError("NDS 2018 layout evidence requires the exact registered source identity")
    if document.page_count != _NDS_PAGE_COUNT:
        raise ValueError(f"NDS 2018 exact layout requires {_NDS_PAGE_COUNT} PDF pages")
    expected_numbers = tuple(range(1, _NDS_PAGE_COUNT + 1))
    actual_numbers = tuple(page.page_number for page in document.pages)
    if actual_numbers != expected_numbers:
        raise ValueError("NDS 2018 exact layout requires contiguous one-based PDF pages")
    for page in document.pages:
        if abs(page.width - _NDS_PAGE_WIDTH) > 0.01 or abs(page.height - _NDS_PAGE_HEIGHT) > 0.01:
            raise ValueError("NDS 2018 exact layout requires 612 x 783 point pages")


def build_nds2018_layout_evidence(
    document: PdfLayoutDocument,
    *,
    ast_source: AstSourceIdentity,
) -> NdsLayoutEvidence:
    """Bind a complete characterized NDS PDF layout to exact source identity."""

    _validate_exact_layout_document(document, ast_source)
    diagnostics = tuple(
        NdsLayoutDiagnostic(
            code="nds-outline-target-invalid",
            message="PDF outline entry has no valid target page; retain as navigation diagnostic only.",
            page_number=item.page_number,
        )
        for item in document.outline
        if item.page_number < 1 or item.page_number > _NDS_PAGE_COUNT
    )
    return NdsLayoutEvidence(
        ast_source=ast_source,
        file_name=document.file_name,
        pages=analyze_nds2018_pages(document.pages),
        diagnostics=diagnostics,
    )
