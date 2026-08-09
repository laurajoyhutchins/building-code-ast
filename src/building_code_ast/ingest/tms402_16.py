"""TMS 402-16 source observations to generic Document AST.

The retained TMS 402/602-16 artifact is image-based and presents normative
TMS 402 text beside informational commentary. This adapter deliberately begins
after source-region observation and OCR. Callers must declare source role and
text origin instead of asking the parser to infer authority from flattened OCR.
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


_TMS402_COMPONENT_ID = "tms-402-16"
_PART_RE = re.compile(r"^PART\s+(?P<number>\d+)\s*:\s*(?P<title>\S.*)$", re.IGNORECASE)
_CHAPTER_RE = re.compile(
    r"^CHAPTER\s+(?P<number>\d+)\b(?:\s+(?P<title>\S.*))?$",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(
    r"^(?P<locator>\d+(?:\.\d+)+)\s*(?:[-\u2013\u2014]\s*)?(?P<title>\S.*)?$"
)
_SUPPORTED_ROLES = {"normative", "commentary"}
_SUPPORTED_TEXT_ORIGINS = {"ocr", "embedded"}
_SUPPORTED_HINTS = {"equation", "table", "figure", "graphical_region"}
_TOP_CONTENT_Y = 65.0
_BOTTOM_CONTENT_Y = 750.0
_BODY_MIDPOINT = 306.0


@dataclass(frozen=True, slots=True)
class Tms402Observation:
    """One coordinate-bearing source observation for the TMS 402 component."""

    block: PdfBlock
    printed_page: str | None = None
    source_role: str = "normative"
    text_origin: str = "ocr"
    structure_hint: str | None = None
    native_locator: str | None = None

    def __post_init__(self) -> None:
        if self.source_role not in _SUPPORTED_ROLES:
            raise ValueError(f"unsupported TMS 402 source role: {self.source_role}")
        if self.text_origin not in _SUPPORTED_TEXT_ORIGINS:
            raise ValueError(f"unsupported TMS 402 text origin: {self.text_origin}")
        if self.structure_hint is not None and self.structure_hint not in _SUPPORTED_HINTS:
            raise ValueError(f"unsupported TMS 402 observation hint: {self.structure_hint}")
        if self.native_locator is not None and not self.native_locator.strip():
            raise ValueError("TMS 402 native locator must not be empty")


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


def _is_body_observation(observation: Tms402Observation) -> bool:
    _, y0, _, y1 = observation.block.bbox
    return y0 >= _TOP_CONTENT_Y and y1 <= _BOTTOM_CONTENT_Y


def _column_for(block: PdfBlock) -> int:
    x0, _, x1, _ = block.bbox
    if x0 < _BODY_MIDPOINT < x1:
        return 0
    if x0 < _BODY_MIDPOINT:
        return 1
    return 2


def _observation_key(observation: Tms402Observation) -> tuple[object, ...]:
    block = observation.block
    return (
        block.page_number,
        _column_for(block),
        block.bbox[1],
        block.bbox[0],
        block.bbox[3],
        block.bbox[2],
        observation.source_role,
        normalize_block_text(block.text),
    )


def _attributes(observation: Tms402Observation) -> dict[str, str]:
    block = observation.block
    attrs = {
        "pdf_page": str(block.page_number),
        "coordinate_space": "pdf_points",
        "bbox_pdf_points": ",".join(f"{value:.3f}" for value in block.bbox),
        "extraction_block": str(block.block_number),
        "source_role": observation.source_role,
        "text_origin": observation.text_origin,
    }
    if observation.printed_page is not None:
        attrs["printed_page"] = observation.printed_page
    if observation.native_locator is not None:
        attrs["native_locator"] = observation.native_locator
    if observation.structure_hint == "graphical_region":
        attrs["semantic_status"] = "unsupported"
    return attrs


def _coordinate_locator(kind: str, observation: Tms402Observation, text: str) -> str:
    block = observation.block
    bbox = "-".join(f"{value:.3f}" for value in block.bbox)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return (
        f"{kind}:{observation.source_role}:pdf-page-{block.page_number}:"
        f"bbox-{bbox}:sha256-{digest}"
    )


def _hinted_structure(
    observation: Tms402Observation,
    text: str,
) -> tuple[DocumentNodeType, str] | None:
    hint = observation.structure_hint
    if hint is None or hint == "graphical_region":
        return None
    if observation.native_locator is None:
        raise ValueError(f"{hint} observations require a publication-native locator")
    node_type = {
        "equation": DocumentNodeType.EQUATION,
        "table": DocumentNodeType.TABLE,
        "figure": DocumentNodeType.FIGURE,
    }[hint]
    return node_type, observation.native_locator


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


def parse_tms402_16_observations(
    observations: Iterable[Tms402Observation],
    *,
    source_artifact: DocumentSourceArtifact,
) -> DocumentAst:
    """Build a deterministic TMS 402-16 structural AST from source observations."""

    if source_artifact.publication_component_id != _TMS402_COMPONENT_ID:
        raise ValueError(
            "TMS 402-16 parsing requires publication_component_id='tms-402-16'"
        )

    ordered = tuple(
        sorted(
            (observation for observation in observations if _is_body_observation(observation)),
            key=_observation_key,
        )
    )
    if not ordered:
        raise ValueError("TMS 402-16 observations must contain body-content regions")

    pieces: list[str] = []
    spans: list[tuple[Tms402Observation, int, int, str]] = []
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
        raise ValueError("TMS 402-16 observations contain no readable text")

    root = _Draft(DocumentNodeType.DOCUMENT, "document", 0, len(source_text))
    current_part: _Draft | None = None
    current_chapter: _Draft | None = None
    section_stack: list[_Draft] = []
    sections_by_native_locator: dict[str, _Draft] = {}
    diagnostics: list[Diagnostic] = []

    def current_parent() -> _Draft:
        if section_stack:
            return section_stack[-1]
        if current_chapter is not None:
            return current_chapter
        if current_part is not None:
            return current_part
        return root

    def extend_ancestors(parent: _Draft, end: int) -> None:
        root.extend_to(end)
        if current_part is not None:
            current_part.extend_to(end)
        if current_chapter is not None:
            current_chapter.extend_to(end)
        for section in section_stack:
            section.extend_to(end)
        parent.extend_to(end)

    for observation, start, end, text in spans:
        if observation.source_role == "normative" and observation.structure_hint is None:
            if match := _PART_RE.match(text):
                part = _Draft(
                    DocumentNodeType.HEADING,
                    f"part:{match.group('number')}",
                    start,
                    end,
                    label=match.group("title"),
                    attributes={**_attributes(observation), "hierarchy_role": "part"},
                )
                root.children.append(part)
                current_part = part
                current_chapter = None
                section_stack = []
                continue

            if match := _CHAPTER_RE.match(text):
                chapter = _Draft(
                    DocumentNodeType.CHAPTER,
                    f"chapter:{match.group('number')}",
                    start,
                    end,
                    label=match.group("title") or None,
                    attributes=_attributes(observation),
                )
                (current_part or root).children.append(chapter)
                current_chapter = chapter
                section_stack = []
                extend_ancestors(current_part or root, end)
                continue

            if match := _SECTION_RE.match(text):
                native_locator = match.group("locator")
                depth = native_locator.count(".")
                while (
                    section_stack
                    and section_stack[-1].locator.removeprefix("section:").count(".") >= depth
                ):
                    section_stack.pop()
                section = _Draft(
                    DocumentNodeType.SECTION if depth == 1 else DocumentNodeType.SUBSECTION,
                    f"section:{native_locator}",
                    start,
                    end,
                    label=match.group("title") or None,
                    attributes={
                        **_attributes(observation),
                        "native_locator": native_locator,
                    },
                )
                parent = section_stack[-1] if section_stack else (current_chapter or current_part or root)
                parent.children.append(section)
                section_stack.append(section)
                sections_by_native_locator[native_locator] = section
                extend_ancestors(parent, end)
                continue

        attrs = _attributes(observation)
        hinted = _hinted_structure(observation, text)
        if hinted is not None:
            node_type, native_locator = hinted
            locator = f"{node_type.value}:{native_locator}"
        elif observation.structure_hint == "graphical_region":
            node_type = DocumentNodeType.GRAPHICAL_REGION
            locator = _coordinate_locator("graphical", observation, text)
        else:
            node_type = DocumentNodeType.PARAGRAPH
            locator = _coordinate_locator("paragraph", observation, text)

        if observation.source_role == "commentary" and observation.native_locator is not None:
            parent = sections_by_native_locator.get(observation.native_locator)
            if parent is None:
                parent = current_part or root
                diagnostics.append(
                    Diagnostic(
                        code="unresolved-tms402-commentary-locator",
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            "Commentary source evidence was preserved, but its declared native "
                            "locator did not resolve to a parsed TMS 402 section."
                        ),
                        span=SourceSpan(start=start, end=end, text=text),
                    )
                )
        else:
            parent = current_parent()

        leaf = _Draft(node_type, locator, start, end, attributes=attrs)
        parent.children.append(leaf)
        extend_ancestors(parent, end)

        if node_type is DocumentNodeType.GRAPHICAL_REGION:
            diagnostics.append(
                Diagnostic(
                    code="unsupported-tms402-graphical-semantics",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Graphical TMS 402 source evidence is preserved, but its engineering "
                        "semantics have not been interpreted."
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
