"""Conservative NDS 2018 non-prose overlay for the generic Document AST.

This stage begins with the existing NDS hierarchy and promotes only source-backed
structural equation, table, and figure regions. It deliberately does not parse
mathematics, table lookup meaning, or figure graphics.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..document_model import DocumentAst, DocumentNode, DocumentNodeType, make_document_node
from ..document_validation import validate_document_ast
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .nds2018_equation_locators import normalize_nds2018_equation_locator
from .nds2018_hierarchy import parse_nds2018_hierarchy
from .nds2018_layout import NdsLayoutEvidence, NdsLayoutPage
from .pdf_layout import PdfBlock, normalize_block_text


_EQUATION_RE = re.compile(r"\((?P<id>[^()\s]+)\)\s*$")
_EQUATION_ONLY_RE = re.compile(r"^\((?P<id>[^()\s]+)\)$")
_FIGURE_RE = re.compile(r"^Figure\s+(?P<id>\d+[A-Z])\s+\S", re.IGNORECASE)
_TABLE_RE = re.compile(r"^Table\s+(?P<id>\d+[A-Z])\s+\S", re.IGNORECASE)
_FOOTNOTE_RE = re.compile(r"^(?P<number>\d+)\.\s+\S")
_PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
_SHORT_INLINE_EQUATION_PREFIX_MAX = 40
_STRUCTURAL = {
    DocumentNodeType.DOCUMENT,
    DocumentNodeType.CHAPTER,
    DocumentNodeType.APPENDIX,
    DocumentNodeType.SECTION,
    DocumentNodeType.SUBSECTION,
}


@dataclass(frozen=True, slots=True)
class _Observation:
    page: NdsLayoutPage
    block: PdfBlock
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class _Region:
    start: int
    end: int
    node: DocumentNode


def _observations(evidence: NdsLayoutEvidence, source_text: str) -> tuple[_Observation, ...]:
    observations: list[_Observation] = []
    cursor = 0
    pieces: list[str] = []
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
            observations.append(_Observation(page, block, start, cursor, text))
    if "".join(pieces) != source_text:
        raise ValueError("NDS non-prose overlay must preserve hierarchy source order exactly")
    return tuple(observations)


def _attributes(observation: _Observation) -> dict[str, str]:
    attrs = {
        "pdf_page": str(observation.block.page_number),
        "coordinate_space": "pdf_points",
        "bbox_pdf_points": ",".join(f"{value:.3f}" for value in observation.block.bbox),
    }
    if observation.page.printed_page is not None:
        attrs["printed_page"] = observation.page.printed_page
    return attrs


def _span(source_text: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start=start, end=end, text=source_text[start:end])


def _same_baseline_equation(left: _Observation, label: _Observation) -> bool:
    if left.block.page_number != label.block.page_number or len(left.text) > 80:
        return False
    lx0, ly0, lx1, ly1 = left.block.bbox
    rx0, ry0, _, ry1 = label.block.bbox
    vertical_overlap = min(ly1, ry1) - max(ly0, ry0)
    centers_close = abs(((ly0 + ly1) / 2.0) - ((ry0 + ry1) / 2.0)) <= 12.0
    horizontally_ordered = lx0 < rx0 and lx1 <= rx0 + 12.0
    return horizontally_ordered and (vertical_overlap > 0.0 or centers_close)


def _equation_regions(
    observations: tuple[_Observation, ...],
    *,
    source_text: str,
    source_artifact,
) -> list[_Region]:
    result: list[_Region] = []
    for index, observation in enumerate(observations):
        match = _EQUATION_RE.search(observation.text)
        if match is None:
            continue
        equation_id = normalize_nds2018_equation_locator(match.group("id"))
        if equation_id is None:
            continue
        start = observation.start
        attrs = _attributes(observation)
        attrs["equation_id"] = equation_id

        if _EQUATION_ONLY_RE.fullmatch(observation.text):
            if index == 0:
                continue
            previous = observations[index - 1]
            private_use = _PRIVATE_USE_RE.search(previous.text) is not None
            if previous.block.page_number != observation.block.page_number:
                continue
            if not private_use and not _same_baseline_equation(previous, observation):
                continue
            start = previous.start
            if private_use:
                attrs["glyph_state"] = "private_use_text_layer"
        else:
            prefix = observation.text[: match.start()].rstrip()
            private_use = _PRIVATE_USE_RE.search(prefix) is not None
            if not prefix:
                continue
            # Exact-source measurement found a bounded family of short inline
            # equation blocks whose text layer loses both '=' and private-use
            # glyphs. Keep that shape narrow so ordinary prose ending in a
            # parenthesized locator is not promoted.
            if (
                "=" not in prefix
                and not private_use
                and len(prefix) > _SHORT_INLINE_EQUATION_PREFIX_MAX
            ):
                continue
            if private_use:
                attrs["glyph_state"] = "private_use_text_layer"

        node = make_document_node(
            source_artifact=source_artifact,
            node_type=DocumentNodeType.EQUATION,
            locator=f"equation:{equation_id}",
            span=_span(source_text, start, observation.end),
            attributes=attrs,
        )
        result.append(_Region(start, observation.end, node))
    return result


def _figure_regions(
    observations: tuple[_Observation, ...],
    *,
    source_text: str,
    source_artifact,
) -> list[_Region]:
    result: list[_Region] = []
    for observation in observations:
        match = _FIGURE_RE.match(observation.text)
        if match is None:
            continue
        figure_id = match.group("id").upper()
        attrs = _attributes(observation)
        attrs["figure_id"] = figure_id
        attrs["graphic_state"] = "unavailable_in_text_layout"
        node = make_document_node(
            source_artifact=source_artifact,
            node_type=DocumentNodeType.FIGURE,
            locator=f"figure:{figure_id}",
            span=_span(source_text, observation.start, observation.end),
            attributes=attrs,
        )
        result.append(_Region(observation.start, observation.end, node))
    return result


def _table_regions(
    observations: tuple[_Observation, ...],
    *,
    source_text: str,
    source_artifact,
) -> list[_Region]:
    captions: dict[str, list[int]] = {}
    for index, observation in enumerate(observations):
        match = _TABLE_RE.match(observation.text)
        if match is not None:
            captions.setdefault(match.group("id").upper(), []).append(index)

    regions: list[_Region] = []
    for table_id, indices in sorted(captions.items()):
        pages = [observations[index].block.page_number for index in indices]
        if len(set(pages)) != len(pages):
            continue
        if any(right != left + 1 for left, right in zip(pages, pages[1:])):
            indices = indices[:1]
            pages = pages[:1]

        page_set = set(pages)
        first = observations[indices[0]]
        related = [
            item
            for item in observations
            if item.block.page_number in page_set
            and (item.block.page_number > first.block.page_number or item.start >= first.start)
        ]
        if not related:
            continue
        last = related[-1]
        children: list[DocumentNode] = []

        for index in indices:
            caption = observations[index]
            children.append(
                make_document_node(
                    source_artifact=source_artifact,
                    node_type=DocumentNodeType.TABLE_HEADING,
                    locator=f"table-heading:{table_id}:pdf-page-{caption.block.page_number}",
                    span=_span(source_text, caption.start, caption.end),
                    attributes={**_attributes(caption), "table_id": table_id},
                )
            )

        for page_number in pages:
            page_items = [
                item
                for item in related
                if item.block.page_number == page_number and _TABLE_RE.match(item.text) is None
            ]
            footnotes = [item for item in page_items if _FOOTNOTE_RE.match(item.text)]
            body_items = [item for item in page_items if item not in footnotes]
            if body_items:
                children.append(
                    make_document_node(
                        source_artifact=source_artifact,
                        node_type=DocumentNodeType.UNSUPPORTED,
                        locator=f"table-body:{table_id}:pdf-page-{page_number}",
                        span=_span(source_text, body_items[0].start, body_items[-1].end),
                        attributes={
                            "pdf_page": str(page_number),
                            "source_role": "table_body_unparsed",
                            "table_id": table_id,
                        },
                    )
                )
            for footnote in footnotes:
                number = _FOOTNOTE_RE.match(footnote.text).group("number")
                children.append(
                    make_document_node(
                        source_artifact=source_artifact,
                        node_type=DocumentNodeType.FOOTNOTE,
                        locator=f"table-footnote:{table_id}:pdf-page-{page_number}:{number}",
                        span=_span(source_text, footnote.start, footnote.end),
                        attributes={
                            **_attributes(footnote),
                            "table_id": table_id,
                            "footnote_number": number,
                        },
                    )
                )

        children.sort(key=lambda node: (node.span.start, node.span.end, node.locator))
        table = make_document_node(
            source_artifact=source_artifact,
            node_type=DocumentNodeType.TABLE,
            locator=f"table:{table_id}",
            span=_span(source_text, first.start, last.end),
            attributes={
                "table_id": table_id,
                "pdf_pages": ",".join(str(page) for page in pages),
                "continuation_state": "continued" if len(pages) > 1 else "single_page",
            },
            children=children,
        )
        regions.append(_Region(first.start, last.end, table))
    return regions


def _overlaps(node: DocumentNode, region: _Region) -> bool:
    return node.span.start < region.end and region.start < node.span.end


def _overlay(hierarchy: DocumentAst, regions: tuple[_Region, ...]) -> DocumentNode:
    owners: dict[str, list[DocumentNode]] = {}
    structural_nodes: list[DocumentNode] = []

    def collect(node: DocumentNode) -> None:
        if node.node_type in _STRUCTURAL:
            structural_nodes.append(node)
        for child in node.children:
            collect(child)

    collect(hierarchy.root)
    for region in regions:
        candidates = [
            node
            for node in structural_nodes
            if node.span.start <= region.start and node.span.end >= region.end
        ]
        owner = min(candidates, key=lambda node: (node.span.end - node.span.start, node.locator))
        owners.setdefault(owner.node_id, []).append(region.node)

    def rebuild(node: DocumentNode) -> DocumentNode:
        children: list[DocumentNode] = []
        for child in node.children:
            if child.node_type not in _STRUCTURAL and any(_overlaps(child, region) for region in regions):
                continue
            children.append(rebuild(child))
        children.extend(owners.get(node.node_id, ()))
        children.sort(key=lambda child: (child.span.start, child.span.end, child.locator))
        return make_document_node(
            source_artifact=hierarchy.source_artifact,
            node_type=node.node_type,
            locator=node.locator,
            span=node.span,
            label=node.label,
            attributes=dict(node.attributes),
            children=children,
        )

    return rebuild(hierarchy.root)


def parse_nds2018_document_structure(evidence: NdsLayoutEvidence) -> DocumentAst:
    """Overlay neutral NDS equations, tables, and figures onto hierarchy output."""

    hierarchy = parse_nds2018_hierarchy(evidence)
    observations = _observations(evidence, hierarchy.source_text)
    regions = tuple(
        sorted(
            [
                *_equation_regions(
                    observations,
                    source_text=hierarchy.source_text,
                    source_artifact=hierarchy.source_artifact,
                ),
                *_figure_regions(
                    observations,
                    source_text=hierarchy.source_text,
                    source_artifact=hierarchy.source_artifact,
                ),
                *_table_regions(
                    observations,
                    source_text=hierarchy.source_text,
                    source_artifact=hierarchy.source_artifact,
                ),
            ],
            key=lambda region: (region.start, region.end, region.node.locator),
        )
    )

    diagnostics = [
        diagnostic
        for diagnostic in hierarchy.diagnostics
        if not (
            diagnostic.code == "nds-nonprose-structure-deferred"
            and diagnostic.span is not None
            and any(
                diagnostic.span.start < region.end and region.start < diagnostic.span.end
                for region in regions
            )
        )
    ]
    for region in regions:
        if region.node.node_type is DocumentNodeType.FIGURE:
            diagnostics.append(
                Diagnostic(
                    code="nds-figure-graphic-unavailable",
                    severity=DiagnosticSeverity.WARNING,
                    message="NDS figure caption is source-backed, but graphic content is unavailable in text layout evidence.",
                    span=region.node.span,
                )
            )
        elif region.node.node_type is DocumentNodeType.TABLE:
            diagnostics.append(
                Diagnostic(
                    code="nds-table-body-structure-deferred",
                    severity=DiagnosticSeverity.WARNING,
                    message="NDS table identity and continuation are source-backed; body cell/header semantics remain deferred.",
                    span=region.node.span,
                )
            )

    ast = DocumentAst(
        source_text=hierarchy.source_text,
        source_artifact=hierarchy.source_artifact,
        root=_overlay(hierarchy, regions),
        diagnostics=tuple(diagnostics),
    )
    validate_document_ast(ast)
    return ast
