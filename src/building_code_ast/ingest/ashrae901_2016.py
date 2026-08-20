"""ASHRAE 90.1-2016 layout observations to generic Document AST.

This adapter begins after PDF region observation. It preserves publication-native
hierarchy, source roles, tables, equations, figures, coordinates, and explicit
unsupported graphical evidence without interpreting energy-code semantics.
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
from ..evidence.source_packages import PublicationState
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .pdf_layout import PdfBlock, PdfLine, PdfSpan, normalize_block_text


ASHRAE_90_1_2016_PUBLICATION = PublicationState(
    publication_family="ANSI/ASHRAE/IES Standard 90.1",
    edition="2016 I-P Edition",
    addenda_set="all addenda to Standard 90.1-2013 enumerated by retained Informative Appendix H",
)
ASHRAE_90_1_2016_ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162",
    edition_id=ASHRAE_90_1_2016_PUBLICATION.publication_id,
)

_MANDATORY_APPENDICES = frozenset({"A", "C", "G"})
_INFORMATIVE_APPENDICES = frozenset({"B", "D", "E", "F", "H"})
_NUMERIC_HEADING_RE = re.compile(
    r"^(?P<locator>\d+(?:\.\d+)*)(?:\.)?(?:\s+(?P<title>\S.*))?$"
)
_APPENDIX_HEADING_RE = re.compile(
    r"^(?P<locator>[A-H]\d+(?:\.\d+)*)(?:\.)?(?:\s+(?P<title>\S.*))?$",
    re.IGNORECASE,
)
_APPENDIX_RE = re.compile(
    r"^(?P<role>NORMATIVE|INFORMATIVE)\s+APPENDIX\s+(?P<letter>[A-H])\b(?:\s+(?P<title>.*))?$",
    re.IGNORECASE,
)
_TABLE_RE = re.compile(
    r"^Table\s+(?P<locator>[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)\b",
    re.IGNORECASE,
)
_FIGURE_RE = re.compile(
    r"^Figure\s+(?P<locator>[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)\b",
    re.IGNORECASE,
)
_EQUATION_RE = re.compile(r"\((?P<locator>\d+(?:\.\d+)*-\d+)\)\s*$")
_SUPPORTED_HINTS = {"equation", "table", "figure", "graphical_region"}
_BODY_MIDPOINT = 306.0
_TOP_CONTENT_Y = 65.0
_BOTTOM_CONTENT_Y = 730.0
_APPENDIX_HEADING_TOP_Y = 40.0
_HEADING_FONT = "Helvetica-Bold"
_TOP_HEADING_SIZE = 11.0
_SUBSECTION_HEADING_SIZE = 10.0
_HEADING_SIZE_TOLERANCE = 0.05
_FIGURE_CAPTION_FONT = "Helvetica-Bold"
_FIGURE_CAPTION_SIZE = 8.5
_FIGURE_CAPTION_SIZE_TOLERANCE = 0.05
_ANNEX1_LOCATOR_PREFIX = "annex1-"
_VERTICAL_UP_X_TOLERANCE = 0.01
_VERTICAL_UP_Y_THRESHOLD = -0.99


@dataclass(frozen=True, slots=True)
class Ashrae901Observation:
    block: PdfBlock
    printed_page: str | None = None
    structure_hint: str | None = None
    native_locator: str | None = None

    def __post_init__(self) -> None:
        if self.structure_hint is not None and self.structure_hint not in _SUPPORTED_HINTS:
            raise ValueError(f"unsupported ASHRAE 90.1 observation hint: {self.structure_hint}")


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


def _is_content(observation: Ashrae901Observation) -> bool:
    _, y0, _, y1 = observation.block.bbox
    return y0 >= _TOP_CONTENT_Y and y1 <= _BOTTOM_CONTENT_Y


def _column(block: PdfBlock) -> int:
    x0, _, x1, _ = block.bbox
    if x0 < _BODY_MIDPOINT < x1:
        return 0
    if x0 < _BODY_MIDPOINT:
        return 1
    return 2


def _first_text_span(block: PdfBlock) -> PdfSpan | None:
    for line in block.lines:
        for span in line.spans:
            if span.text.strip():
                return span
    return None


def _appendix_match(
    observation: Ashrae901Observation,
    text: str,
) -> re.Match[str] | None:
    """Recognize a publication appendix heading, not a TOC reference."""

    if observation.structure_hint is not None:
        return None
    match = _APPENDIX_RE.match(text)
    if match is None:
        return None
    span = _first_text_span(observation.block)
    if span is None or span.font != _HEADING_FONT:
        return None
    if abs(span.size - _TOP_HEADING_SIZE) > _HEADING_SIZE_TOLERANCE:
        return None
    return match


def _observation_key(observation: Ashrae901Observation) -> tuple[object, ...]:
    block = observation.block
    text = normalize_block_text(block.text)
    appendix_priority = 0 if _appendix_match(observation, text) is not None else 1
    return (
        block.page_number,
        appendix_priority,
        _column(block),
        block.bbox[1],
        block.bbox[0],
        block.bbox[3],
        block.bbox[2],
        text,
    )


def _attributes(observation: Ashrae901Observation, *, source_role: str) -> dict[str, str]:
    block = observation.block
    attrs = {
        "coordinate_space": "pdf_points",
        "text_coordinate_space": "normalized_observation_text",
        "pdf_page": str(block.page_number),
        "bbox_pdf_points": ",".join(f"{value:.3f}" for value in block.bbox),
        "extraction_block": str(block.block_number),
        "source_role": source_role,
    }
    if observation.printed_page is not None:
        attrs["printed_page"] = observation.printed_page
    if observation.structure_hint == "graphical_region":
        attrs["semantic_status"] = "unsupported"
    return attrs


def _coordinate_locator(kind: str, observation: Ashrae901Observation, text: str) -> str:
    block = observation.block
    bbox = "-".join(f"{value:.3f}" for value in block.bbox)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:pdf-page-{block.page_number}:bbox-{bbox}:sha256-{digest}"


def _appendix_role(letter: str, declared_role: str) -> str:
    normalized = declared_role.lower()
    expected = "mandatory" if letter in _MANDATORY_APPENDICES else "informative"
    if letter not in _MANDATORY_APPENDICES | _INFORMATIVE_APPENDICES:
        return "unresolved"
    declared = "mandatory" if normalized == "normative" else "informative"
    if declared != expected:
        raise ValueError(f"appendix {letter} is {expected} in the retained publication")
    return expected


def _numeric_heading(
    observation: Ashrae901Observation,
    text: str,
    *,
    inside_appendix: bool,
) -> tuple[str, str | None] | None:
    """Recognize body hierarchy only from exact-source heading typography."""

    if inside_appendix or observation.structure_hint is not None:
        return None
    match = _NUMERIC_HEADING_RE.fullmatch(text)
    if match is None:
        return None

    span = _first_text_span(observation.block)
    if span is None or span.font != _HEADING_FONT:
        return None

    locator = match.group("locator")
    title = match.group("title")
    depth = locator.count(".")
    expected_size = _TOP_HEADING_SIZE if depth == 0 else _SUBSECTION_HEADING_SIZE
    if abs(span.size - expected_size) > _HEADING_SIZE_TOLERANCE:
        return None
    if depth == 0 and title is None:
        return None
    return locator, title


def _appendix_heading(
    observation: Ashrae901Observation,
    text: str,
    *,
    appendix_letter: str | None,
) -> tuple[str, str | None] | None:
    """Recognize appendix-native hierarchy from exact-source heading typography."""

    if appendix_letter is None or observation.structure_hint is not None:
        return None
    match = _APPENDIX_HEADING_RE.fullmatch(text)
    if match is None:
        return None

    locator = match.group("locator").upper()
    if not locator.startswith(appendix_letter.upper()):
        return None

    span = _first_text_span(observation.block)
    if span is None or span.font != _HEADING_FONT:
        return None
    if abs(span.size - _SUBSECTION_HEADING_SIZE) > _HEADING_SIZE_TOLERANCE:
        return None
    return locator, match.group("title")


def _appendix_locator_depth(locator: str) -> int:
    return locator[1:].count(".")


def _line_appendix_heading(line: PdfLine) -> bool:
    text = normalize_block_text(line.text)
    if _APPENDIX_HEADING_RE.fullmatch(text) is None:
        return False
    span = next((span for span in line.spans if span.text.strip()), None)
    return (
        span is not None
        and span.font == _HEADING_FONT
        and abs(span.size - _SUBSECTION_HEADING_SIZE) <= _HEADING_SIZE_TOLERANCE
    )


def _appendix_heading_content(observation: Ashrae901Observation) -> bool:
    text = normalize_block_text(observation.block.text)
    if _APPENDIX_HEADING_RE.fullmatch(text) is None:
        return False
    span = _first_text_span(observation.block)
    if span is None or span.font != _HEADING_FONT:
        return False
    if abs(span.size - _SUBSECTION_HEADING_SIZE) > _HEADING_SIZE_TOLERANCE:
        return False
    _, y0, _, y1 = observation.block.bbox
    return y0 >= _APPENDIX_HEADING_TOP_Y and y1 <= _BOTTOM_CONTENT_Y


def _rotated_annex_figure_content(observation: Ashrae901Observation) -> bool:
    """Admit only the measured vertical-up Annex 1 figure-caption family."""

    if observation.structure_hint is not None:
        return False
    text = normalize_block_text(observation.block.text)
    match = _FIGURE_RE.match(text)
    if match is None or not match.group("locator").casefold().startswith(_ANNEX1_LOCATOR_PREFIX):
        return False
    span = _first_text_span(observation.block)
    if span is None or span.font != _FIGURE_CAPTION_FONT:
        return False
    if abs(span.size - _FIGURE_CAPTION_SIZE) > _FIGURE_CAPTION_SIZE_TOLERANCE:
        return False

    for line in observation.block.lines:
        if not line.text.strip():
            continue
        dx, dy = line.direction
        magnitude = (dx * dx + dy * dy) ** 0.5
        if magnitude <= 1e-9:
            continue
        if (
            abs(dx / magnitude) <= _VERTICAL_UP_X_TOLERANCE
            and dy / magnitude <= _VERTICAL_UP_Y_THRESHOLD
        ):
            return True
    return False


def _derived_block(block: PdfBlock, lines: tuple[PdfLine, ...]) -> PdfBlock:
    return PdfBlock(
        page_number=block.page_number,
        bbox=(
            min(line.bbox[0] for line in lines),
            min(line.bbox[1] for line in lines),
            max(line.bbox[2] for line in lines),
            max(line.bbox[3] for line in lines),
        ),
        text="\n".join(line.text for line in lines),
        block_number=block.block_number,
        table_region_id=block.table_region_id,
        lines=lines,
    )


def _expand_embedded_appendix_headings(
    observation: Ashrae901Observation,
) -> tuple[Ashrae901Observation, ...]:
    block = observation.block
    if observation.structure_hint is not None or len(block.lines) < 2:
        return (observation,)

    heading_indexes = tuple(
        index for index, line in enumerate(block.lines) if _line_appendix_heading(line)
    )
    if not heading_indexes:
        return (observation,)

    reconstructed = "\n".join(line.text for line in block.lines)
    if normalize_block_text(reconstructed) != normalize_block_text(block.text):
        return (observation,)

    ranges: list[tuple[int, int]] = []
    cursor = 0
    for index in heading_indexes:
        if cursor < index:
            ranges.append((cursor, index))
        ranges.append((index, index + 1))
        cursor = index + 1
    if cursor < len(block.lines):
        ranges.append((cursor, len(block.lines)))

    return tuple(
        Ashrae901Observation(
            block=_derived_block(block, block.lines[start:end]),
            printed_page=observation.printed_page,
            structure_hint=observation.structure_hint,
            native_locator=observation.native_locator,
        )
        for start, end in ranges
    )


def _expand_appendix_observations(
    observations: Iterable[Ashrae901Observation],
) -> tuple[Ashrae901Observation, ...]:
    raw = tuple(sorted(observations, key=_observation_key))
    expanded: list[Ashrae901Observation] = []
    inside_appendix = False
    for observation in raw:
        text = normalize_block_text(observation.block.text)
        if _appendix_match(observation, text) is not None:
            inside_appendix = True
            expanded.append(observation)
        elif inside_appendix:
            expanded.extend(_expand_embedded_appendix_headings(observation))
        else:
            expanded.append(observation)
    return tuple(
        sorted(
            (
                item
                for item in expanded
                if _is_content(item)
                or _rotated_annex_figure_content(item)
                or _appendix_heading_content(item)
                or _appendix_match(item, normalize_block_text(item.block.text)) is not None
            ),
            key=_observation_key,
        )
    )


def _automatic_figure_locator(
    observation: Ashrae901Observation,
    text: str,
) -> str | None:
    """Recognize automatic figure captions from retained source typography."""

    if observation.structure_hint is not None:
        return None
    match = _FIGURE_RE.match(text)
    if match is None:
        return None
    span = _first_text_span(observation.block)
    if span is None or span.font != _FIGURE_CAPTION_FONT:
        return None
    if abs(span.size - _FIGURE_CAPTION_SIZE) > _FIGURE_CAPTION_SIZE_TOLERANCE:
        return None
    return match.group("locator")


def _numbered_nonprose(
    observation: Ashrae901Observation,
    text: str,
) -> tuple[DocumentNodeType, str] | None:
    hint = observation.structure_hint
    native_locator = observation.native_locator.strip() if observation.native_locator else None

    if hint == "graphical_region":
        return None

    figure_match = _FIGURE_RE.match(text)
    detected: tuple[DocumentNodeType, str] | None = None
    if match := _TABLE_RE.match(text):
        detected = (DocumentNodeType.TABLE, match.group("locator"))
    elif figure_locator := _automatic_figure_locator(observation, text):
        detected = (DocumentNodeType.FIGURE, figure_locator)
    elif match := _EQUATION_RE.search(text):
        detected = (DocumentNodeType.EQUATION, match.group("locator"))

    if hint in {"equation", "table", "figure"}:
        node_type = {
            "equation": DocumentNodeType.EQUATION,
            "table": DocumentNodeType.TABLE,
            "figure": DocumentNodeType.FIGURE,
        }[hint]
        locator = native_locator
        if locator is None and hint == "figure" and figure_match is not None:
            locator = figure_match.group("locator")
        if locator is None and detected is not None and detected[0] is node_type:
            locator = detected[1]
        if locator is None:
            raise ValueError(f"{hint} observations require a publication-native locator")
        return node_type, locator

    return detected


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


def parse_ashrae901_2016_observations(
    observations: Iterable[Ashrae901Observation],
    *,
    source_artifact: DocumentSourceArtifact = ASHRAE_90_1_2016_ARTIFACT,
) -> DocumentAst:
    """Build a deterministic ASHRAE 90.1-2016 structural AST from PDF observations."""

    ordered = _expand_appendix_observations(observations)
    if not ordered:
        raise ValueError("ASHRAE 90.1-2016 observations must contain body-content regions")

    pieces: list[str] = []
    spans: list[tuple[Ashrae901Observation, int, int, str]] = []
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
        raise ValueError("ASHRAE 90.1-2016 observations contain no readable text")

    root = _Draft(DocumentNodeType.DOCUMENT, "document", 0, len(source_text))
    section_stack: list[_Draft] = []
    current_appendix: _Draft | None = None
    current_role = "mandatory"
    diagnostics: list[Diagnostic] = []

    def current_parent() -> _Draft:
        if section_stack:
            return section_stack[-1]
        if current_appendix is not None:
            return current_appendix
        return root

    def extend_open(end: int) -> None:
        root.extend_to(end)
        if current_appendix is not None:
            current_appendix.extend_to(end)
        for section in section_stack:
            section.extend_to(end)

    for observation, start, end, text in spans:
        if match := _appendix_match(observation, text):
            letter = match.group("letter").upper()
            role = _appendix_role(letter, match.group("role"))
            appendix = _Draft(
                DocumentNodeType.SECTION,
                f"appendix:{letter}",
                start,
                end,
                label=(match.group("title") or None),
                attributes=_attributes(observation, source_role=role),
            )
            root.children.append(appendix)
            current_appendix = appendix
            section_stack = []
            current_role = role
            continue

        appendix_letter = (
            current_appendix.locator.removeprefix("appendix:")
            if current_appendix is not None
            else None
        )
        appendix_heading = _appendix_heading(
            observation,
            text,
            appendix_letter=appendix_letter,
        )
        if appendix_heading is not None:
            locator, title = appendix_heading
            depth = _appendix_locator_depth(locator)
            while (
                section_stack
                and _appendix_locator_depth(section_stack[-1].locator.removeprefix("section:"))
                >= depth
            ):
                section_stack.pop()
            section = _Draft(
                DocumentNodeType.SUBSECTION,
                f"section:{locator}",
                start,
                end,
                label=title,
                attributes=_attributes(observation, source_role=current_role),
            )
            parent = section_stack[-1] if section_stack else current_appendix
            if parent is None:
                raise AssertionError("appendix heading requires an active appendix")
            parent.children.append(section)
            section_stack.append(section)
            extend_open(end)
            continue

        heading = _numeric_heading(
            observation,
            text,
            inside_appendix=current_appendix is not None,
        )
        if heading is not None:
            locator, title = heading
            depth = locator.count(".")
            if depth == 0:
                section_stack = []
                current_role = "mandatory"
                node_type = DocumentNodeType.SECTION
            else:
                while section_stack and section_stack[-1].locator.removeprefix("section:").count(".") >= depth:
                    section_stack.pop()
                node_type = DocumentNodeType.SUBSECTION
            section = _Draft(
                node_type,
                f"section:{locator}",
                start,
                end,
                label=title,
                attributes=_attributes(observation, source_role=current_role),
            )
            parent = section_stack[-1] if section_stack else root
            parent.children.append(section)
            section_stack.append(section)
            extend_open(end)
            continue

        attrs = _attributes(observation, source_role=current_role)
        numbered = _numbered_nonprose(observation, text)
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
        extend_open(end)

        if node_type is DocumentNodeType.GRAPHICAL_REGION:
            diagnostics.append(
                Diagnostic(
                    code="unsupported-ashrae901-graphical-semantics",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Graphical source evidence is preserved, but its energy-code semantics "
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
