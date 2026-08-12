"""ASCE/SEI 7-22 layout observations to generic Document AST.

This adapter deliberately begins after PDF region observation. It reconstructs
publication hierarchy and preserves equations, figures, tables, and graphical
regions without interpreting their engineering meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Iterable

from ..document_model import (
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from ..document_validation import validate_document_ast
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .pdf_layout import PdfBlock, normalize_block_text


_CHAPTER_RE = re.compile(r"^CHAPTER\s+(?P<number>\d+)\b(?:\s+(?P<title>.*))?$", re.IGNORECASE)
_SECTION_RE = re.compile(r"^(?P<locator>\d+\.\d+(?:\.\d+)*)\s+(?P<title>\S.*)$")
_EQUATION_RE = re.compile(r"\((?P<locator>\d+(?:\.\d+)*-\d+(?:\.SI)?)\)\s*$", re.IGNORECASE)
_TABLE_RE = re.compile(r"^Table\s+(?P<locator>\d+(?:\.\d+)*-\d+)\b", re.IGNORECASE)
_FIGURE_RE = re.compile(r"^Figure\s+(?P<locator>\d+(?:\.\d+)*-\d+)\b", re.IGNORECASE)
_SUPPORTED_HINTS = {"equation", "table", "figure", "graphical_region"}
_ASCE_BODY_MIDPOINT = 306.0
_ASCE_TOP_CONTENT_Y = 65.0
_ASCE_BOTTOM_CONTENT_Y = 750.0


@dataclass(frozen=True, slots=True)
class Asce7Observation:
    block: PdfBlock
    printed_page: str | None = None
    structure_hint: str | None = None
    native_locator: str | None = None
    section_declaration: bool | None = None

    def __post_init__(self) -> None:
        if self.structure_hint is not None and self.structure_hint not in _SUPPORTED_HINTS:
            raise ValueError(f"unsupported ASCE observation hint: {self.structure_hint}")


@dataclass(slots=True)
class _Draft:
    node_type: DocumentNodeType
    locator: str
    start: int
    end: int
    label: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    children: list["_Draft"] = field(default_factory=list)

    def extend_to(self, end: int) -> None:
        self.end = max(self.end, end)


def _is_content_observation(observation: Asce7Observation) -> bool:
    _, y0, _, y1 = observation.block.bbox
    return y0 >= _ASCE_TOP_CONTENT_Y and y1 <= _ASCE_BOTTOM_CONTENT_Y


def _column_for(block: PdfBlock) -> int:
    x0, _, x1, _ = block.bbox
    if x0 < _ASCE_BODY_MIDPOINT < x1:
        return 0
    if x0 < _ASCE_BODY_MIDPOINT:
        return 1
    return 2


def _observation_key(observation: Asce7Observation) -> tuple[object, ...]:
    """Return deterministic full-width, left-column, right-column reading order."""

    block = observation.block
    normalized = normalize_block_text(block.text)
    return (
        block.page_number,
        _column_for(block),
        block.bbox[1],
        block.bbox[0],
        block.bbox[3],
        block.bbox[2],
        normalized,
    )


def _attributes(observation: Asce7Observation) -> dict[str, str]:
    block = observation.block
    attrs = {
        "pdf_page": str(block.page_number),
        "coordinate_space": "pdf_points",
        "bbox_pdf_points": ",".join(f"{value:.3f}" for value in block.bbox),
        "extraction_block": str(block.block_number),
    }
    if observation.printed_page is not None:
        attrs["printed_page"] = observation.printed_page
    if observation.structure_hint == "graphical_region":
        attrs["semantic_status"] = "unsupported"
    return attrs


def _coordinate_locator(kind: str, observation: Asce7Observation, text: str) -> str:
    """Return an order-independent locator for source regions without native IDs."""

    block = observation.block
    bbox = "-".join(f"{value:.3f}" for value in block.bbox)
    text_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:pdf-page-{block.page_number}:bbox-{bbox}:sha256-{text_digest}"


def _numbered_structure(
    observation: Asce7Observation,
    text: str,
) -> tuple[DocumentNodeType, str] | None:
    """Recognize conservative publication-native equation/table/figure locators."""

    hint = observation.structure_hint
    native_locator = observation.native_locator.strip() if observation.native_locator else None

    if hint == "graphical_region":
        return None

    detected: tuple[DocumentNodeType, str] | None = None
    if match := _EQUATION_RE.search(text):
        detected = (DocumentNodeType.EQUATION, match.group("locator"))
    elif match := _TABLE_RE.match(text):
        detected = (DocumentNodeType.TABLE, match.group("locator"))
    elif match := _FIGURE_RE.match(text):
        detected = (DocumentNodeType.FIGURE, match.group("locator"))

    if hint in {"equation", "table", "figure"}:
        node_type = {
            "equation": DocumentNodeType.EQUATION,
            "table": DocumentNodeType.TABLE,
            "figure": DocumentNodeType.FIGURE,
        }[hint]
        locator = native_locator
        if locator is None and detected is not None and detected[0] is node_type:
            locator = detected[1]
        if locator is None:
            raise ValueError(f"{hint} observations require a publication-native locator")
        return node_type, locator

    if detected is not None:
        return detected
    return None


def _materialize(
    draft: _Draft,
    *,
    source_text: str,
    source_artifact: DocumentSourceArtifact,
) -> DocumentNode:
    return make_document_node(
        source_artifact=source_artifact,
        node_type=draft.node_type,
        locator=draft.locator,
        span=SourceSpan(
            start=draft.start,
            end=draft.end,
            text=source_text[draft.start : draft.end],
        ),
        label=draft.label,
        attributes=draft.attributes,
        children=tuple(
            _materialize(child, source_text=source_text, source_artifact=source_artifact)
            for child in draft.children
        ),
    )


def parse_asce7_22_observations(
    observations: Iterable[Asce7Observation],
    *,
    source_artifact: DocumentSourceArtifact,
) -> DocumentAst:
    """Build a deterministic structural AST from coordinate-bearing observations.

    Observation ordering is reconstructed from declared PDF coordinates rather
    than caller order. Structural IDs use publication locators when available;
    unnumbered source regions use declared page geometry and a content digest,
    never array or extraction-block position.
    """

    ordered = tuple(
        sorted(
            (observation for observation in observations if _is_content_observation(observation)),
            key=_observation_key,
        )
    )
    if not ordered:
        raise ValueError("ASCE 7-22 observations must contain at least one body-content region")

    pieces: list[str] = []
    spans: list[tuple[Asce7Observation, int, int, str]] = []
    cursor = 0
    for observation in ordered:
        text = normalize_block_text(observation.block.text)
        if not text:
            continue
        if pieces:
            pieces.append("\n")
            cursor += 1
        start = cursor
        pieces.append(text)
        cursor += len(text)
        spans.append((observation, start, cursor, text))

    source_text = "".join(pieces)
    if not source_text:
        raise ValueError("ASCE 7-22 observations contain no readable text")

    root = _Draft(DocumentNodeType.DOCUMENT, "document", 0, len(source_text))
    current_chapter: _Draft | None = None
    section_stack: list[_Draft] = []
    diagnostics: list[Diagnostic] = []

    def current_parent() -> _Draft:
        if section_stack:
            return section_stack[-1]
        if current_chapter is not None:
            return current_chapter
        return root

    def extend_open_ancestors(end: int) -> None:
        root.extend_to(end)
        if current_chapter is not None:
            current_chapter.extend_to(end)
        for section in section_stack:
            section.extend_to(end)

    for observation, start, end, text in spans:
        chapter_match = _CHAPTER_RE.match(text)
        if chapter_match:
            number = chapter_match.group("number")
            chapter = _Draft(
                DocumentNodeType.CHAPTER,
                f"chapter:{number}",
                start,
                end,
                label=(chapter_match.group("title") or None),
                attributes=_attributes(observation),
            )
            root.children.append(chapter)
            current_chapter = chapter
            section_stack = []
            continue

        section_match = (
            _SECTION_RE.match(text)
            if observation.structure_hint is None and observation.section_declaration is not False
            else None
        )
        if section_match:
            locator = section_match.group("locator")
            depth = locator.count(".")
            while section_stack and section_stack[-1].locator.removeprefix("section:").count(".") >= depth:
                section_stack.pop()
            node_type = DocumentNodeType.SECTION if depth == 1 else DocumentNodeType.SUBSECTION
            section = _Draft(
                node_type,
                f"section:{locator}",
                start,
                end,
                label=section_match.group("title"),
                attributes=_attributes(observation),
            )
            parent = section_stack[-1] if section_stack else (current_chapter or root)
            parent.children.append(section)
            section_stack.append(section)
            extend_open_ancestors(end)
            continue

        attrs = _attributes(observation)
        numbered = _numbered_structure(observation, text)
        if numbered is not None:
            node_type, native_locator = numbered
            locator = f"{node_type.value}:{native_locator}"
        elif observation.structure_hint == "graphical_region":
            node_type = DocumentNodeType.GRAPHICAL_REGION
            locator = _coordinate_locator("graphical", observation, text)
        else:
            node_type = DocumentNodeType.PARAGRAPH
            locator = _coordinate_locator("paragraph", observation, text)

        leaf = _Draft(node_type, locator, start, end, attributes=attrs)
        current_parent().children.append(leaf)
        extend_open_ancestors(end)

        if node_type is DocumentNodeType.GRAPHICAL_REGION:
            diagnostics.append(
                Diagnostic(
                    code="unsupported-asce-graphical-semantics",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Graphical source evidence is preserved, but its engineering semantics "
                        "have not been interpreted."
                    ),
                    span=SourceSpan(start=start, end=end, text=text),
                )
            )

    ast = DocumentAst(
        source_text=source_text,
        source_artifact=source_artifact,
        root=_materialize(root, source_text=source_text, source_artifact=source_artifact),
        diagnostics=tuple(diagnostics),
    )
    validate_document_ast(ast)
    return ast
