"""ACI 318-19 publication-structure recognition.

This adapter recognizes source roles and publication-native structural locators
before any engineering semantics are inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..document_model import (
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .pdf_layout import PdfBlock, PdfPage, normalize_block_text


_TABLE_RE = re.compile(r"^Table\s+(?P<locator>R?\d+(?:\.\d+)+)\b", re.IGNORECASE)
_LOCATOR_RE = re.compile(r"^(?P<locator>R?\d+(?:\.\d+)+)\b")


@dataclass(frozen=True, slots=True)
class _PreparedBlock:
    block: PdfBlock
    text: str
    role: str
    start: int
    end: int


def _source_role(block: PdfBlock, page_width: float) -> str:
    midpoint = page_width / 2.0
    x0, _, x1, _ = block.bbox
    width = max(x1 - x0, 0.0)

    # Ordinary ACI Code/Commentary columns terminate near the page midpoint.
    # Wide blocks crossing the gutter are page furniture or otherwise require
    # explicit recognition rather than authority inference.
    if x0 < midpoint and x1 <= midpoint + 8.0 and width < page_width * 0.48:
        return "normative"
    if x1 > midpoint and x0 >= midpoint - 8.0 and width < page_width * 0.48:
        return "commentary"
    return "unresolved"


def _bbox_attribute(block: PdfBlock) -> str:
    return ",".join(f"{value:.3f}" for value in block.bbox)


def _node_type(locator: str) -> DocumentNodeType:
    stem = locator.removeprefix("R")
    return DocumentNodeType.SECTION if stem.count(".") == 1 else DocumentNodeType.SUBSECTION


def _prepare_blocks(page: PdfPage) -> tuple[str, tuple[_PreparedBlock, ...]]:
    classified: list[tuple[int, float, float, int, PdfBlock, str, str]] = []
    role_order = {"normative": 0, "commentary": 1, "unresolved": 2}

    for block in page.blocks:
        text = normalize_block_text(block.text)
        if not text:
            continue
        role = _source_role(block, page.width)
        classified.append(
            (
                role_order[role],
                block.bbox[1],
                block.bbox[0],
                block.block_number,
                block,
                role,
                text,
            )
        )

    classified.sort(key=lambda item: item[:4])
    source_parts: list[str] = []
    prepared: list[_PreparedBlock] = []
    cursor = 0
    for _, _, _, _, block, role, text in classified:
        if source_parts:
            source_parts.append("\n")
            cursor += 1
        start = cursor
        source_parts.append(text)
        cursor += len(text)
        prepared.append(_PreparedBlock(block=block, text=text, role=role, start=start, end=cursor))

    return "".join(source_parts), tuple(prepared)


def _attributes(item: _PreparedBlock, printed_page: int) -> dict[str, str]:
    return {
        "source_role": item.role,
        "pdf_page": str(item.block.page_number),
        "printed_page": str(printed_page),
        "bbox": _bbox_attribute(item.block),
        "extraction_block": str(item.block.block_number),
    }


def _preferred_locator_blocks(
    prepared: tuple[_PreparedBlock, ...],
) -> dict[tuple[str, str], _PreparedBlock]:
    """Choose the richest block for duplicate ordinary locator fragments."""

    preferred: dict[tuple[str, str], _PreparedBlock] = {}
    for item in prepared:
        if item.role == "unresolved" or _TABLE_RE.match(item.text):
            continue
        match = _LOCATOR_RE.match(item.text)
        if not match:
            continue
        key = (item.role, match.group("locator"))
        current = preferred.get(key)
        if current is None or len(item.text) > len(current.text):
            preferred[key] = item
    return preferred


def _native_locator(node: DocumentNode) -> str | None:
    if node.node_type not in {
        DocumentNodeType.SECTION,
        DocumentNodeType.SUBSECTION,
        DocumentNodeType.TABLE,
    }:
        return None
    return node.locator.rsplit(":", 1)[-1]


def _nest_publication_hierarchy(
    nodes: list[DocumentNode],
    *,
    source_artifact: DocumentSourceArtifact,
    source_text: str,
) -> list[DocumentNode]:
    """Nest numbered ACI structures under the nearest present numbered parent."""

    structural: dict[tuple[str, str], DocumentNode] = {}
    for node in nodes:
        if node.node_type not in {DocumentNodeType.SECTION, DocumentNodeType.SUBSECTION}:
            continue
        role = dict(node.attributes).get("source_role")
        native = _native_locator(node)
        if role and native:
            structural[(role, native)] = node

    parent_of: dict[str, str] = {}
    children_of: dict[str, list[DocumentNode]] = {}
    for node in nodes:
        role = dict(node.attributes).get("source_role")
        native = _native_locator(node)
        if role not in {"normative", "commentary"} or native is None:
            continue
        stem = native.removeprefix("R")
        parts = stem.split(".")
        prefix_marker = "R" if native.startswith("R") else ""
        for size in range(len(parts) - 1, 1, -1):
            candidate = prefix_marker + ".".join(parts[:size])
            parent = structural.get((role, candidate))
            if parent is not None and parent.locator != node.locator:
                parent_of[node.node_id] = parent.node_id
                children_of.setdefault(parent.node_id, []).append(node)
                break

    node_by_id = {node.node_id: node for node in nodes}

    def rebuild(node: DocumentNode) -> DocumentNode:
        direct = sorted(children_of.get(node.node_id, ()), key=lambda child: child.span.start)
        children = [rebuild(child) for child in direct]
        if not children:
            return node
        start = min([node.span.start, *(child.span.start for child in children)])
        end = max([node.span.end, *(child.span.end for child in children)])
        return make_document_node(
            source_artifact=source_artifact,
            node_type=node.node_type,
            locator=node.locator,
            span=SourceSpan(start=start, end=end, text=source_text[start:end]),
            label=node.label,
            attributes=dict(node.attributes),
            children=children,
        )

    roots = [node for node in nodes if node.node_id not in parent_of]
    return [rebuild(node_by_id[node.node_id]) for node in roots]


def parse_aci318_page(
    page: PdfPage,
    *,
    source_artifact: DocumentSourceArtifact,
    printed_page: int,
) -> DocumentAst:
    """Parse one ACI 318-19 PDF page into source-role-aware Document AST nodes.

    This first structural slice recognizes numbered Code/Commentary locators and
    numbered table regions. It intentionally leaves table cells, equations,
    references, definitions, and engineering semantics to later reviewed gates.
    """

    source_text, prepared = _prepare_blocks(page)
    if not source_text:
        raise ValueError("ACI 318-19 page has no extractable text blocks")

    preferred = _preferred_locator_blocks(prepared)
    normative_locators = {
        native
        for (role, native), item in preferred.items()
        if role == "normative" and not native.startswith("R") and item.text
    }

    nodes: list[DocumentNode] = []
    diagnostics: list[Diagnostic] = []

    for item in prepared:
        span = SourceSpan(start=item.start, end=item.end, text=item.text)
        attributes = _attributes(item, printed_page)

        if item.role == "unresolved":
            locator = (
                f"aci-318-19:unresolved:pdf-page:{page.page_number}:"
                f"bbox:{_bbox_attribute(item.block)}"
            )
            nodes.append(
                make_document_node(
                    source_artifact=source_artifact,
                    node_type=DocumentNodeType.UNSUPPORTED,
                    locator=locator,
                    span=span,
                    attributes=attributes,
                )
            )
            diagnostics.append(
                Diagnostic(
                    code="aci318_ambiguous_source_role",
                    severity=DiagnosticSeverity.WARNING,
                    message="ACI source region crosses the Code/Commentary boundary",
                    span=span,
                )
            )
            continue

        table_match = _TABLE_RE.match(item.text)
        if table_match:
            native = table_match.group("locator")
            locator = f"aci-318-19:{item.role}:table:{native}"
            nodes.append(
                make_document_node(
                    source_artifact=source_artifact,
                    node_type=DocumentNodeType.TABLE,
                    locator=locator,
                    span=span,
                    label=native,
                    attributes=attributes,
                )
            )
            continue

        match = _LOCATOR_RE.match(item.text)
        if not match:
            continue

        native = match.group("locator")
        if preferred[(item.role, native)] is not item:
            diagnostics.append(
                Diagnostic(
                    code="aci318_duplicate_locator_fragment",
                    severity=DiagnosticSeverity.WARNING,
                    message="Duplicate locator-only extraction fragment was not promoted to structure",
                    span=span,
                )
            )
            continue

        locator = f"aci-318-19:{item.role}:{native}"
        if item.role == "commentary" and native.startswith("R"):
            stem = native[1:]
            if stem in normative_locators:
                attributes["corresponds_to"] = f"aci-318-19:normative:{stem}"

        nodes.append(
            make_document_node(
                source_artifact=source_artifact,
                node_type=_node_type(native),
                locator=locator,
                span=span,
                label=native,
                attributes=attributes,
            )
        )

    nested_nodes = _nest_publication_hierarchy(
        nodes,
        source_artifact=source_artifact,
        source_text=source_text,
    )
    root_span = SourceSpan(start=0, end=len(source_text), text=source_text)
    root = make_document_node(
        source_artifact=source_artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator=f"aci-318-19:pdf-page:{page.page_number}",
        span=root_span,
        attributes={
            "pdf_page": str(page.page_number),
            "printed_page": str(printed_page),
            "source_scope": "page_slice",
        },
        children=nested_nodes,
    )
    return DocumentAst(
        source_text=source_text,
        source_artifact=source_artifact,
        root=root,
        diagnostics=tuple(diagnostics),
    )
