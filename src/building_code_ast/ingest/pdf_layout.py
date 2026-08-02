"""Coordinate-aware PDF layout extraction with an optional PyMuPDF adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


_BROKEN_WORD_RE = re.compile(r"(?<=[A-Za-z])[\u00ad\u2010-]\n(?=[a-z])")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class PdfBlock:
    """One text block extracted from one PDF page.

    Page numbers are one-based. Bounding boxes use PDF points in
    ``(x0, y0, x1, y1)`` order.
    """

    page_number: int
    bbox: tuple[float, float, float, float]
    text: str
    block_number: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "page_number": self.page_number,
            "bbox": [round(value, 3) for value in self.bbox],
            "text": self.text,
            "block_number": self.block_number,
        }


@dataclass(frozen=True, slots=True)
class PdfOutlineItem:
    level: int
    title: str
    page_number: int


@dataclass(frozen=True, slots=True)
class PdfPage:
    page_number: int
    width: float
    height: float
    blocks: tuple[PdfBlock, ...]


@dataclass(frozen=True, slots=True)
class PdfLayoutDocument:
    file_name: str
    pages: tuple[PdfPage, ...]
    outline: tuple[PdfOutlineItem, ...]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page(self, page_number: int) -> PdfPage:
        if page_number < 1 or page_number > self.page_count:
            raise ValueError(f"page number {page_number} is outside the document")
        return self.pages[page_number - 1]


def normalize_block_text(text: str) -> str:
    """Return deterministic reading text for one extracted PDF block."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _BROKEN_WORD_RE.sub("", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def order_content_blocks(
    blocks: Iterable[PdfBlock],
    page_width: float,
    *,
    top_content_y: float = 65.0,
    bottom_content_y: float = 730.0,
) -> tuple[PdfBlock, ...]:
    """Filter recurring headers/footers and return two-column reading order."""

    midpoint = page_width / 2.0
    retained = [
        block
        for block in blocks
        if block.text.strip()
        and block.bbox[1] >= top_content_y
        and block.bbox[3] <= bottom_content_y
    ]

    def sort_key(block: PdfBlock) -> tuple[int, float, float, int]:
        x0, y0, x1, _ = block.bbox
        if x0 < midpoint and x1 > midpoint:
            column = 0
        elif x0 < midpoint:
            column = 1
        else:
            column = 2
        return (column, y0, x0, block.block_number)

    return tuple(sorted(retained, key=sort_key))


def extract_pdf_layout(path: Path | str) -> PdfLayoutDocument:
    """Extract PDF pages, text blocks, and outline through PyMuPDF.

    PyMuPDF is intentionally optional so importing the core package retains an
    empty dependency set.
    """

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised without optional extra
        raise RuntimeError(
            "PyMuPDF is required for PDF ingestion; install "
            "building-code-ast[nec-pdf]"
        ) from exc

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)

    try:
        document = fitz.open(source)
    except Exception as exc:  # pragma: no cover - delegated parser failure
        raise ValueError(f"unable to open PDF source: {source.name}") from exc

    try:
        pages: list[PdfPage] = []
        for page_index in range(document.page_count):
            page = document[page_index]
            blocks: list[PdfBlock] = []
            for block in page.get_text("blocks", sort=False):
                x0, y0, x1, y1, text = block[:5]
                block_number = int(block[5]) if len(block) > 5 else len(blocks)
                block_type = int(block[6]) if len(block) > 6 else 0
                if block_type != 0:
                    continue
                blocks.append(
                    PdfBlock(
                        page_number=page_index + 1,
                        bbox=(float(x0), float(y0), float(x1), float(y1)),
                        text=str(text),
                        block_number=block_number,
                    )
                )
            pages.append(
                PdfPage(
                    page_number=page_index + 1,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    blocks=tuple(blocks),
                )
            )

        outline = tuple(
            PdfOutlineItem(level=int(level), title=str(title), page_number=int(page_number))
            for level, title, page_number in document.get_toc(simple=True)
        )
        return PdfLayoutDocument(
            file_name=source.name,
            pages=tuple(pages),
            outline=outline,
        )
    finally:
        document.close()
