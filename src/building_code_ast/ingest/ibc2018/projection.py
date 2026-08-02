"""Private ChapterSeed and Document AST projection for IBC 2018 layout."""

from __future__ import annotations

from typing import Iterable

from .models import _DEFINITION_RE, _HEX_64_RE, _LIST_RE, _PROVISION_RE, ChapterSeed, IbcLayoutDocument, LogicalBlock, SourceManifest, SourceMapEntry
from .text import _is_heading
from ...document_model import DocumentAst, DocumentNode, DocumentNodeType, DocumentSourceArtifact, make_document_node
from ...document_validation import validate_document_ast
from ...model import Diagnostic, DiagnosticSeverity, SourceSpan


def _build_text_and_map(
    blocks: Iterable[LogicalBlock],
) -> tuple[str, tuple[SourceMapEntry, ...]]:
    chunks: list[str] = []
    entries: list[SourceMapEntry] = []
    offset = 0
    for block in blocks:
        if chunks:
            chunks.append("\n\n")
            offset += 2
        start = offset
        chunks.append(block.text)
        offset += len(block.text)
        entries.append(
            SourceMapEntry(
                normalized_start=start,
                normalized_end=offset,
                normalized_text=block.text,
                fragments=block.fragments,
                source_line_ids=block.source_line_ids,
                confidence=block.confidence,
                evidence=block.evidence,
            )
        )
    return "".join(chunks), tuple(entries)


def _classify_block(
    text: str,
    *,
    chapter_number: str,
    table_like: bool,
    has_table: bool,
) -> tuple[DocumentNodeType, str | None, dict[str, str], str | None]:
    if has_table:
        return (
            DocumentNodeType.TABLE,
            text.split("\n", 1)[0][:180],
            {"kind": "ruled_table"},
            None,
        )
    if table_like or text.startswith("TABLE "):
        return (
            DocumentNodeType.UNSUPPORTED,
            text.split(".", 1)[0][:180],
            {"structure_hint": "table_like_layout"},
            "unsupported-table-layout",
        )
    if text.startswith("CHAPTER "):
        return DocumentNodeType.HEADING, text, {"kind": "chapter_anchor"}, None
    if text.startswith("PART "):
        return DocumentNodeType.HEADING, text[:180], {"kind": "part"}, None
    if text.startswith("SECTION "):
        return DocumentNodeType.SECTION, text[:180], {"kind": "section_heading"}, None
    provision = _PROVISION_RE.match(text)
    if provision is not None:
        label = provision.group("section")
        if provision.group("title"):
            label += " " + provision.group("title").strip()
        attributes = {"section": provision.group("section")}
        if provision.group("designation"):
            attributes["committee_designation"] = provision.group("designation")
        return DocumentNodeType.SECTION, label, attributes, None
    definition = _DEFINITION_RE.match(text) if chapter_number == "2" else None
    if definition is not None:
        attributes: dict[str, str] = {}
        if definition.group("designation"):
            attributes["committee_designation"] = definition.group("designation")
        return DocumentNodeType.DEFINITION_ENTRY, definition.group("term"), attributes, None
    if text.startswith(("Exception:", "Exceptions:", "Informational Note", "Note:")):
        return DocumentNodeType.NOTE, text.split(":", 1)[0], {}, None
    if _LIST_RE.match(text):
        return DocumentNodeType.LIST_ITEM, text.split(" ", 1)[0], {}, None
    if _is_heading(text):
        return DocumentNodeType.HEADING, text[:180], {}, None
    return DocumentNodeType.PARAGRAPH, None, {}, None


def _table_children(
    *,
    artifact: DocumentSourceArtifact,
    block: LogicalBlock,
    entry: SourceMapEntry,
    locator: str,
) -> tuple[DocumentNode, ...]:
    table = block.table
    if table is None:
        return ()
    rows: list[DocumentNode] = []
    for row_index, row in enumerate(table.rows, start=1):
        if row.cells:
            row_start = entry.normalized_start + min(cell.local_start for cell in row.cells)
            row_end = entry.normalized_start + max(cell.local_end for cell in row.cells)
        else:
            row_start = entry.normalized_start
            row_end = entry.normalized_start
        cells: list[DocumentNode] = []
        for cell_index, cell in enumerate(row.cells, start=1):
            cell_start = entry.normalized_start + cell.local_start
            cell_end = entry.normalized_start + cell.local_end
            cells.append(
                make_document_node(
                    source_artifact=artifact,
                    node_type=DocumentNodeType.TABLE_CELL,
                    locator=f"{locator}/row:{row_index:03d}/cell:{cell_index:03d}",
                    span=SourceSpan(cell_start, cell_end, cell.text),
                    attributes={"layout_role": "table_cell"},
                )
            )
        rows.append(
            make_document_node(
                source_artifact=artifact,
                node_type=DocumentNodeType.TABLE_ROW,
                locator=f"{locator}/row:{row_index:03d}",
                span=SourceSpan(
                    row_start,
                    row_end,
                    entry.normalized_text[
                        row_start - entry.normalized_start : row_end - entry.normalized_start
                    ],
                ),
                attributes={"layout_role": "table_row"},
                children=cells,
            )
        )
    return tuple(rows)


