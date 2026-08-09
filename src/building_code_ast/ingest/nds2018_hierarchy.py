"""Conservative NDS 2018 publication hierarchy over positioned layout evidence.

This stage recognizes chapters, decimal sections, appendices, structural
definition entries, ordinary prose/lists, and source-role transitions. Equation,
table, figure, and graphical engineering structure is deliberately deferred to
the next compiler stage.
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
from .nds2018_layout import (
    NDS_2018_ARTIFACT_ID,
    NDS_2018_EDITION_ID,
    NdsLayoutEvidence,
    NdsLayoutPage,
)
from .pdf_layout import PdfBlock, normalize_block_text


_APPENDIX_RE = re.compile(
    r"^Appendix\s+(?P<letter>[A-N])\s+\((?P<role>Non-mandatory|Mandatory)\)\s+(?P<title>\S.*)$",
    re.IGNORECASE,
)
_AMBIGUOUS_APPENDIX_RE = re.compile(
    r"^Appendix\s+\((?:Non-mandatory|Mandatory)\)\b",
    re.IGNORECASE,
)
_NUMERIC_TOKEN_RE = re.compile(r"(?<![\w.])(?P<locator>\d{1,2}(?:\.\d+){1,3})(?![\d.])")
_ANCHOR_RE = re.compile(
    r"(?P<locator>(?:\d{1,2}(?:\.\d+){1,3}|[A-N]\.\d+(?:\.\d+){0,2}))\s+(?=[A-Z])"
)
_LIST_RE = re.compile(r"^(?:\([A-Za-z0-9]+\)|[-•])\s+\S")
_PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
_DEFINITION_LABEL_RE = re.compile(r"^Definitions?$", re.IGNORECASE)
_REFERENCES_RE = re.compile(r"^REFERENCES$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _ObservedBlock:
    page: NdsLayoutPage
    block: PdfBlock
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class _Segment:
    observation: _ObservedBlock
    start: int
    end: int
    text: str
    locator: str | None = None


@dataclass(slots=True)
class _Draft:
    node_type: DocumentNodeType
    locator: str
    start: int
    end: int
    label: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    children: list["_Draft"] = field(default_factory=list)
    native_locator: str | None = None

    def extend_to(self, end: int) -> None:
        self.end = max(self.end, end)


def _canonical_blocks(evidence: NdsLayoutEvidence) -> tuple[str, tuple[_ObservedBlock, ...]]:
    pieces: list[str] = []
    observations: list[_ObservedBlock] = []
    cursor = 0
    for page in sorted(evidence.pages, key=lambda item: item.page_number):
        for block in page.ordered_blocks:
            text = normalize_block_text(block.text)
            if not text:
                continue
            if pieces:
                pieces.append("\n")
                cursor += 1
            start = cursor
            pieces.append(text)
            cursor += len(text)
            observations.append(_ObservedBlock(page, block, start, cursor, text))
    source_text = "".join(pieces)
    if not source_text:
        raise ValueError("NDS 2018 layout evidence contains no readable retained text")
    return source_text, tuple(observations)


def _is_upper_title(text: str, block: PdfBlock, page: NdsLayoutPage) -> bool:
    if any(character.isdigit() for character in text) or _PRIVATE_USE_RE.search(text):
        return False
    if text.casefold().startswith("appendix") or _REFERENCES_RE.match(text):
        return False
    letters = [character for character in text if character.isalpha()]
    if len(letters) < 5:
        return False
    upper_ratio = sum(character.isupper() for character in letters) / len(letters)
    x0, y0, x1, _ = block.bbox
    return (
        upper_ratio >= 0.85
        and 70.0 <= y0 <= 330.0
        and x0 >= page.width * 0.15
        and x1 <= page.width * 0.85
    )


def _chapter_number_from_page(page: NdsLayoutPage) -> str | None:
    counts: dict[str, set[str]] = {}
    for block in page.ordered_blocks:
        text = normalize_block_text(block.text)
        for match in _NUMERIC_TOKEN_RE.finditer(text):
            locator = match.group("locator")
            chapter = locator.split(".", 1)[0]
            counts.setdefault(chapter, set()).add(locator)
    candidates = [chapter for chapter, locators in counts.items() if len(locators) >= 2]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _chapter_openers(pages: Iterable[NdsLayoutPage]) -> dict[int, tuple[str, PdfBlock, str]]:
    result: dict[int, tuple[str, PdfBlock, str]] = {}
    for page in pages:
        chapter = _chapter_number_from_page(page)
        if chapter is None:
            continue
        titles = [
            (block.bbox[1], block)
            for block in page.ordered_blocks
            if (text := normalize_block_text(block.text)) and _is_upper_title(text, block, page)
        ]
        if not titles:
            continue
        _, block = min(titles, key=lambda item: (item[0], item[1].bbox[0]))
        result[page.page_number] = (chapter, block, normalize_block_text(block.text))
    return result


def _attributes(observation: _ObservedBlock, *, source_role: str | None = None) -> dict[str, str]:
    block = observation.block
    attrs = {
        "pdf_page": str(block.page_number),
        "coordinate_space": "pdf_points",
        "bbox_pdf_points": ",".join(f"{value:.3f}" for value in block.bbox),
        "page_role": observation.page.page_role.value,
    }
    if observation.page.printed_page is not None:
        attrs["printed_page"] = observation.page.printed_page
    if source_role is not None:
        attrs["source_role"] = source_role
    return attrs


def _coordinate_locator(kind: str, observation: _ObservedBlock, text: str) -> str:
    bbox = "-".join(f"{value:.3f}" for value in observation.block.bbox)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:pdf-page-{observation.block.page_number}:bbox-{bbox}:sha256-{digest}"


def _locator_depth(locator: str) -> int:
    return locator.count(".")


def _anchor_allowed(locator: str, *, chapter: str | None, appendix: str | None) -> bool:
    if appendix is not None:
        return locator.startswith(f"{appendix}.")
    if chapter is not None and locator[0].isdigit():
        return locator.split(".", 1)[0] == chapter
    return False


def _anchor_matches(
    text: str,
    *,
    chapter: str | None,
    appendix: str | None,
) -> tuple[re.Match[str], ...]:
    matches: list[re.Match[str]] = []
    for match in _ANCHOR_RE.finditer(text):
        locator = match.group("locator")
        if not _anchor_allowed(locator, chapter=chapter, appendix=appendix):
            continue
        if match.start("locator") != 0:
            prefix = text[: match.start("locator")].rstrip()
            if not prefix or prefix[-1] not in ".!?":
                continue
        matches.append(match)
    return tuple(matches)


def _segments_for_block(
    observation: _ObservedBlock,
    *,
    chapter: str | None,
    appendix: str | None,
) -> tuple[_Segment, ...]:
    matches = _anchor_matches(observation.text, chapter=chapter, appendix=appendix)
    if not matches:
        return (_Segment(observation, observation.start, observation.end, observation.text),)
    segments: list[_Segment] = []
    if matches[0].start("locator") > 0:
        prefix = observation.text[: matches[0].start("locator")].rstrip()
        if prefix:
            segments.append(
                _Segment(
                    observation,
                    observation.start,
                    observation.start + len(prefix),
                    prefix,
                )
            )
    for index, match in enumerate(matches):
        local_start = match.start("locator")
        local_end = matches[index + 1].start("locator") if index + 1 < len(matches) else len(observation.text)
        raw = observation.text[local_start:local_end].strip()
        leading = len(observation.text[local_start:local_end]) - len(observation.text[local_start:local_end].lstrip())
        absolute_start = observation.start + local_start + leading
        absolute_end = absolute_start + len(raw)
        segments.append(
            _Segment(
                observation,
                absolute_start,
                absolute_end,
                raw,
                locator=match.group("locator"),
            )
        )
    return tuple(segments)


def _looks_like_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > 90:
        return False
    return stripped[-1] not in ".;:!?"


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
        span=SourceSpan(start=draft.start, end=draft.end, text=source_text[draft.start : draft.end]),
        label=draft.label,
        attributes=draft.attributes,
        children=tuple(
            _materialize(child, source_text=source_text, source_artifact=source_artifact)
            for child in draft.children
        ),
    )


def parse_nds2018_hierarchy(evidence: NdsLayoutEvidence) -> DocumentAst:
    """Build a source-backed NDS hierarchy without non-prose semantic promotion."""

    if (
        evidence.ast_source.artifact_id != NDS_2018_ARTIFACT_ID
        or evidence.ast_source.edition_id != NDS_2018_EDITION_ID
    ):
        raise ValueError("NDS hierarchy requires exact registered NDS 2018 source identity")

    source_text, observations = _canonical_blocks(evidence)
    openers = _chapter_openers(evidence.pages)
    source_artifact = DocumentSourceArtifact(
        artifact_id=evidence.ast_source.artifact_id,
        edition_id=evidence.ast_source.edition_id,
    )
    root = _Draft(DocumentNodeType.DOCUMENT, "document", 0, len(source_text))
    current_chapter: _Draft | None = None
    current_chapter_number: str | None = None
    current_appendix: _Draft | None = None
    current_appendix_letter: str | None = None
    section_stack: list[_Draft] = []
    active_definition: _Draft | None = None
    ambiguous_appendix = False
    in_references = False
    diagnostics: list[Diagnostic] = []

    def structural_parent() -> _Draft:
        if active_definition is not None:
            return active_definition
        if section_stack:
            return section_stack[-1]
        if current_appendix is not None:
            return current_appendix
        if current_chapter is not None:
            return current_chapter
        return root

    def extend_context(end: int) -> None:
        root.extend_to(end)
        if current_chapter is not None:
            current_chapter.extend_to(end)
        if current_appendix is not None:
            current_appendix.extend_to(end)
        for section in section_stack:
            section.extend_to(end)
        if active_definition is not None:
            active_definition.extend_to(end)

    def add_leaf(
        node_type: DocumentNodeType,
        segment: _Segment,
        *,
        parent: _Draft | None = None,
        label: str | None = None,
        source_role: str | None = None,
        locator_kind: str | None = None,
    ) -> _Draft:
        target = parent or structural_parent()
        locator = _coordinate_locator(locator_kind or node_type.value, segment.observation, segment.text)
        node = _Draft(
            node_type,
            locator,
            segment.start,
            segment.end,
            label=label,
            attributes=_attributes(segment.observation, source_role=source_role),
        )
        target.children.append(node)
        extend_context(segment.end)
        return node

    opener_by_block: dict[tuple[int, int], tuple[str, str]] = {}
    opener_pages: set[int] = set()
    for page_number, (chapter, block, title) in openers.items():
        opener_by_block[(page_number, block.block_number)] = (chapter, title)
        opener_pages.add(page_number)

    for observation in observations:
        text = observation.text
        opener = opener_by_block.get((observation.block.page_number, observation.block.block_number))
        if opener is not None:
            chapter_number, title = opener
            current_appendix = None
            current_appendix_letter = None
            section_stack = []
            active_definition = None
            ambiguous_appendix = False
            in_references = False
            chapter = _Draft(
                DocumentNodeType.CHAPTER,
                f"chapter:{chapter_number}",
                observation.start,
                observation.end,
                label=title,
                attributes=_attributes(observation, source_role="mandatory"),
                native_locator=chapter_number,
            )
            root.children.append(chapter)
            current_chapter = chapter
            current_chapter_number = chapter_number
            continue

        if observation.block.page_number in opener_pages and current_chapter is not None:
            segment = _Segment(observation, observation.start, observation.end, text)
            add_leaf(
                DocumentNodeType.NOTE,
                segment,
                parent=current_chapter,
                source_role="chapter_contents",
                locator_kind="chapter-contents",
            )
            continue

        appendix_match = _APPENDIX_RE.match(text)
        if appendix_match:
            letter = appendix_match.group("letter").upper()
            raw_role = appendix_match.group("role").casefold()
            source_role = "non_mandatory" if raw_role.startswith("non-") else "mandatory"
            current_chapter = None
            current_chapter_number = None
            section_stack = []
            active_definition = None
            ambiguous_appendix = False
            in_references = False
            appendix = _Draft(
                DocumentNodeType.APPENDIX,
                f"appendix:{letter}",
                observation.start,
                observation.end,
                label=appendix_match.group("title").strip(),
                attributes=_attributes(observation, source_role=source_role),
                native_locator=letter,
            )
            root.children.append(appendix)
            current_appendix = appendix
            current_appendix_letter = letter
            continue

        if _AMBIGUOUS_APPENDIX_RE.match(text):
            current_chapter = None
            current_chapter_number = None
            current_appendix = None
            current_appendix_letter = None
            section_stack = []
            active_definition = None
            ambiguous_appendix = True
            in_references = False
            segment = _Segment(observation, observation.start, observation.end, text)
            node = add_leaf(
                DocumentNodeType.UNSUPPORTED,
                segment,
                parent=root,
                source_role="unresolved_appendix",
                locator_kind="unsupported-appendix",
            )
            diagnostics.append(
                Diagnostic(
                    code="nds-appendix-locator-unresolved",
                    severity=DiagnosticSeverity.WARNING,
                    message="Appendix source role is visible but the publication-native appendix locator is absent from extracted text.",
                    span=SourceSpan(start=node.start, end=node.end, text=source_text[node.start : node.end]),
                )
            )
            continue

        if _REFERENCES_RE.match(text):
            current_chapter = None
            current_chapter_number = None
            current_appendix = None
            current_appendix_letter = None
            section_stack = []
            active_definition = None
            ambiguous_appendix = False
            in_references = True
            segment = _Segment(observation, observation.start, observation.end, text)
            heading = _Draft(
                DocumentNodeType.HEADING,
                _coordinate_locator("references", observation, text),
                observation.start,
                observation.end,
                label="REFERENCES",
                attributes=_attributes(observation, source_role="references"),
            )
            root.children.append(heading)
            continue

        if ambiguous_appendix:
            segment = _Segment(observation, observation.start, observation.end, text)
            add_leaf(
                DocumentNodeType.UNSUPPORTED,
                segment,
                parent=root,
                source_role="unresolved_appendix",
                locator_kind="unsupported-appendix-content",
            )
            continue

        if in_references:
            segment = _Segment(observation, observation.start, observation.end, text)
            add_leaf(
                DocumentNodeType.PARAGRAPH,
                segment,
                parent=root,
                source_role="references",
                locator_kind="reference-prose",
            )
            continue

        if _PRIVATE_USE_RE.search(text):
            segment = _Segment(observation, observation.start, observation.end, text)
            node = add_leaf(DocumentNodeType.UNSUPPORTED, segment, locator_kind="unsupported-nonprose")
            diagnostics.append(
                Diagnostic(
                    code="nds-nonprose-structure-deferred",
                    severity=DiagnosticSeverity.WARNING,
                    message="Extracted private-use glyphs indicate non-prose structure whose faithful representation is deferred.",
                    span=SourceSpan(start=node.start, end=node.end, text=source_text[node.start : node.end]),
                )
            )
            continue

        segments = _segments_for_block(
            observation,
            chapter=current_chapter_number,
            appendix=current_appendix_letter,
        )
        for segment in segments:
            if segment.locator is None:
                if _LIST_RE.match(segment.text):
                    add_leaf(DocumentNodeType.LIST_ITEM, segment)
                else:
                    add_leaf(DocumentNodeType.PARAGRAPH, segment)
                continue

            locator = segment.locator
            depth = _locator_depth(locator)
            while section_stack and section_stack[-1].native_locator is not None and _locator_depth(section_stack[-1].native_locator) >= depth:
                section_stack.pop()
            active_definition = None
            parent = section_stack[-1] if section_stack else (current_appendix or current_chapter or root)
            body = segment.text[len(locator) :].lstrip()

            definition_owner = (
                parent.node_type in {DocumentNodeType.SECTION, DocumentNodeType.SUBSECTION}
                and parent.label is not None
                and _DEFINITION_LABEL_RE.match(parent.label) is not None
            )
            if definition_owner:
                definition = _Draft(
                    DocumentNodeType.DEFINITION_ENTRY,
                    f"definition:{locator}",
                    segment.start,
                    segment.end,
                    attributes=_attributes(segment.observation),
                    native_locator=locator,
                )
                parent.children.append(definition)
                active_definition = definition
                extend_context(segment.end)
                continue

            node_type = DocumentNodeType.SECTION if depth == 1 else DocumentNodeType.SUBSECTION
            label = body if _looks_like_heading(body) else None
            section = _Draft(
                node_type,
                f"section:{locator}",
                segment.start,
                segment.end,
                label=label,
                attributes=_attributes(segment.observation),
                native_locator=locator,
            )
            parent.children.append(section)
            section_stack.append(section)
            extend_context(segment.end)

            if body and label is None:
                body_local_start = segment.text.find(body)
                body_start = segment.start + body_local_start
                body_segment = _Segment(
                    segment.observation,
                    body_start,
                    segment.end,
                    source_text[body_start : segment.end],
                )
                add_leaf(
                    DocumentNodeType.PARAGRAPH,
                    body_segment,
                    parent=section,
                    locator_kind="section-prose",
                )

    ast = DocumentAst(
        source_text=source_text,
        source_artifact=source_artifact,
        root=_materialize(root, source_text=source_text, source_artifact=source_artifact),
        diagnostics=tuple(diagnostics),
    )
    validate_document_ast(ast)
    return ast
