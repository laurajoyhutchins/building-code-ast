#!/usr/bin/env python3
"""Build a local, source-linked NFPA 13 (2019) AST bundle.

The source PDF and generated text-bearing output remain local. The public tool
contains deterministic extraction, diagnostics, and validation only.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence

try:
    import fitz  # type: ignore[import-untyped]
except ModuleNotFoundError:
    fitz = None  # type: ignore[assignment]

ARTIFACT_ID = "nfpa:13"
EDITION_ID = "2019"
BUNDLE_SCHEMA = "nfpa13-ast-bundle/0.1.0"
DOCUMENT_AST_VERSION = "0.1.0"
EXPECTED_SOURCE_SHA256 = "07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5"

LOCATOR_PATTERN = r"(?:[A-F]\.)?\d+(?:\.\d+)*"
OBJECT_LOCATOR_PATTERN = LOCATOR_PATTERN + r"(?:\([A-Za-z0-9]+\))?"
CLAUSE_AT_START_RE = re.compile(rf"^\s*(?P<locator>{LOCATOR_PATTERN})(?P<star>\*)?(?=\s|\(|$)")
CONTAINER_RE = re.compile(r"^\s*(?:Chapter\s+(?P<chapter>\d+)|Annex\s+(?P<annex>[A-F]))\b")
PRINTED_PAGE_RE = re.compile(r"\b13-(?P<number>\d+)\b")
ROMAN_LIST_TOKEN_PATTERN = r"(?:x(?:ix|iv|v?i{0,3})|ix|iv|v?i{1,3})"
LIST_TOKEN_PATTERN = rf"(?:\d{{1,3}}|[A-Za-z]|{ROMAN_LIST_TOKEN_PATTERN})"
LIST_PREFIX_RE = re.compile(
    rf"^\s*(?:(?P<base>{LOCATOR_PATTERN})(?:\*)?)?"
    rf"(?P<markers>(?:\({LIST_TOKEN_PATTERN}\))+)(?=\s|$)",
    re.IGNORECASE,
)
TABLE_CAPTION_RE = re.compile(rf"^\s*Table\s+(?P<locator>{OBJECT_LOCATOR_PATTERN})(?=\s|$)", re.IGNORECASE)
FIGURE_CAPTION_RE = re.compile(rf"^\s*FIGURE\s+(?P<locator>{OBJECT_LOCATOR_PATTERN})(?=\s|$)", re.IGNORECASE)
NOTE_RE = re.compile(r"^\s*(?:NOTE|Note)(?:\s+\d+)?\s*[:.]", re.IGNORECASE)
EXCEPTION_RE = re.compile(r"^\s*Exception(?:\s+No\.\s*\d+|\s+\d+)?\s*[:.]", re.IGNORECASE)
FOOTNOTE_RE = re.compile(r"^\s*(?:\*|†|‡|[a-z])\s+(?=\S)")

REFERENCE_RE = re.compile(
    rf"(?P<section>\bSection[ \t]+(?P<section_locator>{LOCATOR_PATTERN}))"
    rf"|(?P<table>\bTable[ \t]+(?P<table_locator>{OBJECT_LOCATOR_PATTERN}))"
    rf"|(?P<figure>\bFigure[ \t]+(?P<figure_locator>{OBJECT_LOCATOR_PATTERN}))"
    r"|(?P<chapter>\bChapter[ \t]+(?P<chapter_locator>\d+))"
    r"|(?P<nfpa>\bNFPA[ \t]+(?P<nfpa_number>\d+[A-Z]?))",
    re.IGNORECASE,
)
MODAL_RE = re.compile(
    r"\b(?P<modal>shall\s+not|must\s+not|may\s+not|shall|must|may|should|"
    r"(?:is|are)\s+required\s+to|(?:is|are)\s+permitted\s+to)\b",
    re.IGNORECASE,
)
CONDITION_RE = re.compile(
    r"\b(where|when|if|unless|provided\s+that|exceeding|greater\s+than|"
    r"less\s+than|at\s+least|not\s+less\s+than)\b",
    re.IGNORECASE,
)
ALTERNATIVE_RE = re.compile(r"\b(either|one\s+of|any\s+of|in\s+lieu\s+of|alternatively)\b", re.IGNORECASE)
APPLICABILITY_RE = re.compile(r"\b(applies?\s+to|applicable\s+to|for\s+use\s+with)\b", re.IGNORECASE)
CALCULATION_RE = re.compile(r"\b(calculate(?:d|s|ing)?|calculation|equation|formula|interpolation)\b", re.IGNORECASE)
EXCEPTION_INLINE_RE = re.compile(r"\bexcept(?:ion)?\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RawLine:
    text: str
    pdf_page: int
    printed_page: str | None
    column: int
    bbox: tuple[float, float, float, float]
    fonts: tuple[str, ...] = ()
    sizes: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceLine:
    text: str
    pdf_page: int
    printed_page: str | None
    column: int
    bbox: tuple[float, float, float, float]
    fonts: tuple[str, ...]
    sizes: tuple[float, ...]
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class SourceStream:
    text: str
    lines: tuple[SourceLine, ...]
    starts: tuple[int, ...]

    def lines_in(self, start: int, end: int) -> list[SourceLine]:
        left = bisect_left(self.starts, start)
        right = bisect_right(self.starts, end)
        return [line for line in self.lines[left:right] if line.start >= start and line.end <= end]


@dataclass(frozen=True, slots=True)
class StructuralRange:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class TableObject:
    locator: str
    pdf_page: int
    bbox: tuple[float, float, float, float]
    start: int
    end: int
    rows: tuple[tuple[SourceLine, ...], ...]

    @property
    def source_lines(self) -> tuple[SourceLine, ...]:
        unique = {line.start: line for row in self.rows for line in row}
        return tuple(unique[start] for start in sorted(unique))

    @property
    def matrix(self) -> tuple[tuple[str | None, ...], ...]:
        return tuple(tuple(line.text.strip() for line in row) for row in self.rows)


@dataclass(frozen=True, slots=True)
class TableSourceIndex:
    starts: tuple[int, ...]
    entries: tuple[tuple[int, int, str], ...]
    tables: tuple[TableObject, ...]

    @classmethod
    def from_tables(cls, tables: Sequence[TableObject]) -> "TableSourceIndex":
        ordered_tables = tuple(sorted(tables, key=lambda item: (item.start, item.locator)))
        entries = tuple(
            sorted(
                (line.start, line.end, table.locator)
                for table in ordered_tables
                for line in table.source_lines
            )
        )
        return cls(
            starts=tuple(entry[0] for entry in entries),
            entries=entries,
            tables=ordered_tables,
        )

    def overlapping(self, start: int, end: int) -> list[TableObject]:
        if start >= end or not self.entries:
            return []
        left = bisect_left(self.starts, start)
        while left > 0 and self.entries[left - 1][1] > start:
            left -= 1
        right = bisect_left(self.starts, end)
        locators = {
            locator
            for line_start, line_end, locator in self.entries[left:right]
            if line_start < end and line_end > start
        }
        return [table for table in self.tables if table.locator in locators]


def _pdf_module() -> Any:
    if fitz is None:
        raise RuntimeError(
            "NFPA 13 AST extraction requires PyMuPDF; install it with "
            "`python -m pip install pymupdf`."
        )
    return fitz


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _node_id(locator: str, node_type: str) -> str:
    canonical = json.dumps(
        {
            "artifact_id": ARTIFACT_ID,
            "edition_id": EDITION_ID,
            "locator": locator,
            "node_type": node_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "docnode:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _span(source: str, start: int, end: int) -> dict[str, Any]:
    return {"start": start, "end": end, "text": source[start:end]}


def _node(
    source: str,
    *,
    node_type: str,
    locator: str,
    start: int,
    end: int,
    label: str | None = None,
    attributes: Mapping[str, str] | None = None,
    children: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "node_id": _node_id(locator, node_type),
        "type": node_type,
        "locator": locator,
        "span": _span(source, start, end),
        "label": label,
        "attributes": dict(sorted((attributes or {}).items())),
        "children": list(children),
    }


def _artifact_line(line: RawLine) -> bool:
    text = line.text.strip()
    if not text:
        return True
    if line.bbox[1] < 55.0 or line.bbox[1] > 730.0:
        return True
    if text in {"N", "Δ"} and any("BoldIt" in font for font in line.fonts):
        return True
    return False


def build_source_stream_from_lines(lines: Iterable[RawLine]) -> SourceStream:
    retained = [line for line in lines if not _artifact_line(line)]
    retained.sort(key=lambda line: (line.pdf_page, line.column, line.bbox[1], line.bbox[0], line.bbox[2]))
    parts: list[str] = []
    positioned: list[SourceLine] = []
    cursor = 0
    for index, line in enumerate(retained):
        if index:
            parts.append("\n")
            cursor += 1
        start = cursor
        parts.append(line.text)
        cursor += len(line.text)
        positioned.append(
            SourceLine(
                text=line.text,
                pdf_page=line.pdf_page,
                printed_page=line.printed_page,
                column=line.column,
                bbox=line.bbox,
                fonts=line.fonts,
                sizes=line.sizes,
                start=start,
                end=cursor,
            )
        )
    positioned_tuple = tuple(positioned)
    return SourceStream(
        text="".join(parts),
        lines=positioned_tuple,
        starts=tuple(line.start for line in positioned_tuple),
    )


def raw_lines_from_document(doc: Any, first_page: int, last_page: int) -> list[RawLine]:
    lines: list[RawLine] = []
    for pdf_page in range(first_page, last_page + 1):
        page = doc[pdf_page - 1]
        printed_match = PRINTED_PAGE_RE.search(page.get_text("text")[:400])
        printed_page = f"13-{printed_match.group('number')}" if printed_match else None
        for block in page.get_text("dict", sort=False).get("blocks", []):
            for raw in block.get("lines", []):
                spans = [span for span in raw.get("spans", []) if span.get("text")]
                text = "".join(str(span.get("text", "")) for span in spans)
                if not text.strip():
                    continue
                bbox = tuple(float(value) for value in raw["bbox"])
                lines.append(
                    RawLine(
                        text=text,
                        pdf_page=pdf_page,
                        printed_page=printed_page,
                        column=0 if bbox[0] < 306.0 else 1,
                        bbox=bbox,
                        fonts=tuple(str(span.get("font", "")) for span in spans),
                        sizes=tuple(float(span.get("size", 0.0)) for span in spans),
                    )
                )
    return lines


def _depth(locator: str, parents: Mapping[str, str | None]) -> int:
    depth = 0
    cursor: str | None = locator
    seen: set[str] = set()
    while cursor and cursor != "document":
        if cursor in seen:
            raise ValueError(f"cyclic structural parent chain at {locator}")
        seen.add(cursor)
        depth += 1
        cursor = parents.get(cursor)
    return depth


def _is_descendant(
    locator: str,
    ancestor: str,
    parents: Mapping[str, str | None],
) -> bool:
    cursor = parents.get(locator)
    seen: set[str] = set()
    while cursor:
        if cursor == ancestor:
            return True
        if cursor in seen:
            raise ValueError(f"cyclic structural parent chain at {locator}")
        seen.add(cursor)
        cursor = parents.get(cursor)
    return False


def compute_structural_ranges(
    parents: Mapping[str, str | None],
    anchors: Mapping[str, int],
    *,
    source_length: int,
) -> dict[str, StructuralRange]:
    ordered = sorted(anchors.items(), key=lambda item: (item[1], _depth(item[0], parents), item[0]))
    result: dict[str, StructuralRange] = {}
    for index, (locator, start) in enumerate(ordered):
        end = source_length
        for following, following_start in ordered[index + 1 :]:
            if not _is_descendant(following, locator, parents):
                end = following_start
                break
        result[locator] = StructuralRange(start, end)

    unresolved = [locator for locator in parents if locator not in result and locator != "document"]
    while unresolved:
        progress = False
        for locator in list(unresolved):
            children = [child for child, parent in parents.items() if parent == locator]
            if children and all(child in result for child in children):
                result[locator] = StructuralRange(
                    min(result[child].start for child in children),
                    max(result[child].end for child in children),
                )
                unresolved.remove(locator)
                progress = True
        if not progress:
            break
    return result


def direct_intervals(parent: StructuralRange, children: Sequence[StructuralRange]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    cursor = parent.start
    for child in sorted(children, key=lambda item: (item.start, item.end)):
        if child.end <= cursor:
            continue
        if child.start > cursor:
            intervals.append((cursor, min(child.start, parent.end)))
        cursor = max(cursor, child.end)
        if cursor >= parent.end:
            break
    if cursor < parent.end:
        intervals.append((cursor, parent.end))
    return [(start, end) for start, end in intervals if start < end]


def _trim_interval(source: str, start: int, end: int) -> tuple[int, int]:
    while start < end and source[start].isspace():
        start += 1
    while end > start and source[end - 1].isspace():
        end -= 1
    return start, end


def _line_gap(left: SourceLine, right: SourceLine) -> float:
    if left.pdf_page != right.pdf_page or left.column != right.column:
        return 999.0
    return right.bbox[1] - left.bbox[3]


def _marker_tokens(markers: str) -> list[str]:
    return re.findall(r"\(([^)]+)\)", markers)


def _list_marker_match(line: SourceLine, owner_locator: str) -> re.Match[str] | None:
    match = LIST_PREFIX_RE.match(line.text)
    if match is None:
        return None
    if not line.fonts or not line.fonts[0].startswith("NewBaskervilleStd"):
        return None
    base = match.group("base")
    structural_owner = owner_locator.split("#", 1)[0]
    if base and base != structural_owner:
        return None
    return match


def _marker_level(token: str, current_stack: Sequence[tuple[int, dict[str, Any]]]) -> int:
    if token.isdigit():
        return 1
    lowered = token.lower()
    roman = bool(re.fullmatch(r"[ivxlcdm]+", lowered))
    if roman and (len(lowered) > 1 or current_stack and current_stack[-1][0] >= 2):
        return 3
    return 2


def _locations(lines: Sequence[SourceLine]) -> str:
    return json.dumps(
        [
            {
                "pdf_page": line.pdf_page,
                "printed_page": line.printed_page,
                "column": line.column,
                "bbox": [round(value, 3) for value in line.bbox],
            }
            for line in lines
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def _make_leaf(
    stream: SourceStream,
    *,
    node_type: str,
    locator: str,
    lines: Sequence[SourceLine],
    label: str | None = None,
    attributes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    start, end = _trim_interval(stream.text, lines[0].start, lines[-1].end)
    attrs = dict(attributes or {})
    attrs["owns_source"] = "true"
    attrs["source_locations"] = _locations(lines)
    return _node(
        stream.text,
        node_type=node_type,
        locator=locator,
        start=start,
        end=end,
        label=label,
        attributes=attrs,
    )


def _paragraph_kind(
    first_text: str,
    *,
    owner_attributes: Mapping[str, str],
    owner_heading: str | None,
    is_first: bool,
    fonts: Sequence[str],
) -> tuple[str, dict[str, str]]:
    stripped = first_text.strip()
    if FIGURE_CAPTION_RE.match(stripped):
        match = FIGURE_CAPTION_RE.match(stripped)
        assert match
        return "unsupported", {"kind": "figure", "target_locator": f"figure:{match.group('locator')}"}
    if TABLE_CAPTION_RE.match(stripped):
        match = TABLE_CAPTION_RE.match(stripped)
        assert match
        return "table_heading", {"kind": "table_caption", "target_locator": f"table:{match.group('locator')}"}
    if EXCEPTION_RE.match(stripped):
        return "note", {"kind": "exception"}
    if NOTE_RE.match(stripped):
        return "note", {"kind": "note"}
    if FOOTNOTE_RE.match(stripped) and any("Italic" in font for font in fonts):
        return "footnote", {"kind": "footnote"}
    if is_first and owner_attributes.get("chapter") == "3" and owner_heading:
        return "definition_entry", {"kind": "definition", "term": owner_heading}
    if fonts and all(not font.startswith("NewBaskervilleStd") for font in fonts if font):
        return "unsupported", {"kind": "graphical_text"}
    return "paragraph", {"kind": "prose"}


def _build_paragraph_leaf(
    stream: SourceStream,
    owner_locator: str,
    index: int,
    lines: Sequence[SourceLine],
    *,
    owner_attributes: Mapping[str, str],
    owner_heading: str | None,
    is_first: bool,
    locator_override: str | None = None,
) -> dict[str, Any]:
    fonts = tuple(font for line in lines for font in line.fonts)
    node_type, attrs = _paragraph_kind(
        lines[0].text,
        owner_attributes=owner_attributes,
        owner_heading=owner_heading,
        is_first=is_first,
        fonts=fonts,
    )
    locator = locator_override or f"{owner_locator}#p{index}"
    return _make_leaf(
        stream,
        node_type=node_type,
        locator=locator,
        lines=lines,
        label=owner_heading if node_type == "definition_entry" else None,
        attributes=attrs,
    )


def parse_direct_blocks(
    stream: SourceStream,
    intervals: Sequence[tuple[int, int]],
    *,
    owner_locator: str,
    owner_heading: str | None,
    owner_attributes: Mapping[str, str],
) -> list[dict[str, Any]]:
    candidate_lines: list[SourceLine] = []
    for start, end in intervals:
        candidate_lines.extend(stream.lines_in(start, end))
    candidate_lines.sort(key=lambda line: line.start)
    if not candidate_lines:
        return []

    top_level: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []
    paragraph_lines: list[SourceLine] = []
    paragraph_index = 0
    first_block = True
    list_locator_counts: Counter[str] = Counter()

    def append_block(block: dict[str, Any], level: int | None = None) -> None:
        nonlocal first_block
        if level is None:
            top_level.append(block)
            stack.clear()
        else:
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(block)
            else:
                top_level.append(block)
            stack.append((level, block))
        first_block = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_index
        if not paragraph_lines:
            return
        paragraph_index += 1
        block = _build_paragraph_leaf(
            stream,
            owner_locator,
            paragraph_index,
            paragraph_lines,
            owner_attributes=owner_attributes,
            owner_heading=owner_heading,
            is_first=first_block,
        )
        append_block(block)
        paragraph_lines = []

    previous_line: SourceLine | None = None
    for line in candidate_lines:
        marker_match = _list_marker_match(line, owner_locator)
        special = bool(
            FIGURE_CAPTION_RE.match(line.text.strip())
            or TABLE_CAPTION_RE.match(line.text.strip())
            or NOTE_RE.match(line.text.strip())
            or EXCEPTION_RE.match(line.text.strip())
        )
        if marker_match:
            flush_paragraph()
            tokens = _marker_tokens(marker_match.group("markers"))
            for token_index, token in enumerate(tokens):
                level = _marker_level(token, stack)
                marker = f"({token})"
                parent_node = next(
                    (item[1] for item in reversed(stack) if item[0] < level),
                    None,
                )
                locator_base = (
                    f"{parent_node['locator']}{marker}"
                    if parent_node is not None
                    else f"{owner_locator}#list{marker}"
                )
                list_locator_counts[locator_base] += 1
                occurrence = list_locator_counts[locator_base]
                locator = locator_base if occurrence == 1 else f"{locator_base}~{occurrence}"
                list_node = _node(
                    stream.text,
                    node_type="list_item",
                    locator=locator,
                    start=line.start,
                    end=line.end,
                    attributes={
                        "marker": marker,
                        "marker_level": str(level),
                        "owns_source": "false",
                        "source_locations": _locations([line]),
                    },
                )
                append_block(list_node, level)
                if token_index < len(tokens) - 1:
                    continue
            current = stack[-1][1]
            text_locator = f"{current['locator']}#text"
            leaf = _build_paragraph_leaf(
                stream,
                owner_locator,
                paragraph_index + 1,
                [line],
                owner_attributes=owner_attributes,
                owner_heading=None,
                is_first=False,
                locator_override=text_locator,
            )
            current["children"].append(leaf)
            current["span"] = _span(stream.text, line.start, line.end)
            previous_line = line
            continue

        if stack and previous_line is not None and not special and _line_gap(previous_line, line) <= 8.5:
            current = stack[-1][1]
            text_child = next((child for child in current["children"] if child["locator"].endswith("#text")), None)
            if text_child is not None:
                start = text_child["span"]["start"]
                text_child["span"] = _span(stream.text, start, line.end)
                locations = json.loads(text_child["attributes"]["source_locations"])
                locations.append(
                    {
                        "pdf_page": line.pdf_page,
                        "printed_page": line.printed_page,
                        "column": line.column,
                        "bbox": [round(value, 3) for value in line.bbox],
                    }
                )
                text_child["attributes"]["source_locations"] = json.dumps(
                    locations, sort_keys=True, separators=(",", ":")
                )
                current["span"] = _span(stream.text, current["span"]["start"], line.end)
                previous_line = line
                continue

        stack.clear()
        if special:
            flush_paragraph()
            paragraph_index += 1
            block = _build_paragraph_leaf(
                stream,
                owner_locator,
                paragraph_index,
                [line],
                owner_attributes=owner_attributes,
                owner_heading=owner_heading,
                is_first=first_block,
            )
            append_block(block)
            previous_line = line
            continue

        if paragraph_lines and _line_gap(paragraph_lines[-1], line) > 8.5:
            flush_paragraph()
        paragraph_lines.append(line)
        previous_line = line

    flush_paragraph()

    def expand_span(node: dict[str, Any]) -> None:
        for child in node["children"]:
            expand_span(child)
        if node["children"]:
            node["span"] = _span(
                stream.text,
                min([node["span"]["start"], *(child["span"]["start"] for child in node["children"])]),
                max([node["span"]["end"], *(child["span"]["end"] for child in node["children"])]),
            )

    for block in top_level:
        expand_span(block)
    return top_level


def document_level_blocks(
    stream: SourceStream,
    structural_child_ranges: Sequence[StructuralRange],
) -> list[dict[str, Any]]:
    intervals = direct_intervals(
        StructuralRange(0, len(stream.text)),
        structural_child_ranges,
    )
    blocks: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(intervals, start=1):
        lines = stream.lines_in(start, end)
        if not lines:
            continue
        blocks.append(
            _make_leaf(
                stream,
                node_type="unsupported",
                locator=f"document#matter{index}",
                lines=lines,
                attributes={"kind": "document_matter"},
            )
        )
    return blocks


def extract_relations(
    *,
    source_node_locator: str,
    text: str,
    base_offset: int,
    known_locators: set[str],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for match in REFERENCE_RE.finditer(text):
        relation_type: str
        target: str
        if match.group("section"):
            relation_type = "references_clause"
            target = match.group("section_locator")
        elif match.group("table"):
            relation_type = "references_table"
            target = f"table:{match.group('table_locator')}"
        elif match.group("figure"):
            relation_type = "references_figure"
            target = f"figure:{match.group('figure_locator')}"
        elif match.group("chapter"):
            relation_type = "references_chapter"
            target = match.group("chapter_locator")
        else:
            relation_type = "references_external_standard"
            target = f"external:nfpa:{match.group('nfpa_number')}"
        relations.append(
            {
                "type": relation_type,
                "source_locator": source_node_locator,
                "target_locator": target,
                "resolved": target in known_locators or target.startswith("external:"),
                "evidence": {
                    "start": base_offset + match.start(),
                    "end": base_offset + match.end(),
                    "text": match.group(0),
                },
            }
        )
    return relations


def annex_a_relation(locator: str, known_locators: set[str]) -> dict[str, Any]:
    target = locator.removeprefix("A.")
    return {
        "type": "explains",
        "source_locator": locator,
        "target_locator": target,
        "resolved": target in known_locators,
        "evidence": None,
    }


def _semantic_annotation(
    annotation_type: str,
    source_node_locator: str,
    base_offset: int,
    text: str,
    start: int,
    end: int,
    *,
    confidence: str = "deterministic",
) -> dict[str, Any]:
    return {
        "type": annotation_type,
        "source_locator": source_node_locator,
        "confidence": confidence,
        "evidence": {
            "start": base_offset + start,
            "end": base_offset + end,
            "text": text[start:end],
        },
    }


def classify_semantics(
    *,
    source_node_locator: str,
    text: str,
    base_offset: int,
    attributes: Mapping[str, str],
) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    if attributes.get("annex"):
        annotations.append(_semantic_annotation("informative", source_node_locator, base_offset, text, 0, len(text)))
    if attributes.get("kind") == "definition":
        annotations.append(_semantic_annotation("definition", source_node_locator, base_offset, text, 0, len(text)))
    if attributes.get("scope") == "true" or source_node_locator.startswith("1.1"):
        annotations.append(_semantic_annotation("scope", source_node_locator, base_offset, text, 0, len(text)))
    if EXCEPTION_RE.match(text) or EXCEPTION_INLINE_RE.search(text):
        match = EXCEPTION_RE.match(text) or EXCEPTION_INLINE_RE.search(text)
        assert match
        annotations.append(
            _semantic_annotation(
                "exception", source_node_locator, base_offset, text, match.start(), match.end()
            )
        )
    for match in CONDITION_RE.finditer(text):
        annotations.append(
            _semantic_annotation(
                "condition", source_node_locator, base_offset, text, match.start(), match.end()
            )
        )
    for match in ALTERNATIVE_RE.finditer(text):
        annotations.append(
            _semantic_annotation(
                "alternative", source_node_locator, base_offset, text, match.start(), match.end()
            )
        )
    for match in APPLICABILITY_RE.finditer(text):
        annotations.append(
            _semantic_annotation(
                "applicability", source_node_locator, base_offset, text, match.start(), match.end()
            )
        )
    for match in CALCULATION_RE.finditer(text):
        annotations.append(
            _semantic_annotation(
                "calculation", source_node_locator, base_offset, text, match.start(), match.end()
            )
        )
    for match in MODAL_RE.finditer(text):
        normalized = " ".join(match.group("modal").lower().split())
        if normalized in {"shall not", "must not", "may not"}:
            semantic_type = "prohibition"
        elif normalized in {"may", "is permitted to", "are permitted to"}:
            semantic_type = "permission"
        elif normalized == "should":
            semantic_type = "recommendation"
        else:
            semantic_type = "requirement"
        annotations.append(
            _semantic_annotation(
                semantic_type,
                source_node_locator,
                base_offset,
                text,
                match.start(),
                match.end(),
            )
        )
    unique: dict[tuple[str, int, int], dict[str, Any]] = {}
    for item in annotations:
        evidence = item["evidence"]
        unique[(item["type"], evidence["start"], evidence["end"])] = item
    return sorted(unique.values(), key=lambda item: (item["evidence"]["start"], item["type"]))


def build_diagnostics(
    relations: Sequence[Mapping[str, Any]],
    nodes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for relation in relations:
        if relation.get("resolved") or relation.get("evidence") is None:
            continue
        diagnostics.append(
            {
                "code": "unresolved-reference",
                "severity": "warning",
                "message": (
                    f"Reference from {relation.get('source_locator')} to "
                    f"{relation.get('target_locator')} did not resolve to an extracted target."
                ),
                "span": relation["evidence"],
            }
        )
    for node in nodes:
        attributes = node.get("attributes", {})
        if not isinstance(attributes, Mapping):
            continue
        if attributes.get("kind") == "figure":
            diagnostics.append(
                {
                    "code": "unsupported-figure-interpretation",
                    "severity": "info",
                    "message": (
                        f"Figure caption {node.get('locator')} was preserved, but image and "
                        "diagram semantics were not interpreted."
                    ),
                    "span": node["span"],
                }
            )
        if (
            node.get("type") == "table_heading"
            and not str(node.get("locator", "")).startswith("table:")
        ):
            diagnostics.append(
                {
                    "code": "unsupported-table-layout",
                    "severity": "info",
                    "message": (
                        f"Table caption {node.get('locator')} was preserved, but its layout "
                        "did not produce an accepted geometry-backed table subtree."
                    ),
                    "span": node["span"],
                }
            )
    diagnostics.sort(
        key=lambda item: (
            -1 if item["span"] is None else item["span"]["start"],
            item["code"],
            item["message"],
        )
    )
    return diagnostics


def _walk(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def synthetic_bundle(source_text: str) -> dict[str, Any]:
    child = _node(
        source_text,
        node_type="paragraph",
        locator="1.1#p1",
        start=0,
        end=len(source_text),
        attributes={"owns_source": "true"},
    )
    root = _node(
        source_text,
        node_type="document",
        locator="document",
        start=0,
        end=len(source_text),
        attributes={"owns_source": "false"},
        children=[child],
    )
    return {
        "schema": BUNDLE_SCHEMA,
        "source": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
        "document_ast": {
            "ast_version": DOCUMENT_AST_VERSION,
            "type": "document_tree",
            "source_text": source_text,
            "source_artifact": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
            "root": root,
            "diagnostics": [],
        },
        "relations": [],
        "semantic_annotations": [],
        "tables": [],
        "source_map": [],
        "statistics": {},
        "validation": {},
    }


def validate_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    ast = bundle.get("document_ast", {})
    source = ast.get("source_text", "") if isinstance(ast, Mapping) else ""
    root = ast.get("root") if isinstance(ast, Mapping) else None
    if not isinstance(root, Mapping):
        return {
            "passed": False,
            "duplicate_locators": [],
            "duplicate_node_ids": [],
            "invalid_deterministic_ids": [],
            "invalid_spans": ["missing root"],
            "child_spans_outside_parent": [],
            "invalid_resolved_relations": [],
            "invalid_relation_sources": [],
            "invalid_relation_evidence": [],
            "invalid_semantic_sources": [],
            "invalid_semantic_evidence": [],
            "invalid_diagnostic_spans": [],
            "uncovered_non_whitespace_characters": [],
            "multiply_owned_non_whitespace_characters": [],
            "revision_marker_leaks": [],
        }
    nodes = list(_walk(dict(root)))
    locator_counts = Counter(str(node.get("locator")) for node in nodes)
    id_counts = Counter(str(node.get("node_id")) for node in nodes)
    duplicate_locators = sorted(key for key, count in locator_counts.items() if count > 1)
    duplicate_ids = sorted(key for key, count in id_counts.items() if count > 1)
    invalid_ids: list[str] = []
    invalid_spans: list[str] = []
    child_outside: list[str] = []
    revision_leaks: list[str] = []
    owners = [0] * len(source)

    def visit(node: Mapping[str, Any], parent: Mapping[str, Any] | None) -> None:
        locator = str(node.get("locator", ""))
        node_type = str(node.get("type", ""))
        if node.get("node_id") != _node_id(locator, node_type):
            invalid_ids.append(locator)
        span = node.get("span", {})
        try:
            start = int(span["start"])
            end = int(span["end"])
            text = span["text"]
        except (KeyError, TypeError, ValueError):
            invalid_spans.append(locator)
            start = end = 0
            text = ""
        if start < 0 or end < start or end > len(source) or source[start:end] != text:
            invalid_spans.append(locator)
        if parent is not None:
            pspan = parent.get("span", {})
            if start < int(pspan.get("start", 0)) or end > int(pspan.get("end", 0)):
                child_outside.append(locator)
        attributes = node.get("attributes", {})
        if isinstance(attributes, Mapping) and attributes.get("owns_source") == "true":
            for index in range(max(0, start), min(len(source), end)):
                if not source[index].isspace():
                    owners[index] += 1
        for child in node.get("children", []):
            visit(child, node)

    visit(root, None)
    known = set(locator_counts)
    for node in nodes:
        attributes = node.get("attributes", {})
        if isinstance(attributes, Mapping) and attributes.get("target_locator"):
            known.add(str(attributes["target_locator"]))
    for table in bundle.get("tables", []):
        if isinstance(table, Mapping) and table.get("locator"):
            known.add(str(table["locator"]))
    for item in bundle.get("source_map", []):
        if not isinstance(item, Mapping):
            continue
        try:
            start = int(item["start"])
            end = int(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        fonts = item.get("fonts", [])
        if (
            source[start:end].strip() in {"N", "Δ"}
            and isinstance(fonts, list)
            and any("BoldIt" in str(font) for font in fonts)
        ):
            revision_leaks.append(f"source:{start}")
    relations = bundle.get("relations", [])
    invalid_relations = [
        f"{relation.get('source_locator')}->{relation.get('target_locator')}"
        for relation in relations
        if relation.get("resolved")
        and not str(relation.get("target_locator", "")).startswith("external:")
        and relation.get("target_locator") not in known
    ]

    def valid_evidence(value: Any, *, allow_none: bool = False) -> bool:
        if value is None:
            return allow_none
        if not isinstance(value, Mapping):
            return False
        try:
            start = int(value["start"])
            end = int(value["end"])
            text = value["text"]
        except (KeyError, TypeError, ValueError):
            return False
        return (
            isinstance(text, str)
            and 0 <= start <= end <= len(source)
            and source[start:end] == text
        )

    invalid_relation_sources = sorted(
        {
            str(relation.get("source_locator"))
            for relation in relations
            if relation.get("source_locator") not in known
        }
    )
    invalid_relation_evidence = [
        f"{relation.get('source_locator')}->{relation.get('target_locator')}"
        for relation in relations
        if not valid_evidence(relation.get("evidence"), allow_none=True)
    ]
    semantics = bundle.get("semantic_annotations", [])
    invalid_semantic_sources = sorted(
        {
            str(annotation.get("source_locator"))
            for annotation in semantics
            if annotation.get("source_locator") not in known
        }
    )
    invalid_semantic_evidence = [
        f"{annotation.get('source_locator')}:{annotation.get('type')}"
        for annotation in semantics
        if not valid_evidence(annotation.get("evidence"))
    ]
    diagnostics = ast.get("diagnostics", []) if isinstance(ast, Mapping) else []
    invalid_diagnostic_spans = [
        f"{index}:{diagnostic.get('code') if isinstance(diagnostic, Mapping) else 'invalid'}"
        for index, diagnostic in enumerate(diagnostics if isinstance(diagnostics, list) else [])
        if not isinstance(diagnostic, Mapping)
        or not valid_evidence(diagnostic.get("span"), allow_none=True)
    ]
    if not isinstance(diagnostics, list):
        invalid_diagnostic_spans.append("diagnostics:not-an-array")

    uncovered = [index for index, char in enumerate(source) if not char.isspace() and owners[index] == 0]
    multiplied = [index for index, char in enumerate(source) if not char.isspace() and owners[index] > 1]
    report = {
        "passed": not (
            duplicate_locators
            or duplicate_ids
            or invalid_ids
            or invalid_spans
            or child_outside
            or invalid_relations
            or invalid_relation_sources
            or invalid_relation_evidence
            or invalid_semantic_sources
            or invalid_semantic_evidence
            or invalid_diagnostic_spans
            or uncovered
            or multiplied
            or revision_leaks
        ),
        "node_count": len(nodes),
        "duplicate_locators": duplicate_locators,
        "duplicate_node_ids": duplicate_ids,
        "invalid_deterministic_ids": sorted(set(invalid_ids)),
        "invalid_spans": sorted(set(invalid_spans)),
        "child_spans_outside_parent": sorted(set(child_outside)),
        "invalid_resolved_relations": sorted(set(invalid_relations)),
        "invalid_relation_sources": invalid_relation_sources,
        "invalid_relation_evidence": sorted(set(invalid_relation_evidence)),
        "invalid_semantic_sources": invalid_semantic_sources,
        "invalid_semantic_evidence": sorted(set(invalid_semantic_evidence)),
        "invalid_diagnostic_spans": sorted(set(invalid_diagnostic_spans)),
        "uncovered_non_whitespace_characters": uncovered[:100],
        "uncovered_non_whitespace_count": len(uncovered),
        "multiply_owned_non_whitespace_characters": multiplied[:100],
        "multiply_owned_non_whitespace_count": len(multiplied),
        "revision_marker_leaks": sorted(set(revision_leaks)),
    }
    return report


def _load_hierarchy_module() -> Any:
    path = Path(__file__).with_name("extract_nfpa13_2019_hierarchy.py")
    spec = importlib.util.spec_from_file_location("extract_nfpa13_2019_hierarchy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import hierarchy extractor at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _flatten_hierarchy(root: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    def visit(node: Mapping[str, Any], parent: str | None) -> None:
        locator = str(node["locator"])
        result[locator] = {
            "locator": locator,
            "parent": parent,
            "type": str(node["type"]),
            "label": node.get("label"),
            "attributes": dict(node.get("attributes", {})),
            "source": node.get("source"),
            "references": list(node.get("references", [])),
            "children": [str(child["locator"]) for child in node.get("children", [])],
        }
        for child in node.get("children", []):
            visit(child, locator)

    visit(root, None)
    return result


def _find_anchors(
    hierarchy_nodes: Mapping[str, Mapping[str, Any]], stream: SourceStream
) -> dict[str, int]:
    anchors: dict[str, int] = {"document": 0}
    by_page: dict[int, list[SourceLine]] = {}
    for line in stream.lines:
        by_page.setdefault(line.pdf_page, []).append(line)

    for locator, node in hierarchy_nodes.items():
        if locator == "document":
            continue
        source = node.get("source")
        candidates: list[SourceLine] = []
        if isinstance(source, Mapping) and source.get("pdf_page"):
            candidates = by_page.get(int(source["pdf_page"]), [])
        if isinstance(source, Mapping) and source.get("bbox"):
            bbox = [float(value) for value in source["bbox"]]
            matching = [
                line
                for line in candidates
                if line.text.lstrip().startswith(locator)
                and abs(line.bbox[0] - bbox[0]) <= 3.0
                and abs(line.bbox[1] - bbox[1]) <= 3.0
            ]
            if matching:
                anchors[locator] = min(matching, key=lambda line: abs(line.bbox[1] - bbox[1])).start
                continue
        if node.get("attributes", {}).get("container_kind"):
            pattern = re.compile(
                rf"^\s*(?:Chapter\s+{re.escape(locator)}|Annex\s+{re.escape(locator)})\b",
                re.IGNORECASE,
            )
            matching = [line for line in candidates if pattern.match(line.text)]
            if matching:
                anchors[locator] = matching[0].start
                continue
        if candidates:
            matching = [line for line in candidates if line.text.lstrip().startswith(locator)]
            if matching:
                anchors[locator] = matching[0].start
    return anchors


def _source_locations_for_span(stream: SourceStream, start: int, end: int) -> str:
    return _locations(stream.lines_in(start, end))




def table_caption_clips(stream: SourceStream) -> list[dict[str, Any]]:
    clips: list[dict[str, Any]] = []
    lines_by_page: dict[int, list[SourceLine]] = {}
    for line in stream.lines:
        lines_by_page.setdefault(line.pdf_page, []).append(line)
    for line in stream.lines:
        match = TABLE_CAPTION_RE.match(line.text.strip())
        if not match or not line.fonts or not line.fonts[0].startswith("NewBaskervilleStd-Bold"):
            continue
        spans_columns = line.bbox[0] < 306.0 < line.bbox[2]
        x0, x1 = (36.0, 576.0) if spans_columns else ((36.0, 306.0) if line.column == 0 else (306.0, 576.0))
        y1 = 729.0
        for following in lines_by_page.get(line.pdf_page, []):
            if following.bbox[1] <= line.bbox[1] + 2.0:
                continue
            if not spans_columns and following.column != line.column:
                continue
            bold = bool(following.fonts and following.fonts[0].startswith("NewBaskervilleStd-Bold"))
            structural = bool(
                CLAUSE_AT_START_RE.match(following.text)
                or TABLE_CAPTION_RE.match(following.text.strip())
                or FIGURE_CAPTION_RE.match(following.text.strip())
                or CONTAINER_RE.match(following.text)
            )
            if bold and structural:
                y1 = max(line.bbox[3] + 12.0, following.bbox[1] - 1.0)
                break
        clips.append(
            {
                "locator": f"table:{match.group('locator')}",
                "pdf_page": line.pdf_page,
                "bbox": (x0, max(55.0, line.bbox[1] - 1.0), x1, y1),
                "caption_start": line.start,
            }
        )
    return clips

def _extract_tables(doc: Any, stream: SourceStream) -> list[TableObject]:
    del doc  # Geometry-only extraction is deterministic and avoids a costly layout solver.
    lines_by_page: dict[int, list[SourceLine]] = {}
    for line in stream.lines:
        lines_by_page.setdefault(line.pdf_page, []).append(line)
    tables: list[TableObject] = []
    for clip in table_caption_clips(stream):
        pdf_page = int(clip["pdf_page"])
        x0, y0, x1, y1 = (float(value) for value in clip["bbox"])
        region = [
            line
            for line in lines_by_page.get(pdf_page, [])
            if line.bbox[0] < x1
            and line.bbox[2] > x0
            and line.bbox[1] >= y0
            and line.bbox[3] <= y1 + 0.5
        ]
        region.sort(key=lambda line: ((line.bbox[1] + line.bbox[3]) / 2.0, line.bbox[0]))
        caption = next((line for line in region if line.start == clip["caption_start"]), None)
        if caption is None:
            continue
        rows: list[list[SourceLine]] = []
        current: list[SourceLine] = []
        current_y: float | None = None
        for line in region:
            center_y = (line.bbox[1] + line.bbox[3]) / 2.0
            if current_y is None or abs(center_y - current_y) <= 2.5:
                current.append(line)
                current_y = center_y if current_y is None else (current_y + center_y) / 2.0
            else:
                rows.append(current)
                current = [line]
                current_y = center_y
        if current:
            rows.append(current)
        tables.append(
            TableObject(
                locator=str(clip["locator"]),
                pdf_page=pdf_page,
                bbox=(x0, y0, x1, y1),
                start=min(line.start for row in rows for line in row),
                end=max(line.end for row in rows for line in row),
                rows=tuple(tuple(row) for row in rows),
            )
        )
    unique: dict[str, TableObject] = {}
    for table in sorted(tables, key=lambda item: (item.start, item.locator)):
        unique.setdefault(table.locator, table)
    return list(unique.values())


def _deepest_owner(
    start: int,
    end: int,
    ranges: Mapping[str, StructuralRange],
    parents: Mapping[str, str | None],
) -> str | None:
    candidates = [
        locator
        for locator, item in ranges.items()
        if locator != "document" and item.start <= start and end <= item.end
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda locator: _depth(locator, parents))


def _split_around_objects(
    interval: tuple[int, int],
    objects: Sequence[TableObject],
    *,
    emit_tables: bool = True,
) -> list[tuple[str, int, int, TableObject | None]]:
    start, end = interval
    blocked: list[tuple[int, int]] = []
    table_events: list[tuple[str, int, int, TableObject | None]] = []
    for obj in objects:
        relevant = [
            line
            for line in obj.source_lines
            if line.start < end and line.end > start
        ]
        if not relevant:
            continue
        blocked.extend(
            (max(start, line.start), min(end, line.end))
            for line in relevant
        )
        if emit_tables and start <= obj.start < end:
            table_events.append(("table", obj.start, obj.start, obj))

    merged: list[tuple[int, int]] = []
    for left, right in sorted(blocked):
        if not merged or left > merged[-1][1]:
            merged.append((left, right))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))

    text_parts: list[tuple[str, int, int, TableObject | None]] = []
    cursor = start
    for left, right in merged:
        if left > cursor:
            text_parts.append(("text", cursor, left, None))
        cursor = max(cursor, right)
    if cursor < end:
        text_parts.append(("text", cursor, end, None))

    return sorted(
        [*text_parts, *table_events],
        key=lambda item: (item[1], 0 if item[0] == "table" else 1, item[2]),
    )


def _table_node(stream: SourceStream, table: TableObject) -> dict[str, Any]:
    caption: SourceLine | None = None
    data_rows: list[tuple[SourceLine, ...]] = []
    for row in table.rows:
        remaining: list[SourceLine] = []
        for line in row:
            if caption is None and TABLE_CAPTION_RE.match(line.text.strip()):
                caption = line
            else:
                remaining.append(line)
        if remaining:
            data_rows.append(tuple(remaining))
    if caption is None:
        raise ValueError(f"table {table.locator} has no source-backed caption")

    children: list[dict[str, Any]] = [
        _make_leaf(
            stream,
            node_type="table_heading",
            locator=f"{table.locator}#heading",
            lines=[caption],
            attributes={
                "kind": "table_caption",
                "target_locator": table.locator,
            },
        )
    ]
    for row_index, row in enumerate(data_rows, start=1):
        cell_nodes = [
            _make_leaf(
                stream,
                node_type="table_cell",
                locator=f"{table.locator}#r{row_index}#c{column_index}",
                lines=[line],
                attributes={
                    "kind": "table_cell",
                    "row_index": str(row_index),
                    "column_index": str(column_index),
                },
            )
            for column_index, line in enumerate(row, start=1)
        ]
        row_start = min(cell["span"]["start"] for cell in cell_nodes)
        row_end = max(cell["span"]["end"] for cell in cell_nodes)
        children.append(
            _node(
                stream.text,
                node_type="table_row",
                locator=f"{table.locator}#r{row_index}",
                start=row_start,
                end=row_end,
                attributes={
                    "owns_source": "false",
                    "row_index": str(row_index),
                },
                children=cell_nodes,
            )
        )
    children.sort(key=lambda child: (child["span"]["start"], child["span"]["end"], child["locator"]))
    return _node(
        stream.text,
        node_type="table",
        locator=table.locator,
        start=table.start,
        end=table.end,
        label=caption.text.strip(),
        attributes={
            "owns_source": "false",
            "pdf_page": str(table.pdf_page),
            "bbox": json.dumps([round(value, 3) for value in table.bbox], separators=(",", ":")),
            "matrix_index": table.locator,
        },
        children=children,
    )


def _propagate_context(node: dict[str, Any], context: Mapping[str, str]) -> None:
    attrs = node.get("attributes", {})
    for key, value in context.items():
        attrs.setdefault(key, value)
    for child in node.get("children", []):
        _propagate_context(child, context)


def build_bundle(pdf_path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    source_sha = _sha256(pdf_path)
    if expected_sha256 and source_sha.lower() != expected_sha256.lower():
        raise RuntimeError(
            f"Source SHA-256 mismatch: expected {expected_sha256}, got {source_sha}"
        )
    hierarchy_module = _load_hierarchy_module()
    hierarchy = hierarchy_module.extract(pdf_path)
    nodes = _flatten_hierarchy(hierarchy["root"])
    pdf = _pdf_module()
    doc = pdf.open(pdf_path)
    first_page = int(hierarchy["source"]["nfpa13_first_pdf_page"])
    last_page = int(hierarchy["source"]["nfpa13_last_clause_pdf_page"])
    stream = build_source_stream_from_lines(raw_lines_from_document(doc, first_page, last_page))
    anchors = _find_anchors(nodes, stream)
    missing_explicit_anchors = sorted(
        locator
        for locator, node in nodes.items()
        if locator != "document"
        and node.get("attributes", {}).get("explicit") == "true"
        and locator not in anchors
    )
    if missing_explicit_anchors:
        doc.close()
        raise RuntimeError(f"Missing explicit clause anchors: {missing_explicit_anchors[:20]}")
    parents = {locator: node.get("parent") for locator, node in nodes.items()}
    ranges = compute_structural_ranges(parents, anchors, source_length=len(stream.text))
    if "document" not in ranges:
        ranges["document"] = StructuralRange(0, len(stream.text))
    tables = _extract_tables(doc, stream)
    table_index = TableSourceIndex.from_tables(tables)
    doc.close()
    table_owners: dict[str, list[TableObject]] = {}
    for table in tables:
        owner = _deepest_owner(table.start, table.end, ranges, parents)
        if owner:
            table_owners.setdefault(owner, []).append(table)

    def build_structural(locator: str) -> dict[str, Any]:
        meta = nodes[locator]
        item_range = ranges.get(locator)
        if item_range is None:
            raise RuntimeError(f"No structural range for {locator}")
        structural_children = [child for child in meta["children"] if child in ranges]
        child_ranges = [ranges[child] for child in structural_children]
        intervals = direct_intervals(item_range, child_ranges)
        block_nodes: list[dict[str, Any]] = []
        owner_tables = table_owners.get(locator, [])
        chapter = locator.split(".")[0]
        context: dict[str, str] = {"chapter": chapter}
        if locator[0].isalpha():
            context["annex"] = locator[0]
        if locator == "1.1":
            context["scope"] = "true"
        parse_counter = 0
        for interval in intervals:
            interval_start, interval_end = interval
            blocking_tables = table_index.overlapping(interval_start, interval_end)
            for kind, start, end, _ in _split_around_objects(
                interval,
                blocking_tables,
                emit_tables=False,
            ):
                if kind != "text" or start >= end:
                    continue
                parse_counter += 1
                blocks = parse_direct_blocks(
                    stream,
                    [(start, end)],
                    owner_locator=f"{locator}#segment{parse_counter}",
                    owner_heading=meta.get("label"),
                    owner_attributes=context,
                )
                for block in blocks:
                    _propagate_context(block, context)
                block_nodes.extend(blocks)
        for table in owner_tables:
            table_node = _table_node(stream, table)
            _propagate_context(table_node, context)
            block_nodes.append(table_node)
        children = [build_structural(child) for child in structural_children]
        children.extend(block_nodes)
        children.sort(key=lambda child: (child["span"]["start"], child["span"]["end"], child["locator"]))
        attrs = dict(meta.get("attributes", {}))
        attrs["owns_source"] = "false"
        attrs["parent_locator"] = str(meta.get("parent")) if meta.get("parent") else ""
        attrs["source_locations"] = _source_locations_for_span(stream, item_range.start, item_range.end)
        if meta.get("references"):
            attrs["hierarchy_references"] = json.dumps(meta["references"], separators=(",", ":"))
        return _node(
            stream.text,
            node_type=meta["type"],
            locator=locator,
            start=item_range.start,
            end=item_range.end,
            label=meta.get("label"),
            attributes=attrs,
            children=children,
        )

    root_meta = nodes["document"]
    structural_root_children = [build_structural(child) for child in root_meta["children"]]
    root_children = [
        *structural_root_children,
        *document_level_blocks(
            stream,
            [ranges[child] for child in root_meta["children"] if child in ranges],
        ),
    ]
    root_children.sort(key=lambda child: (child["span"]["start"], child["span"]["end"], child["locator"]))
    root = _node(
        stream.text,
        node_type="document",
        locator="document",
        start=0,
        end=len(stream.text),
        label=root_meta.get("label"),
        attributes={"owns_source": "false"},
        children=root_children,
    )
    all_nodes = list(_walk(root))
    known_locators = {node["locator"] for node in all_nodes}
    for node in all_nodes:
        target = node.get("attributes", {}).get("target_locator")
        if target:
            known_locators.add(target)
    known_locators.update(table.locator for table in tables)
    relations: list[dict[str, Any]] = []
    semantics: list[dict[str, Any]] = []
    for node in all_nodes:
        attrs = node.get("attributes", {})
        if attrs.get("owns_source") != "true":
            continue
        text = node["span"]["text"]
        base = node["span"]["start"]
        relations.extend(
            extract_relations(
                source_node_locator=node["locator"],
                text=text,
                base_offset=base,
                known_locators=known_locators,
            )
        )
        semantics.extend(
            classify_semantics(
                source_node_locator=node["locator"],
                text=text,
                base_offset=base,
                attributes=attrs,
            )
        )
    for locator, meta in nodes.items():
        if locator.startswith("A.") and meta.get("attributes", {}).get("corresponds_to"):
            relations.append(annex_a_relation(locator, known_locators))
    relations.sort(
        key=lambda item: (
            item["source_locator"],
            item["type"],
            item["target_locator"],
            -1 if item["evidence"] is None else item["evidence"]["start"],
        )
    )
    semantics.sort(key=lambda item: (item["source_locator"], item["evidence"]["start"], item["type"]))
    diagnostics = build_diagnostics(relations, all_nodes)
    table_payload = [
        {
            "locator": table.locator,
            "pdf_page": table.pdf_page,
            "bbox": [round(value, 3) for value in table.bbox],
            "span": _span(stream.text, table.start, table.end),
            "matrix": [list(row) for row in table.matrix],
        }
        for table in tables
    ]
    source_map = [
        {
            "start": line.start,
            "end": line.end,
            "pdf_page": line.pdf_page,
            "printed_page": line.printed_page,
            "column": line.column,
            "bbox": [round(value, 3) for value in line.bbox],
            "fonts": list(line.fonts),
            "sizes": [round(value, 3) for value in line.sizes],
        }
        for line in stream.lines
    ]
    bundle: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "source": {
            "artifact_id": ARTIFACT_ID,
            "edition_id": EDITION_ID,
            "title": "NFPA 13: Standard for the Installation of Sprinkler Systems",
            "file_name": pdf_path.name,
            "source_pdf_sha256": source_sha,
            "source_pdf_pages": hierarchy["source"]["source_pdf_pages"],
            "nfpa13_first_pdf_page": first_page,
            "nfpa13_last_clause_pdf_page": last_page,
        },
        "document_ast": {
            "ast_version": DOCUMENT_AST_VERSION,
            "type": "document_tree",
            "source_text": stream.text,
            "source_artifact": {"artifact_id": ARTIFACT_ID, "edition_id": EDITION_ID},
            "root": root,
            "diagnostics": diagnostics,
        },
        "relations": relations,
        "semantic_annotations": semantics,
        "tables": table_payload,
        "source_map": source_map,
        "statistics": {
            **hierarchy["statistics"],
            "source_lines": len(stream.lines),
            "source_characters": len(stream.text),
            "document_nodes": len(all_nodes),
            "owned_leaf_nodes": sum(
                node.get("attributes", {}).get("owns_source") == "true" for node in all_nodes
            ),
            "tables": len(tables),
            "relations": len(relations),
            "resolved_relations": sum(item["resolved"] for item in relations),
            "semantic_annotations": len(semantics),
            "diagnostics": len(diagnostics),
            "missing_explicit_anchors": len(missing_explicit_anchors),
        },
        "validation": {},
    }
    report = validate_bundle(bundle)
    bundle["validation"] = report
    if not report["passed"]:
        raise RuntimeError(f"NFPA 13 AST validation failed: {json.dumps(report, indent=2)}")
    return bundle


def write_validation_report(bundle: Mapping[str, Any], path: Path) -> None:
    validation = bundle["validation"]
    statistics = bundle["statistics"]
    lines = [
        "# NFPA 13 (2019) Source-Linked AST Validation",
        "",
        f"**Result:** {'PASS' if validation['passed'] else 'FAIL'}",
        "",
        "## Source",
        "",
        f"- SHA-256: `{bundle['source']['source_pdf_sha256']}`",
        (
            f"- NFPA 13 PDF range: {bundle['source']['nfpa13_first_pdf_page']}-"
            f"{bundle['source']['nfpa13_last_clause_pdf_page']}"
        ),
        "",
        "## Statistics",
        "",
    ]
    lines.extend(f"- {key.replace('_', ' ').title()}: {value}" for key, value in sorted(statistics.items()))
    lines.extend(["", "## Invariants", ""])
    for key, value in validation.items():
        if key == "passed":
            continue
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def overlay_rectangles_for_page(
    bundle: Mapping[str, Any],
    pdf_page: int,
) -> list[tuple[float, float, float, float]]:
    rectangles: list[tuple[float, float, float, float]] = []
    root = bundle.get("document_ast", {}).get("root", {})
    if not isinstance(root, Mapping):
        return rectangles
    for node in _walk(dict(root)):
        attributes = node.get("attributes", {})
        if not isinstance(attributes, Mapping) or attributes.get("owns_source") != "true":
            continue
        encoded = attributes.get("source_locations")
        if not isinstance(encoded, str):
            continue
        try:
            locations = json.loads(encoded)
        except json.JSONDecodeError:
            continue
        for location in locations:
            if not isinstance(location, Mapping) or location.get("pdf_page") != pdf_page:
                continue
            bbox = location.get("bbox")
            if (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(isinstance(value, (int, float)) for value in bbox)
            ):
                rectangles.append(tuple(float(value) for value in bbox))
    return sorted(set(rectangles), key=lambda rect: (rect[1], rect[0], rect[3], rect[2]))


def write_overlay_pages(
    pdf_path: Path,
    bundle: Mapping[str, Any],
    output_dir: Path,
    pages: Sequence[int],
) -> list[Path]:
    pdf = _pdf_module()
    doc = pdf.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pdf_page in pages:
        page = doc[pdf_page - 1]
        shape = page.new_shape()
        for bbox in overlay_rectangles_for_page(bundle, pdf_page):
            shape.draw_rect(pdf.Rect(bbox))
        shape.finish(color=(1, 0, 0), width=0.6)
        shape.commit()
        out = output_dir / f"nfpa13-2019-ast-overlay-p{pdf_page}.pdf"
        single = pdf.open()
        single.insert_pdf(doc, from_page=pdf_page - 1, to_page=pdf_page - 1)
        single.save(out)
        single.close()
        written.append(out)
    doc.close()
    return written


def _parse_pages(value: str) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            pages.extend(range(int(left), int(right) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, default=Path("nfpa13-2019-source-linked-ast.json"))
    parser.add_argument("--report", type=Path, default=Path("nfpa13-2019-source-linked-ast-validation.md"))
    parser.add_argument("--expected-sha256", default=EXPECTED_SOURCE_SHA256)
    parser.add_argument("--overlays-dir", type=Path)
    parser.add_argument("--overlay-pages", default="22,181,182,323,489,513")
    args = parser.parse_args()

    bundle = build_bundle(args.pdf, expected_sha256=args.expected_sha256 or None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(bundle) + b"\n")
    write_validation_report(bundle, args.report)
    if args.overlays_dir:
        write_overlay_pages(args.pdf, bundle, args.overlays_dir, _parse_pages(args.overlay_pages))
    print(json.dumps(bundle["statistics"], indent=2, sort_keys=True))
    print(args.output)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