def build_chapter_seed(
    layout: IbcLayoutDocument,
    chapter_number: str,
    *,
    source_sha256: str,
    source_size: int,
) -> ChapterSeed:
    digest = source_sha256.lower()
    if _HEX_64_RE.fullmatch(digest) is None:
        raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
    if source_size <= 0:
        raise ValueError("source_size must be positive")
    chapter = layout.chapter(chapter_number)
    source_text, source_map = _build_text_and_map(chapter.blocks)
    if not source_text:
        raise ValueError(f"chapter {chapter.spec.number} produced empty normalized text")
    artifact = DocumentSourceArtifact(
        artifact_id="icc:ibc",
        edition_id=f"2018:pdf:sha256:{digest}",
    )
    nodes: list[DocumentNode] = []
    diagnostics: list[Diagnostic] = []
    for index, (block, entry) in enumerate(zip(chapter.blocks, source_map, strict=True), start=1):
        node_type, label, attributes, diagnostic_code = _classify_block(
            block.text,
            chapter_number=chapter.spec.number,
            table_like=block.table_like,
            has_table=block.table is not None,
        )
        span = SourceSpan(entry.normalized_start, entry.normalized_end, entry.normalized_text)
        locator = f"chapter:{chapter.spec.number}/block:{index:05d}"
        pages = sorted({fragment.page_number for fragment in entry.fragments})
        node_attributes = {
            **attributes,
            "pdf_pages": ",".join(str(page) for page in pages),
            "layout_role": node_type.value,
        }
        if block.table is not None:
            node_attributes.update(
                {
                    "row_count": str(len(block.table.rows)),
                    "column_count": str(max(len(row.cells) for row in block.table.rows)),
                }
            )
        nodes.append(
            make_document_node(
                source_artifact=artifact,
                node_type=node_type,
                locator=locator,
                span=span,
                label=label,
                attributes=node_attributes,
                children=_table_children(
                    artifact=artifact,
                    block=block,
                    entry=entry,
                    locator=locator,
                ),
            )
        )
        if diagnostic_code:
            diagnostics.append(
                Diagnostic(
                    code=diagnostic_code,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "The source text was preserved in reconstructed reading order, "
                        "but the table-like PDF layout was not inferred as cells."
                    ),
                    span=span,
                )
            )
    full_span = SourceSpan(0, len(source_text), source_text)
    chapter_node = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.CHAPTER,
        locator=f"chapter:{chapter.spec.number}",
        span=full_span,
        label=f"Chapter {chapter.spec.number} - {chapter.spec.title}",
        attributes={"chapter_number": chapter.spec.number},
        children=nodes,
    )
    root = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator=f"document:chapter:{chapter.spec.number}",
        span=full_span,
        label=f"International Building Code (2018), Chapter {chapter.spec.number}",
        children=(chapter_node,),
    )
    document_ast = DocumentAst(source_text, artifact, root, tuple(diagnostics))
    validate_document_ast(document_ast)
    manifest = SourceManifest(
        source_title="International Building Code",
        edition="2018",
        artifact_id=artifact.artifact_id,
        edition_id=artifact.edition_id,
        sha256=digest,
        size_bytes=source_size,
        page_count=layout.page_count,
        file_name=layout.file_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
    )
    return ChapterSeed(
        source_manifest=manifest,
        chapter_number=chapter.spec.number,
        chapter_title=chapter.spec.title,
        source_pages=(chapter.spec.start_page, chapter.spec.end_page),
        source_map=source_map,
        document_ast=document_ast,
        diagnostics=tuple(diagnostics),
        layout_analysis=chapter.analysis,
    )
