"""Coordinate-aware PDF layout extraction with an optional PyMuPDF adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from ..pdf_observation import ObservedPdfPage, observe_pymupdf_page


_BROKEN_WORD_RE = re.compile(r"(?<=[A-Za-z])[\u00ad\u2010-]\n(?=[a-z])")
_WHITESPACE_RE = re.compile(r"\s+")
_TABLE_ANNOUNCEMENT_RE = re.compile(r"^\s*Table\s+(?:\d|[A-Z]+-\d)", re.IGNORECASE)
_HORIZONTAL_DIRECTION = (1.0, 0.0)


@dataclass(frozen=True, slots=True)
class PdfSpan:
    """One source text span within a PDF visual line."""

    bbox: tuple[float, float, float, float]
    text: str
    font: str
    size: float
    flags: int

    def to_dict(self) -> dict[str, object]:
        return {
            "bbox": [round(value, 3) for value in self.bbox],
            "text": self.text,
            "font": self.font,
            "size": round(self.size, 3),
            "flags": self.flags,
        }


@dataclass(frozen=True, slots=True)
class PdfLine:
    """One visual text line with ordered source spans and writing direction."""

    bbox: tuple[float, float, float, float]
    spans: tuple[PdfSpan, ...]
    direction: tuple[float, float] = _HORIZONTAL_DIRECTION

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "bbox": [round(value, 3) for value in self.bbox],
            "spans": [span.to_dict() for span in self.spans],
        }
        if self.direction != _HORIZONTAL_DIRECTION:
            payload["direction"] = [round(value, 6) for value in self.direction]
        return payload


@dataclass(frozen=True, slots=True)
class PdfBlock:
    """One text block extracted from one PDF page.

    Page numbers are one-based. Bounding boxes use PDF points in
    ``(x0, y0, x1, y1)`` order. ``table_region_id`` is page-local geometric
    evidence only; it does not assign table semantics to the block. ``lines``
    retains optional visual-line/font evidence without replacing ``text``.
    """

    page_number: int
    bbox: tuple[float, float, float, float]
    text: str
    block_number: int = 0
    table_region_id: int | None = None
    lines: tuple[PdfLine, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "page_number": self.page_number,
            "bbox": [round(value, 3) for value in self.bbox],
            "text": self.text,
            "block_number": self.block_number,
        }
        if self.table_region_id is not None:
            payload["table_region_id"] = self.table_region_id
        if self.lines:
            payload["lines"] = [line.to_dict() for line in self.lines]
        return payload


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


def _table_region_bboxes(page: object, block_texts: Iterable[str]) -> tuple[tuple[float, float, float, float], ...]:
    """Return page-local geometric table candidates when a table is announced.

    Detection is intentionally gated by visible table-announcement text so the
    legacy layout adapter does not run a table finder on every page or promote
    unannounced geometric coincidences into structural evidence.
    """

    if not any(_TABLE_ANNOUNCEMENT_RE.match(normalize_block_text(text)) for text in block_texts):
        return ()
    finder = getattr(page, "find_tables", None)
    if finder is None:
        return ()
    found = finder()
    tables = getattr(found, "tables", ())
    return tuple(
        tuple(float(value) for value in table.bbox)
        for table in tables
    )


def _table_region_id(
    bbox: tuple[float, float, float, float],
    regions: tuple[tuple[float, float, float, float], ...],
) -> int | None:
    """Return the one-based candidate region containing a block center."""

    center_x = (bbox[0] + bbox[2]) / 2.0
    center_y = (bbox[1] + bbox[3]) / 2.0
    for index, (x0, y0, x1, y1) in enumerate(regions, start=1):
        if x0 <= center_x <= x1 and y0 <= center_y <= y1:
            return index
    return None


def _line_evidence_by_block(page: ObservedPdfPage) -> dict[int, tuple[PdfLine, ...]]:
    """Project shared positioned-text observations into the legacy layout shape."""

    result: dict[int, tuple[PdfLine, ...]] = {}
    for block in page.blocks:
        lines = tuple(
            PdfLine(
                bbox=line.bbox,
                spans=tuple(
                    PdfSpan(
                        bbox=span.bbox,
                        text=span.text,
                        font=span.font_name,
                        size=span.font_size,
                        flags=span.flags,
                    )
                    for span in line.spans
                ),
                direction=line.direction,
            )
            for line in block.lines
        )
        result[block.block_number] = lines
    return result


def extract_pdf_layout(path: Path | str) -> PdfLayoutDocument:
    """Extract PDF pages, text blocks, outline, and bounded table geometry.

    PyMuPDF is intentionally optional so importing the core package retains an
    empty dependency set. Table-region IDs are geometric candidates only and
    do not imply header roles, cell semantics, or rule interpretation. Visual
    line/span evidence is projected from the publication-neutral PDF observer;
    legacy block text remains additive and unchanged.
    """

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised without optional extra
        raise RuntimeError(
            "PyMuPDF is required for PDF layout extraction; install "
            "building-code-ast[pdf-inspection]"
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
            page_number = page_index + 1
            page = document[page_index]
            raw_blocks = tuple(page.get_text("blocks", sort=False))
            observed_page = observe_pymupdf_page(page, page_number=page_number)
            line_evidence = _line_evidence_by_block(observed_page)
            table_regions = _table_region_bboxes(
                page,
                (str(block[4]) for block in raw_blocks if len(block) > 4),
            )
            blocks: list[PdfBlock] = []
            for block in raw_blocks:
                x0, y0, x1, y1, text = block[:5]
                block_number = int(block[5]) if len(block) > 5 else len(blocks)
                block_type = int(block[6]) if len(block) > 6 else 0
                if block_type != 0:
                    continue
                bbox = (float(x0), float(y0), float(x1), float(y1))
                blocks.append(
                    PdfBlock(
                        page_number=page_number,
                        bbox=bbox,
                        text=str(text),
                        block_number=block_number,
                        table_region_id=_table_region_id(bbox, table_regions),
                        lines=line_evidence.get(block_number, ()),
                    )
                )
            pages.append(
                PdfPage(
                    page_number=page_number,
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
