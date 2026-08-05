"""IBC 2018 positioned-PDF extraction and chapter layout projection."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

from .models import CHAPTER_SPECS, ChapterLayout, ChapterLayoutAnalysis, IbcLayoutDocument, LogicalBlock
from .text import (
    _block_evidence,
    _extract_page_lines,
    _join_text,
    HyphenationLexicon,
    build_hyphenation_lexicon,
    _normalize_visual_text,
    _opening_commentary_indexes,
    _starts_new_block,
    _trim_opening_commentary,
    parse_chapter_numbers,
    repair_source_spacing,
)
from ..layout_analysis import BodyFontProfile, CleanedPage, RemovedLine, VisualLine, clean_recurring_margins, detect_recurring_margins, estimate_body_font, infer_page_order, order_page_lines as order_analyzed_page_lines
from ..layout_validation import validate_layout_projection
from ..table_geometry import TableCandidate, detect_ruled_tables


def coalesce_visual_lines(
    lines: Sequence[VisualLine],
    *,
    chapter_number: str,
    body_font: BodyFontProfile | None = None,
    trim_commentary: bool = True,
    hyphenation_lexicon: HyphenationLexicon | None = None,
) -> tuple[LogicalBlock, ...]:
    """Coalesce visual lines into source-mapped structural blocks."""

    retained = _trim_opening_commentary(lines) if trim_commentary else tuple(lines)
    lexicon = hyphenation_lexicon or build_hyphenation_lexicon(retained)
    blocks: list[LogicalBlock] = []
    current_lines: list[VisualLine] = []
    current_text = ""
    current_table = False
    previous_line: VisualLine | None = None

    def flush() -> None:
        nonlocal current_lines, current_text, current_table
        if current_text and current_lines:
            confidence, evidence = _block_evidence(
                current_lines,
                body_font,
                chapter_number,
            )
            blocks.append(
                LogicalBlock(
                    text=_normalize_visual_text(current_text),
                    fragments=tuple(
                        fragment for line in current_lines for fragment in line.fragments
                    ),
                    table_like=current_table,
                    source_line_ids=tuple(line.line_id for line in current_lines),
                    confidence=confidence,
                    evidence=evidence,
                )
            )
        current_lines = []
        current_text = ""
        current_table = False

    for line in retained:
        text = line.text
        starts = _starts_new_block(line, chapter_number, body_font)
        if current_text and current_text.endswith(("-", "‐")) and text[:1].isalpha():
            current_text = _join_text(current_text, text, lexicon)
            current_lines.append(line)
            previous_line = line
            continue
        if current_text and current_table and not starts:
            current_text = _join_text(current_text, text, lexicon)
            current_lines.append(line)
            previous_line = line
            continue
        if starts:
            flush()
            current_text = text
            current_lines = [line]
            current_table = text.startswith("TABLE ")
            previous_line = line
            continue

        gap = 0.0
        if previous_line and previous_line.page_number == line.page_number:
            gap = line.bbox[1] - previous_line.bbox[3]
        paragraph_break = (
            bool(current_text)
            and gap > 5.0
            and current_text.endswith((".", ":", ";"))
            and text[:1].isupper()
        )
        if paragraph_break:
            flush()
            current_text = text
            current_lines = [line]
        elif current_text:
            current_text = _join_text(current_text, text, lexicon)
            current_lines.append(line)
        else:
            current_text = text
            current_lines = [line]
        previous_line = line
    flush()
    return tuple(blocks)


def _remove_chapter_commentary(
    pages: Sequence[CleanedPage],
    ordered_lines: Sequence[VisualLine],
) -> tuple[tuple[CleanedPage, ...], tuple[VisualLine, ...]]:
    indexes = _opening_commentary_indexes(ordered_lines)
    chapter_index = next(
        (index for index, line in enumerate(ordered_lines) if line.text.startswith("CHAPTER ")),
        0,
    )
    keep_ids = {
        line.line_id
        for index, line in enumerate(ordered_lines)
        if index >= chapter_index and index not in indexes
    }
    commentary_ids = {
        line.line_id for index, line in enumerate(ordered_lines) if index in indexes
    }
    adjusted: list[CleanedPage] = []
    for page in pages:
        removed = list(page.removed)
        retained: list[VisualLine] = []
        for line in page.retained:
            if line.line_id in commentary_ids:
                removed.append(RemovedLine(line, "publisher_commentary"))
            elif line.line_id in keep_ids:
                retained.append(line)
            else:
                removed.append(RemovedLine(line, "before_chapter_anchor"))
        adjusted.append(
            CleanedPage(
                page.page_number,
                page.width,
                page.height,
                tuple(retained),
                tuple(removed),
                page.rules,
            )
        )
    retained_order = tuple(line for line in ordered_lines if line.line_id in keep_ids)
    return tuple(adjusted), retained_order


def _shift_table_after_heading(
    table: TableCandidate,
    heading: VisualLine,
) -> TableCandidate:
    shift = len(heading.text) + 1
    shifted_rows = tuple(
        replace(
            row,
            cells=tuple(
                replace(
                    cell,
                    local_start=cell.local_start + shift,
                    local_end=cell.local_end + shift,
                )
                for cell in row.cells
            ),
        )
        for row in table.rows
    )
    return replace(
        table,
        rows=shifted_rows,
        normalized_text=heading.text + "\n" + table.normalized_text,
        evidence=table.evidence + ("announced_table",),
    )


def _announced_ruled_tables(
    page: CleanedPage,
) -> tuple[tuple[TableCandidate, VisualLine], ...]:
    labels = sorted(
        (
            line
            for line in page.retained
            if re.match(r"^(?:\[[A-Z]{1,3}\]\s+)?TABLE\s+\d", line.text)
        ),
        key=lambda line: (line.bbox[1], line.bbox[0]),
    )
    if not labels:
        return ()
    output: list[tuple[TableCandidate, VisualLine]] = []
    used_labels: set[str] = set()
    for table in detect_ruled_tables(page):
        table_top = min(row.bbox[1] for row in table.rows)
        candidates = [
            label
            for label in labels
            if label.line_id not in used_labels
            and label.bbox[1] <= table_top
            and table_top - label.bbox[1] <= 80.0
        ]
        if not candidates:
            continue
        heading = max(candidates, key=lambda line: line.bbox[1])
        used_labels.add(heading.line_id)
        output.append((_shift_table_after_heading(table, heading), heading))
    return tuple(output)


def _table_blocks_in_order(
    ordered_lines: Sequence[VisualLine],
    tables: Sequence[tuple[TableCandidate, VisualLine]],
    *,
    chapter_number: str,
    body_font: BodyFontProfile,
    hyphenation_lexicon: HyphenationLexicon,
) -> tuple[LogicalBlock, ...]:
    table_by_line: dict[str, tuple[TableCandidate, VisualLine]] = {}
    for table, heading in tables:
        table_by_line[heading.line_id] = (table, heading)
        for row in table.rows:
            for line_id in row.source_line_ids:
                table_by_line[line_id] = (table, heading)
    emitted: set[int] = set()
    ordinary: list[VisualLine] = []
    output: list[LogicalBlock] = []

    def flush_ordinary() -> None:
        nonlocal ordinary
        if ordinary:
            output.extend(
                coalesce_visual_lines(
                    ordinary,
                    chapter_number=chapter_number,
                    body_font=body_font,
                    trim_commentary=False,
                    hyphenation_lexicon=hyphenation_lexicon,
                )
            )
            ordinary = []

    for line in ordered_lines:
        record = table_by_line.get(line.line_id)
        if record is None:
            ordinary.append(line)
            continue
        flush_ordinary()
        table, heading = record
        identity = id(table)
        if identity in emitted:
            continue
        emitted.add(identity)
        line_ids = tuple(
            dict.fromkeys(
                [heading.line_id]
                + [line_id for row in table.rows for line_id in row.source_line_ids]
            )
        )
        fragments = heading.fragments + tuple(
            fragment for row in table.rows for fragment in row.fragments
        )
        output.append(
            LogicalBlock(
                text=table.normalized_text,
                fragments=fragments,
                table_like=True,
                source_line_ids=line_ids,
                confidence=table.confidence,
                evidence=table.evidence,
                table=table,
            )
        )
    flush_ordinary()
    return tuple(output)


def extract_ibc2018_layout(
    path: Path | str,
    chapter_numbers: Iterable[str] = ("1", "2", "3"),
) -> IbcLayoutDocument:
    chapters = parse_chapter_numbers(chapter_numbers)
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyMuPDF is required for IBC PDF ingestion; install building-code-ast[ibc-pdf]"
        ) from exc
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        document = fitz.open(source)
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"unable to open PDF source: {source.name}") from exc
    try:
        if document.page_count < max(spec.end_page for spec in CHAPTER_SPECS.values()):
            raise ValueError("the supplied PDF is too short to match the supported IBC 2018 layout")
        extracted: list[ChapterLayout] = []
        for number in chapters:
            spec = CHAPTER_SPECS[number]
            raw_pages = tuple(
                _extract_page_lines(document[page_number - 1], page_number)
                for page_number in range(spec.start_page, spec.end_page + 1)
            )
            raw_pages = repair_source_spacing(raw_pages)
            margins = detect_recurring_margins(raw_pages)
            cleaned = clean_recurring_margins(raw_pages, margins)
            body_font = estimate_body_font(cleaned)
            profiles = tuple(infer_page_order(page) for page in cleaned)
            ordered_by_page = tuple(
                order_analyzed_page_lines(page, profile)
                for page, profile in zip(cleaned, profiles, strict=True)
            )
            ordered = tuple(line for page_lines in ordered_by_page for line in page_lines)
            cleaned, ordered = _remove_chapter_commentary(cleaned, ordered)

            tables = tuple(
                record
                for page in cleaned
                for record in _announced_ruled_tables(page)
            )
            hyphenation_lexicon = build_hyphenation_lexicon(ordered)
            blocks = _table_blocks_in_order(
                ordered,
                tables,
                chapter_number=number,
                body_font=body_font,
                hyphenation_lexicon=hyphenation_lexicon,
            )
            analysis = ChapterLayoutAnalysis(
                body_font=body_font,
                margins=margins,
                page_profiles=profiles,
                removed_lines=tuple(item for page in cleaned for item in page.removed),
            )
            chapter = ChapterLayout(spec, blocks, cleaned, analysis)
            validate_layout_projection(chapter)
            if not blocks or not blocks[0].text.startswith(f"CHAPTER {number}"):
                raise ValueError(
                    f"visible CHAPTER {number} anchor was not reconstructed at physical PDF page {spec.start_page}"
                )
            if not any(block.text.startswith("SECTION ") for block in blocks):
                raise ValueError(f"chapter {number} contains no reconstructed SECTION heading")
            extracted.append(chapter)
        return IbcLayoutDocument(source.name, document.page_count, tuple(extracted))
    finally:
        document.close()
