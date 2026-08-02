"""Local structural ingestion for the 2017 edition of NFPA 70.

The generated seeds may contain copyrighted source expression and are intended
for private/local storage. This module does not determine applicability or
compliance.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any, Iterable

from ..document_model import (
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from ..document_validation import validate_document_ast
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .nec_hierarchy import build_nec_hierarchy
from .pdf_layout import PdfBlock, PdfLayoutDocument, normalize_block_text, order_content_blocks


SEED_VERSION = "0.1.0"
EXTRACTOR_ID = "building-code-ast:nec2017-pdf"
EXTRACTOR_VERSION = "0.1.0"

_ARTICLE_BOOKMARK_RE = re.compile(r"^\s*(?P<number>\d{2,3})\s+(?P<title>\S.*)$")
_ARTICLE_ANCHOR_RE = re.compile(r"^ARTICLE\s+(?P<number>\d{2,3})\b", re.IGNORECASE)
_SECTION_RE = re.compile(
    r"^(?P<section>\d{2,3}\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)\s+"
    r"(?P<title>[^.]+\.)?",
)
_DEFINITION_RE = re.compile(r"^(?P<term>[A-Z][^.]{1,180})\.\s+\S")
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ArticleRange:
    number: str
    title: str
    start_page: int
    scan_end_page: int
    next_number: str | None


@dataclass(frozen=True, slots=True)
class SourceManifest:
    source_title: str
    edition: str
    artifact_id: str
    edition_id: str
    sha256: str
    size_bytes: int
    page_count: int
    file_name: str
    extractor_id: str = EXTRACTOR_ID
    extractor_version: str = EXTRACTOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_title": self.source_title,
            "edition": self.edition,
            "artifact_id": self.artifact_id,
            "edition_id": self.edition_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "file_name": self.file_name,
            "extractor_id": self.extractor_id,
            "extractor_version": self.extractor_version,
        }


@dataclass(frozen=True, slots=True)
class SourceMapEntry:
    normalized_start: int
    normalized_end: int
    normalized_text: str
    page_number: int
    bbox: tuple[float, float, float, float]
    block_number: int
    raw_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_span": {
                "start": self.normalized_start,
                "end": self.normalized_end,
                "text": self.normalized_text,
            },
            "page_number": self.page_number,
            "bbox": [round(value, 3) for value in self.bbox],
            "block_number": self.block_number,
            "raw_text": self.raw_text,
        }


@dataclass(frozen=True, slots=True)
class ArticleSeed:
    source_manifest: SourceManifest
    article_number: str
    article_title: str
    source_map: tuple[SourceMapEntry, ...]
    document_ast: DocumentAst
    diagnostics: tuple[Diagnostic, ...] = ()
    seed_version: str = SEED_VERSION

    def to_dict(self) -> dict[str, Any]:
        node_counts: Counter[str] = Counter()

        def count(node: DocumentNode) -> None:
            node_counts[node.node_type.value] += 1
            for child in node.children:
                count(child)

        count(self.document_ast.root)
        return {
            "seed_version": self.seed_version,
            "source_manifest": self.source_manifest.to_dict(),
            "article": {
                "number": self.article_number,
                "title": self.article_title,
            },
            "source_map": [entry.to_dict() for entry in self.source_map],
            "document_ast": self.document_ast.to_dict(),
            "ingestion_diagnostics": [item.to_dict() for item in self.diagnostics],
            "stats": {
                "source_map_entries": len(self.source_map),
                "node_counts": dict(sorted(node_counts.items())),
            },
        }


def discover_article_ranges(layout: PdfLayoutDocument) -> tuple[ArticleRange, ...]:
    """Return numeric NEC article bookmarks with inclusive scan ranges."""

    found: list[tuple[str, str, int]] = []
    for item in layout.outline:
        title = " ".join(item.title.split())
        match = _ARTICLE_BOOKMARK_RE.match(title)
        if match is None:
            continue
        found.append((match.group("number"), match.group("title"), item.page_number))

    if not found:
        raise ValueError("no numeric NEC article bookmarks were found")

    ranges: list[ArticleRange] = []
    for index, (number, title, start_page) in enumerate(found):
        if index + 1 < len(found):
            next_number, _, next_page = found[index + 1]
            scan_end_page = next_page
        else:
            next_number = None
            scan_end_page = layout.page_count
        ranges.append(
            ArticleRange(
                number=number,
                title=title,
                start_page=start_page,
                scan_end_page=scan_end_page,
                next_number=next_number,
            )
        )
    return tuple(ranges)


def _range_for(layout: PdfLayoutDocument, article_number: str) -> ArticleRange:
    normalized = str(article_number).strip()
    for item in discover_article_ranges(layout):
        if item.number == normalized:
            return item
    raise ValueError(f"article {normalized} is not present in the PDF outline")


def _visible_article_number(block: PdfBlock) -> str | None:
    match = _ARTICLE_ANCHOR_RE.match(normalize_block_text(block.text))
    return None if match is None else match.group("number")


def select_article_blocks(
    layout: PdfLayoutDocument,
    article_number: str,
) -> tuple[PdfBlock, ...]:
    """Select one article, trimming same-page transitions by visible anchors."""

    article_range = _range_for(layout, article_number)
    ordered: list[PdfBlock] = []
    for page_number in range(article_range.start_page, article_range.scan_end_page + 1):
        page = layout.page(page_number)
        ordered.extend(order_content_blocks(page.blocks, page.width))

    start_index: int | None = None
    for index, block in enumerate(ordered):
        if _visible_article_number(block) == article_range.number:
            start_index = index
            break
    if start_index is None:
        raise ValueError(
            f"visible ARTICLE {article_range.number} anchor was not found in the PDF text"
        )

    end_index = len(ordered)
    if article_range.next_number is not None:
        for index in range(start_index + 1, len(ordered)):
            candidate = ordered[index]
            candidate_text = normalize_block_text(candidate.text)
            if (
                candidate.page_number == article_range.scan_end_page
                and re.match(r"^Chapter\s+\d+\b", candidate_text)
            ):
                end_index = index
                break
            if _visible_article_number(candidate) == article_range.next_number:
                end_index = index
                break

    selected = tuple(
        block
        for block in ordered[start_index:end_index]
        if normalize_block_text(block.text)
    )
    if not selected:
        raise ValueError(f"article {article_range.number} has no retained content")
    return selected


def _looks_table_like(text: str, block: PdfBlock) -> bool:
    numeric_tokens = len(re.findall(r"\b\d+(?:\.\d+)?\b", text))
    width = block.bbox[2] - block.bbox[0]
    return (numeric_tokens >= 10 and width >= 400.0) or (" | " in text and width >= 350.0)


def _classify_block(
    article_number: str,
    text: str,
    block: PdfBlock,
) -> tuple[DocumentNodeType, str | None, dict[str, str], str | None]:
    anchor = _ARTICLE_ANCHOR_RE.match(text)
    if anchor is not None:
        return DocumentNodeType.HEADING, f"Article {anchor.group('number')}", {}, None

    if text.startswith("Informational Note"):
        return DocumentNodeType.NOTE, "Informational Note", {}, None
    if text.startswith("Exception"):
        return DocumentNodeType.NOTE, "Exception", {"kind": "exception"}, None
    if re.match(r"^(?:Chapter\s+\d+|Part\s+[IVXLC]+\.)", text):
        return DocumentNodeType.HEADING, text.split(" ", 3)[0], {}, None

    section = _SECTION_RE.match(text)
    if section is not None:
        label = section.group("section")
        title = section.group("title")
        if title:
            label = f"{label} {title.strip()}"
        return DocumentNodeType.SECTION, label, {}, None

    if text.startswith("("):
        marker = text.split(")", 1)[0] + ")"
        if re.match(r"^\([A-Z]\)$", marker):
            return DocumentNodeType.SUBSECTION, marker, {"marker": marker}, None
        return DocumentNodeType.LIST_ITEM, marker, {"marker": marker}, None

    if article_number == "100" and not text.startswith(("Scope.", "Part ")):
        definition = _DEFINITION_RE.match(text)
        if definition is not None:
            return (
                DocumentNodeType.DEFINITION_ENTRY,
                definition.group("term"),
                {},
                None,
            )

    if _looks_table_like(text, block):
        return (
            DocumentNodeType.UNSUPPORTED,
            None,
            {"structure_hint": "table_like_layout"},
            "unsupported-table-layout",
        )

    return DocumentNodeType.PARAGRAPH, None, {}, None


def _build_text_and_map(
    blocks: Iterable[PdfBlock],
) -> tuple[str, tuple[SourceMapEntry, ...]]:
    chunks: list[str] = []
    entries: list[SourceMapEntry] = []
    offset = 0
    for block in blocks:
        normalized = normalize_block_text(block.text)
        if not normalized:
            continue
        if chunks:
            chunks.append("\n\n")
            offset += 2
        start = offset
        chunks.append(normalized)
        offset += len(normalized)
        entries.append(
            SourceMapEntry(
                normalized_start=start,
                normalized_end=offset,
                normalized_text=normalized,
                page_number=block.page_number,
                bbox=block.bbox,
                block_number=block.block_number,
                raw_text=block.text,
            )
        )
    return "".join(chunks), tuple(entries)


def build_article_seed(
    layout: PdfLayoutDocument,
    article_number: str,
    *,
    source_sha256: str,
    source_size: int,
) -> ArticleSeed:
    """Build and validate one private ArticleSeed from an extracted PDF layout."""

    digest = source_sha256.lower()
    if _HEX_64_RE.fullmatch(digest) is None:
        raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
    if source_size <= 0:
        raise ValueError("source_size must be positive")

    article_range = _range_for(layout, article_number)
    selected = select_article_blocks(layout, article_range.number)
    source_text, source_map = _build_text_and_map(selected)
    if not source_text:
        raise ValueError(f"article {article_range.number} produced empty normalized text")

    artifact = DocumentSourceArtifact(
        artifact_id="nfpa:70",
        edition_id=f"2017:pdf:sha256:{digest}",
    )
    diagnostics: list[Diagnostic] = []
    block_nodes: list[DocumentNode] = []
    for index, (block, entry) in enumerate(zip(selected, source_map, strict=True), start=1):
        node_type, label, attributes, diagnostic_code = _classify_block(
            article_range.number,
            entry.normalized_text,
            block,
        )
        span = SourceSpan(
            start=entry.normalized_start,
            end=entry.normalized_end,
            text=entry.normalized_text,
        )
        locator = f"article:{article_range.number}/block:{index:04d}"
        block_nodes.append(
            make_document_node(
                source_artifact=artifact,
                node_type=node_type,
                locator=locator,
                span=span,
                label=label,
                attributes={
                    **attributes,
                    "pdf_page": str(block.page_number),
                    "layout_role": node_type.value,
                },
            )
        )
        if diagnostic_code is not None:
            diagnostics.append(
                Diagnostic(
                    code=diagnostic_code,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "The source text was preserved, but the table-like PDF layout "
                        "was not reconstructed into cells."
                    ),
                    span=span,
                )
            )

    hierarchy = build_nec_hierarchy(
        article_number=article_range.number,
        source_text=source_text,
        source_artifact=artifact,
        nodes=block_nodes,
    )
    diagnostics.extend(hierarchy.diagnostics)

    full_span = SourceSpan(0, len(source_text), source_text)
    article_node = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.SECTION,
        locator=f"article:{article_range.number}",
        span=full_span,
        label=f"Article {article_range.number} - {article_range.title}",
        attributes={"article_number": article_range.number},
        children=hierarchy.nodes,
    )
    root = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator=f"document:article:{article_range.number}",
        span=full_span,
        label=f"NFPA 70 (2017), Article {article_range.number}",
        children=(article_node,),
    )
    document_ast = DocumentAst(
        source_text=source_text,
        source_artifact=artifact,
        root=root,
        diagnostics=tuple(diagnostics),
    )
    validate_document_ast(document_ast)

    manifest = SourceManifest(
        source_title="NFPA 70, National Electrical Code",
        edition="2017",
        artifact_id=artifact.artifact_id,
        edition_id=artifact.edition_id,
        sha256=digest,
        size_bytes=source_size,
        page_count=layout.page_count,
        file_name=layout.file_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
    )
    return ArticleSeed(
        source_manifest=manifest,
        article_number=article_range.number,
        article_title=article_range.title,
        source_map=source_map,
        document_ast=document_ast,
        diagnostics=tuple(diagnostics),
    )
