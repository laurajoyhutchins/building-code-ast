"""ASHRAE 62.1-2016 layout observations to generic Document AST.

This adapter begins after PDF region observation. It preserves the exact
retained publication identity, publication-native hierarchy, source roles,
coordinates, explicitly identified nonprose structures, and unsupported
graphical evidence without interpreting ventilation or compliance semantics.
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
from .pdf_layout import PdfBlock, PdfLine, normalize_block_text
from .structural_occurrences import LocatorOccurrence, group_locator_occurrences


ASHRAE_62_1_2016_PUBLICATION = PublicationState(
    publication_family="ANSI/ASHRAE Standard 62.1",
    edition="2016",
    addenda_set="a,c,d,e,f,g,h,i,j,k,p,q,r,s",
)
ASHRAE_62_1_2016_ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759",
    edition_id=ASHRAE_62_1_2016_PUBLICATION.publication_id,
)

_MANDATORY_APPENDICES = frozenset({"A", "B"})
_INFORMATIVE_APPENDICES = frozenset("CDEFGHIJK")
_TOP_SECTION_RE = re.compile(r"^(?P<locator>[1-9])\.\s+(?P<title>\S.*)$")
_SUBSECTION_RE = re.compile(r"^(?P<locator>\d+(?:\.\d+)+)\s+(?P<title>\S.*)$")
_APPENDIX_SECTION_RE = re.compile(
    r"^(?P<locator>[A-K]\d+(?:\.\d+)*)(?:\.)?\s+(?P<title>\S.*)$",
    re.IGNORECASE,
)
_APPENDIX_RE = re.compile(
    r"^(?P<role>NORMATIVE|INFORMATIVE)\s+APPENDIX\s+(?P<letter>[A-K])\b(?:\s+(?P<title>.*))?$",
    re.IGNORECASE,
)
_FOREWORD_RE = re.compile(r"^FOREWORD$", re.IGNORECASE)
_TABLE_RE = re.compile(r"^Table\s+(?P<locator>[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)\b", re.IGNORECASE)
_FIGURE_RE = re.compile(r"^Figure\s+(?P<locator>[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)\b", re.IGNORECASE)
_EQUATION_RE = re.compile(
    r"\((?P<locator>(?:[A-K]\d+(?:\.\d+)*(?:-\d+)?|[A-K]-\d+(?:-\d+)?|\d+(?:\.\d+)*(?:-\d+)?))\)\s*$",
    re.IGNORECASE,
)
_SUPPORTED_HINTS = {"equation", "table", "figure", "graphical_region"}
_BODY_MIDPOINT = 306.0
_TOP_CONTENT_Y = 30.0
_BOTTOM_CONTENT_Y = 750.0


@dataclass(frozen=True, slots=True)
class Ashrae621Observation:
    block: PdfBlock
    printed_page: str | None = None
    structure_hint: str | None = None
    native_locator: str | None = None

    def __post_init__(self) -> None:
        if self.structure_hint is not None and self.structure_hint not in _SUPPORTED_HINTS:
            raise ValueError(f"unsupported ASHRAE 62.1 observation hint: {self.structure_hint}")


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


def _is_content(observation: Ashrae621Observation) -> bool:
    _, y0, _, y1 = observation.block.bbox
    return y0 >= _TOP_CONTENT_Y and y1 <= _BOTTOM_CONTENT_Y


def _column(block: PdfBlock) -> int:
    x0, _, x1, _ = block.bbox
    if x0 < _BODY_MIDPOINT < x1:
        return 0
    if x0 < _BODY_MIDPOINT:
        return 1
    return 2


def _observation_key(observation: Ashrae621Observation) -> tuple[object, ...]:
    block = observation.block
    return (
        block.page_number,
        _column(block),
        block.bbox[1],
        block.bbox[0],
        block.bbox[3],
        block.bbox[2],
        normalize_block_text(block.text),
    )


def _attributes(observation: Ashrae621Observation, *, source_role: str) -> dict[str, str]:
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


def _coordinate_locator(kind: str, observation: Ashrae621Observation, text: str) -> str:
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


def _top_section_match(text: str) -> re.Match[str] | None:
    match = _TOP_SECTION_RE.match(text)
    if match is None:
        return None
    letters = [character for character in match.group("title") if character.isalpha()]
    if not letters or not all(character.isupper() for character in letters):
        return None
    return match


def _appendix_locator_depth(locator: str) -> int:
    return locator[1:].count(".")


def _appendix_section_match(text: str) -> re.Match[str] | None:
    match = _APPENDIX_SECTION_RE.match(text)
    if match is None:
        return None
    locator = match.group("locator").upper()
    if _appendix_locator_depth(locator) == 0:
        letters = [character for character in match.group("title") if character.isalpha()]
        if not letters or not all(character.isupper() for character in letters):
            return None
    return match


def _line_is_bold(line: PdfLine) -> bool:
    return any((span.flags & 16) != 0 or "bold" in span.font.lower() for span in line.spans)


def _line_is_structural_heading(line: PdfLine) -> bool:
    text = normalize_block_text(line.text)
    return _line_is_bold(line) and (
        _appendix_section_match(text) is not None or _SUBSECTION_RE.match(text) is not None
    )


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


def _expand_embedded_heading_observation(
    observation: Ashrae621Observation,
) -> tuple[Ashrae621Observation, ...]:
    block = observation.block
    if observation.structure_hint is not None or len(block.lines) < 2:
        return (observation,)

    heading_indexes = tuple(
        index for index, line in enumerate(block.lines) if _line_is_structural_heading(line)
    )
    if not heading_indexes or (len(heading_indexes) == 1 and heading_indexes[0] == 0):
        return (observation,)

    reconstructed = "\n".join(line.text for line in block.lines)
    if normalize_block_text(reconstructed) != normalize_block_text(block.text):
        return (observation,)

    ranges: list[tuple[int, int]] = []
    if heading_indexes[0] > 0:
        ranges.append((0, heading_indexes[0]))
    for position, start in enumerate(heading_indexes):
        end = heading_indexes[position + 1] if position + 1 < len(heading_indexes) else len(block.lines)
        ranges.append((start, end))

    return tuple(
        Ashrae621Observation(
            block=_derived_block(block, block.lines[start:end]),
            printed_page=observation.printed_page,
            structure_hint=observation.structure_hint,
            native_locator=observation.native_locator,
        )
        for start, end in ranges
    )


def _numbered_nonprose(
    observation: Ashrae621Observation,
    text: str,
) -> tuple[DocumentNodeType, str] | None:
    hint = observation.structure_hint
    native_locator = observation.native_locator.strip() if observation.native_locator else None

    if hint == "graphical_region":
        return None

    detected: tuple[DocumentNodeType, str] | None = None
    if match := _TABLE_RE.match(text):
        detected = (DocumentNodeType.TABLE, match.group("locator"))
    elif match := _FIGURE_RE.match(text):
        detected = (DocumentNodeType.FIGURE, match.group("locator"))
    elif "=" in text and (match := _EQUATION_RE.search(text)):
        detected = (DocumentNodeType.EQUATION, match.group("locator"))

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


def _table_occurrence_metadata(
    spans: tuple[tuple[Ashrae621Observation, int, int, str], ...],
) -> dict[int, tuple[object, int]]:
    occurrences: list[LocatorOccurrence] = []
    for source_order, (observation, _, _, text) in enumerate(spans):
        match = _TABLE_RE.match(text)
        native_locator: str | None = None
        if observation.structure_hint == "table":
            if observation.native_locator is not None:
                native_locator = observation.native_locator.strip()
            elif match is not None:
                native_locator = match.group("locator")
        elif observation.structure_hint is None and match is not None:
            native_locator = match.group("locator")
        if native_locator:
            occurrences.append(
                LocatorOccurrence(
                    native_locator=native_locator,
                    pdf_page=observation.block.page_number,
                    source_order=source_order,
                )
            )

    metadata: dict[int, tuple[object, int]] = {}
    for group in group_locator_occurrences(occurrences):
        for occurrence_index, occurrence in enumerate(group.occurrences):
            metadata[occurrence.source_order] = (group, occurrence_index)
    return metadata


def parse_ashrae621_2016_observations(
    observations: Iterable[Ashrae621Observation],
    *,
    source_artifact: DocumentSourceArtifact = ASHRAE_62_1_2016_ARTIFACT,
) -> DocumentAst:
    """Build a deterministic ASHRAE 62.1-2016 structural AST from PDF observations."""

    expanded = tuple(
        piece
        for observation in observations
        for piece in _expand_embedded_heading_observation(observation)
    )
    ordered = tuple(sorted((item for item in expanded if _is_content(item)), key=_observation_key))
    if not ordered:
        raise ValueError("ASHRAE 62.1-2016 observations must contain body-content regions")

    pieces: list[str] = []
    span_items: list[tuple[Ashrae621Observation, int, int, str]] = []
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
        span_items.append((observation, start, cursor, text))

    source_text = "".join(pieces)
    if not source_text:
        raise ValueError("ASHRAE 62.1-2016 observations contain no readable text")
    spans = tuple(span_items)
    table_metadata = _table_occurrence_metadata(spans)

    root = _Draft(DocumentNodeType.DOCUMENT, "document", 0, len(source_text))
    section_stack: list[_Draft] = []
    current_appendix: _Draft | None = None
    current_foreword: _Draft | None = None
    current_role = "mandatory"
    diagnostics: list[Diagnostic] = []

    def current_parent() -> _Draft:
        if section_stack:
            return section_stack[-1]
        if current_appendix is not None:
            return current_appendix
        if current_foreword is not None:
            return current_foreword
        return root

    def extend_open(end: int) -> None:
        root.extend_to(end)
        if current_appendix is not None:
            current_appendix.extend_to(end)
        if current_foreword is not None:
            current_foreword.extend_to(end)
        for section in section_stack:
            section.extend_to(end)

    for source_order, (observation, start, end, text) in enumerate(spans):
        if _FOREWORD_RE.fullmatch(text):
            foreword = _Draft(
                DocumentNodeType.SECTION,
                "foreword",
                start,
                end,
                label="Foreword",
                attributes=_attributes(observation, source_role="informative"),
            )
            root.children.append(foreword)
            current_foreword = foreword
            current_appendix = None
            section_stack = []
            current_role = "informative"
            continue

        if match := _APPENDIX_RE.match(text):
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
            current_foreword = None
            section_stack = []
            current_role = role
            continue

        appendix_match = (
            _appendix_section_match(text)
            if observation.structure_hint is None and current_appendix is not None
            else None
        )
        if appendix_match is not None:
            locator = appendix_match.group("locator").upper()
            appendix_letter = current_appendix.locator.removeprefix("appendix:")
            if locator.startswith(appendix_letter):
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
                    label=appendix_match.group("title"),
                    attributes=_attributes(observation, source_role=current_role),
                )
                parent = section_stack[-1] if section_stack else current_appendix
                parent.children.append(section)
                section_stack.append(section)
                extend_open(end)
                continue

        top_match = (
            _top_section_match(text)
            if observation.structure_hint is None and current_appendix is None
            else None
        )
        sub_match = (
            _SUBSECTION_RE.match(text)
            if observation.structure_hint is None and current_appendix is None
            else None
        )
        match = sub_match or top_match
        if match is not None:
            locator = match.group("locator")
            depth = locator.count(".")
            if depth == 0:
                current_appendix = None
                current_foreword = None
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
                label=match.group("title"),
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
            if node_type is DocumentNodeType.TABLE and source_order in table_metadata:
                group, occurrence_index = table_metadata[source_order]
                attrs["native_locator"] = native_locator
                attrs["occurrence_count"] = str(len(group.occurrences))
                attrs["occurrence_pattern"] = group.pattern.value
                attrs["occurrence_index"] = str(occurrence_index)
                if occurrence_index == 0:
                    locator = f"table:{native_locator}"
                    if len(group.occurrences) > 1:
                        diagnostics.append(
                            Diagnostic(
                                code="ashrae621-repeated-table-structure-deferred",
                                severity=DiagnosticSeverity.WARNING,
                                message=(
                                    "Repeated native table observations are preserved without "
                                    "asserting continuation or table-body semantics."
                                ),
                                span=SourceSpan(start=start, end=end, text=text),
                            )
                        )
                else:
                    node_type = DocumentNodeType.TABLE_HEADING
                    same_page_index = 1 + sum(
                        1
                        for prior in group.occurrences[:occurrence_index]
                        if prior.pdf_page == observation.block.page_number
                    )
                    locator = (
                        f"table-heading:{native_locator}:"
                        f"pdf-page-{observation.block.page_number}:"
                        f"occurrence-{same_page_index}"
                    )
            else:
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
                    code="unsupported-ashrae621-graphical-semantics",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Graphical source evidence is preserved, but its ventilation-standard "
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