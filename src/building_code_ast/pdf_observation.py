"""Publication-neutral positioned-text and vector PDF observation.

This module converts PyMuPDF pages into source-faithful geometric records. It
contains no publication identity, locator grammar, authority role, or table
semantics. Downstream layout and publication adapters may interpret these
observations separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import statistics

from .ingest.layout_analysis import PageLines, RuleSegment, SourceFragment, VisualLine


_HORIZONTAL_DIRECTION = (1.0, 0.0)


def _bbox(value: object) -> tuple[float, float, float, float]:
    try:
        x0, y0, x1, y1 = value  # type: ignore[misc]
        return (float(x0), float(y0), float(x1), float(y1))
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0, 0.0)


def _direction(value: object) -> tuple[float, float]:
    try:
        x, y = value  # type: ignore[misc]
        return (float(x), float(y))
    except (TypeError, ValueError):
        return _HORIZONTAL_DIRECTION


@dataclass(frozen=True, slots=True)
class ObservedPdfSpan:
    span_id: str
    bbox: tuple[float, float, float, float]
    text: str
    font_name: str
    font_size: float
    flags: int


@dataclass(frozen=True, slots=True)
class ObservedPdfLine:
    line_id: str
    bbox: tuple[float, float, float, float]
    spans: tuple[ObservedPdfSpan, ...]
    direction: tuple[float, float] = _HORIZONTAL_DIRECTION

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)


@dataclass(frozen=True, slots=True)
class ObservedPdfBlock:
    page_number: int
    block_number: int
    block_id: str
    bbox: tuple[float, float, float, float]
    lines: tuple[ObservedPdfLine, ...]

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)


@dataclass(frozen=True, slots=True)
class ObservedPdfPage:
    page_number: int
    width: float
    height: float
    blocks: tuple[ObservedPdfBlock, ...]
    rules: tuple[RuleSegment, ...]

    def to_page_lines(self) -> PageLines:
        """Project observed evidence into the existing layout-analysis records.

        ``VisualLine`` keeps its established content-derived identifier rather
        than inheriting the extraction-coordinate ``line_id``. That preserves
        existing downstream layout and NEC measurement identity semantics while
        the observed record retains a stable page-local extraction identifier.
        """

        lines: list[VisualLine] = []
        for block in self.blocks:
            for line in block.lines:
                fragments = tuple(
                    SourceFragment(
                        page_number=self.page_number,
                        bbox=span.bbox,
                        block_number=block.block_number,
                        raw_text=span.text,
                        font_size=span.font_size,
                        font_name=span.font_name,
                    )
                    for span in line.spans
                    if span.text
                )
                if not fragments:
                    continue
                font_sizes = [item.font_size for item in fragments if item.font_size > 0.0]
                lines.append(
                    VisualLine(
                        page_number=self.page_number,
                        bbox=line.bbox,
                        text=line.text,
                        fragments=fragments,
                        font_size=float(statistics.median(font_sizes or [0.0])),
                        font_name=fragments[0].font_name,
                    )
                )
        return PageLines(
            page_number=self.page_number,
            width=self.width,
            height=self.height,
            lines=tuple(lines),
            rules=self.rules,
        )


def _observe_rules(page: object, *, page_number: int) -> tuple[RuleSegment, ...]:
    rules: list[RuleSegment] = []
    get_drawings = getattr(page, "get_drawings", None)
    if get_drawings is None:
        return ()
    for drawing in get_drawings():
        if not isinstance(drawing, dict):
            continue
        for item in drawing.get("items", ()):
            if not isinstance(item, (tuple, list)) or not item:
                continue
            kind = item[0]
            if kind == "l" and len(item) >= 3:
                start, end = item[1], item[2]
                rules.append(
                    RuleSegment(
                        page_number,
                        float(start.x),
                        float(start.y),
                        float(end.x),
                        float(end.y),
                    )
                )
            elif kind == "re" and len(item) >= 2:
                rect = item[1]
                x0, y0 = float(rect.x0), float(rect.y0)
                x1, y1 = float(rect.x1), float(rect.y1)
                rules.extend(
                    (
                        RuleSegment(page_number, x0, y0, x1, y0),
                        RuleSegment(page_number, x1, y0, x1, y1),
                        RuleSegment(page_number, x1, y1, x0, y1),
                        RuleSegment(page_number, x0, y1, x0, y0),
                    )
                )
    return tuple(rules)


def observe_pymupdf_page(page: object, *, page_number: int) -> ObservedPdfPage:
    """Observe one PyMuPDF page without assigning publication semantics."""

    if page_number < 1:
        raise ValueError("page_number must be positive")
    raw = page.get_text("dict", sort=False)
    blocks: list[ObservedPdfBlock] = []
    for raw_block in raw.get("blocks", ()):
        if not isinstance(raw_block, dict) or int(raw_block.get("type", 0)) != 0:
            continue
        block_number = int(raw_block.get("number", -1))
        if block_number < 0:
            continue
        block_id = f"p{page_number}:b{block_number}"
        lines: list[ObservedPdfLine] = []
        for line_index, raw_line in enumerate(raw_block.get("lines", ())):
            if not isinstance(raw_line, dict):
                continue
            spans: list[ObservedPdfSpan] = []
            for span_index, raw_span in enumerate(raw_line.get("spans", ())):
                if not isinstance(raw_span, dict):
                    continue
                spans.append(
                    ObservedPdfSpan(
                        span_id=f"{block_id}:l{line_index}:s{span_index}",
                        bbox=_bbox(raw_span.get("bbox", (0, 0, 0, 0))),
                        text=str(raw_span.get("text", "")),
                        font_name=str(raw_span.get("font", "")),
                        font_size=float(raw_span.get("size", 0.0)),
                        flags=int(raw_span.get("flags", 0)),
                    )
                )
            lines.append(
                ObservedPdfLine(
                    line_id=f"{block_id}:l{line_index}",
                    bbox=_bbox(raw_line.get("bbox", (0, 0, 0, 0))),
                    spans=tuple(spans),
                    direction=_direction(raw_line.get("dir", _HORIZONTAL_DIRECTION)),
                )
            )
        blocks.append(
            ObservedPdfBlock(
                page_number=page_number,
                block_number=block_number,
                block_id=block_id,
                bbox=_bbox(raw_block.get("bbox", (0, 0, 0, 0))),
                lines=tuple(lines),
            )
        )

    rect = getattr(page, "rect")
    return ObservedPdfPage(
        page_number=page_number,
        width=float(rect.width),
        height=float(rect.height),
        blocks=tuple(blocks),
        rules=_observe_rules(page, page_number=page_number),
    )


def observe_pdf_pages(
    path: Path | str,
    *,
    expected_page_count: int | None = None,
) -> tuple[ObservedPdfPage, ...]:
    """Observe all pages of one PDF through the publication-neutral adapter."""

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "PyMuPDF is required; install building-code-ast[pdf-inspection]"
        ) from exc

    with fitz.open(Path(path)) as document:
        page_count = int(document.page_count)
        if expected_page_count is not None and page_count != expected_page_count:
            raise ValueError(
                "observed PDF page count does not match expected factual page count: "
                f"expected {expected_page_count}, observed {page_count}"
            )
        return tuple(
            observe_pymupdf_page(document[index], page_number=index + 1)
            for index in range(page_count)
        )
