"""Private structural ingestion for a user-supplied 2018 IBC PDF.

This adapter reconstructs visual lines from a pathological glyph-oriented PDF
text layer, preserves page/bounding-box provenance, and emits a conservative
Document AST. It does not determine applicability, compliance, or meaning.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import statistics
from typing import Any, Iterable, Mapping, Sequence

from ..document_model import (
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from ..document_validation import validate_document_ast
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan


SEED_VERSION = "0.1.0"
EXTRACTOR_ID = "building-code-ast:ibc2018-glyph-pdf"
EXTRACTOR_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ChapterSpec:
    number: str
    title: str
    start_page: int
    end_page: int


CHAPTER_SPECS: Mapping[str, ChapterSpec] = {
    "1": ChapterSpec("1", "Scope and Administration", 28, 39),
    "2": ChapterSpec("2", "Definitions", 40, 71),
    "3": ChapterSpec("3", "Occupancy Classification and Use", 72, 81),
}

_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVISION_RE = re.compile(
    r"^(?:\[(?P<designation>[A-Z]{1,3})\]\s*)?"
    r"(?P<section>\d{3}(?:\.\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))*)+)\s+"
    r"(?P<title>[^.]{1,180}\.)?"
)
_DEFINITION_RE = re.compile(
    r"^(?:\[(?P<designation>[A-Z]{1,3})\]\s*)?"
    r"(?P<term>[A-Z0-9][A-Z0-9 /,()'’&\-]{1,180})\.\s+\S"
)
_LIST_RE = re.compile(r"^(?:\([A-Za-z0-9]+\)|\d+\.)\s+")


@dataclass(frozen=True, slots=True)
class SourceFragment:
    page_number: int
    bbox: tuple[float, float, float, float]
    block_number: int
    raw_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "bbox": [round(value, 3) for value in self.bbox],
            "block_number": self.block_number,
            "raw_text": self.raw_text,
        }


@dataclass(frozen=True, slots=True)
class VisualLine:
    page_number: int
    bbox: tuple[float, float, float, float]
    text: str
    fragments: tuple[SourceFragment, ...]


@dataclass(frozen=True, slots=True)
class LogicalBlock:
    text: str
    fragments: tuple[SourceFragment, ...]
    table_like: bool = False


@dataclass(frozen=True, slots=True)
class ChapterLayout:
    spec: ChapterSpec
    blocks: tuple[LogicalBlock, ...]


@dataclass(frozen=True, slots=True)
class IbcLayoutDocument:
    file_name: str
    page_count: int
    chapters: tuple[ChapterLayout, ...]

    def chapter(self, number: str) -> ChapterLayout:
        normalized = str(number).strip()
        for chapter in self.chapters:
            if chapter.spec.number == normalized:
                return chapter
        raise ValueError(f"chapter {normalized} was not extracted")


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
    fragments: tuple[SourceFragment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_span": {
                "start": self.normalized_start,
                "end": self.normalized_end,
                "text": self.normalized_text,
            },
            "fragments": [fragment.to_dict() for fragment in self.fragments],
        }


@dataclass(frozen=True, slots=True)
class ChapterSeed:
    source_manifest: SourceManifest
    chapter_number: str
    chapter_title: str
    source_pages: tuple[int, int]
    source_map: tuple[SourceMapEntry, ...]
    document_ast: DocumentAst
    diagnostics: tuple[Diagnostic, ...] = ()
    seed_version: str = SEED_VERSION

    def to_dict(self) -> dict[str, Any]:
        counts: Counter[str] = Counter()

        def count(node: DocumentNode) -> None:
            counts[node.node_type.value] += 1
            for child in node.children:
                count(child)

        count(self.document_ast.root)
        return {
            "seed_version": self.seed_version,
            "source_manifest": self.source_manifest.to_dict(),
            "chapter": {
                "number": self.chapter_number,
                "title": self.chapter_title,
                "physical_pdf_pages": list(self.source_pages),
            },
            "source_map": [entry.to_dict() for entry in self.source_map],
            "document_ast": self.document_ast.to_dict(),
            "ingestion_diagnostics": [item.to_dict() for item in self.diagnostics],
            "stats": {
                "source_map_entries": len(self.source_map),
                "source_fragments": sum(len(entry.fragments) for entry in self.source_map),
                "node_counts": dict(sorted(counts.items())),
            },
        }


def parse_chapter_numbers(values: Iterable[str]) -> tuple[str, ...]:
    chapters = tuple(str(value).strip() for value in values if str(value).strip())
    if not chapters:
        raise ValueError("at least one chapter number is required")
    if len(set(chapters)) != len(chapters):
        raise ValueError("chapter numbers must not be duplicated")
    unsupported = [number for number in chapters if number not in CHAPTER_SPECS]
    if unsupported:
        supported = ", ".join(CHAPTER_SPECS)
        raise ValueError(
            f"unsupported IBC 2018 chapter(s): {', '.join(unsupported)}; "
            f"this bounded adapter supports {supported}"
        )
    return chapters


def _normalize_visual_text(text: str) -> str:
    normalized = (
        text.replace("\u00ad", "")
        .replace("¬", "")
        .replace("\uf0a3", "≤")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    normalized = re.sub(r"\s+([.,;:!?])", r"\1", normalized)
    normalized = re.sub(r"\b(\d{1,4})\s+\.(?=\d)", r"\1.", normalized)
    normalized = re.sub(r"\b(\d)\s+(\d{2})(?=\b|\.)", r"\1\2", normalized)
    normalized = re.sub(r"\b(Chapter)\s+(\d)\s+(\d)\b", r"\1 \2\3", normalized)
    normalized = re.sub(
        r"\b(Section)\s+(\d)\s+(\d{2,3})(?=\b|\.)",
        r"\1 \2\3",
        normalized,
    )
    normalized = re.sub(
        r"\b(ASTM\s+[A-Z]\d{1,2})\s+(\d{2,3})\b",
        r"\1\2",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def reconstruct_glyph_line(chars: Sequence[Mapping[str, Any]]) -> str:
    """Reconstruct one visual line from individually positioned glyphs."""

    retained = [char for char in chars if str(char.get("c", "")).strip()]
    if not retained:
        return ""
    retained.sort(key=lambda char: float(char["bbox"][0]))
    heights = [
        float(char["bbox"][3]) - float(char["bbox"][1])
        for char in retained
    ]
    threshold = max(0.75, statistics.median(heights) * 0.10)
    output = [str(retained[0]["c"])]
    previous = retained[0]
    for char in retained[1:]:
        gap = float(char["bbox"][0]) - float(previous["bbox"][2])
        if gap > threshold:
            output.append(" ")
        output.append(str(char["c"]))
        previous = char
    return _normalize_visual_text("".join(output))


def _raw_block_text(block: Mapping[str, Any]) -> str:
    chars: list[Mapping[str, Any]] = []
    for line in block.get("lines", ()):
        for span in line.get("spans", ()):
            chars.extend(span.get("chars", ()))
    return reconstruct_glyph_line(chars)


def _same_column(left: VisualLine, right: VisualLine, midpoint: float) -> bool:
    return (
        (left.bbox[0] < midpoint and right.bbox[0] < midpoint)
        or (left.bbox[0] >= midpoint and right.bbox[0] >= midpoint)
    )


def merge_visual_fragments(
    lines: Iterable[VisualLine],
    *,
    page_width: float,
) -> tuple[VisualLine, ...]:
    """Merge split same-baseline PDF blocks without merging table columns."""

    midpoint = page_width / 2.0
    ordered = sorted(lines, key=lambda line: (line.bbox[1], line.bbox[0]))
    merged: list[VisualLine] = []
    for line in ordered:
        if merged:
            previous = merged[-1]
            overlap = min(previous.bbox[3], line.bbox[3]) - max(
                previous.bbox[1],
                line.bbox[1],
            )
            min_height = min(
                previous.bbox[3] - previous.bbox[1],
                line.bbox[3] - line.bbox[1],
            )
            gap = line.bbox[0] - previous.bbox[2]
            if (
                previous.page_number == line.page_number
                and overlap >= min_height * 0.60
                and _same_column(previous, line, midpoint)
                and gap < 8.0
            ):
                separator = " " if gap > 1.0 else ""
                combined = _normalize_visual_text(
                    previous.text + separator + line.text
                )
                merged[-1] = VisualLine(
                    page_number=line.page_number,
                    bbox=(
                        min(previous.bbox[0], line.bbox[0]),
                        min(previous.bbox[1], line.bbox[1]),
                        max(previous.bbox[2], line.bbox[2]),
                        max(previous.bbox[3], line.bbox[3]),
                    ),
                    text=combined,
                    fragments=previous.fragments + line.fragments,
                )
                continue
        merged.append(line)
    return tuple(merged)


def order_page_lines(
    lines: Iterable[VisualLine],
    *,
    page_width: float,
) -> tuple[VisualLine, ...]:
    """Return opening matter top-to-bottom, then left and right columns."""

    midpoint = page_width / 2.0
    material = list(lines)
    if not material:
        return ()
    right_y = [line.bbox[1] for line in material if line.bbox[0] >= midpoint]
    top_cutoff = min(right_y) - 1.0 if right_y and min(right_y) > 200.0 else 65.0
    top = [line for line in material if line.bbox[1] < top_cutoff]
    body = [line for line in material if line.bbox[1] >= top_cutoff]
    top.sort(key=lambda line: (line.bbox[1], line.bbox[0]))
    body.sort(
        key=lambda line: (
            0 if line.bbox[0] < midpoint else 1,
            line.bbox[1],
            line.bbox[0],
        )
    )
    return tuple(top + body)


def _extract_page_lines(page: Any, page_number: int) -> tuple[VisualLine, ...]:
    raw = page.get_text("rawdict")
    candidates: list[VisualLine] = []
    for block in raw.get("blocks", ()):
        if int(block.get("type", 0)) != 0:
            continue
        bbox = tuple(float(value) for value in block["bbox"])
        if bbox[1] < 65.0 or bbox[3] > 750.0:
            continue
        text = _raw_block_text(block)
        if not text:
            continue
        fragment = SourceFragment(
            page_number=page_number,
            bbox=bbox,
            block_number=int(block.get("number", len(candidates))),
            raw_text=text,
        )
        candidates.append(
            VisualLine(
                page_number=page_number,
                bbox=bbox,
                text=text,
                fragments=(fragment,),
            )
        )
    merged = merge_visual_fragments(
        candidates,
        page_width=float(page.rect.width),
    )
    return order_page_lines(merged, page_width=float(page.rect.width))


def _is_heading(text: str) -> bool:
    if text.startswith(("CHAPTER ", "PART ", "SECTION ")):
        return True
    letters = [char for char in text if char.isalpha()]
    return (
        bool(letters)
        and len(text) <= 120
        and all(char.isupper() for char in letters)
    )


def _is_definition_start(text: str, chapter_number: str) -> bool:
    return chapter_number == "2" and _DEFINITION_RE.match(text) is not None


def _starts_new_block(text: str, chapter_number: str) -> bool:
    return (
        _is_heading(text)
        or text.startswith(
            ("Exception:", "Exceptions:", "Informational Note", "Note:")
        )
        or _PROVISION_RE.match(text) is not None
        or _LIST_RE.match(text) is not None
        or _is_definition_start(text, chapter_number)
        or text.startswith(("TABLE ", "FIGURE "))
    )


def _join_text(previous: str, current: str) -> str:
    if previous.endswith(("-", "‐")) and current[:1].islower():
        return previous[:-1] + current
    return previous + " " + current


def _trim_opening_commentary(
    lines: Sequence[VisualLine],
) -> tuple[VisualLine, ...]:
    if not lines:
        return ()
    chapter_index = next(
        (i for i, line in enumerate(lines) if line.text.startswith("CHAPTER ")),
        0,
    )
    body_index = next(
        (
            i
            for i, line in enumerate(
                lines[chapter_index + 1 :],
                start=chapter_index + 1,
            )
            if line.text.startswith(("PART ", "SECTION "))
        ),
        len(lines),
    )
    commentary_index = next(
        (
            i
            for i, line in enumerate(
                lines[chapter_index:body_index],
                start=chapter_index,
            )
            if line.text.startswith(("User note", "User notes"))
        ),
        body_index,
    )
    return tuple(lines[chapter_index:commentary_index]) + tuple(
        lines[body_index:]
    )


def coalesce_visual_lines(
    lines: Sequence[VisualLine],
    *,
    chapter_number: str,
) -> tuple[LogicalBlock, ...]:
    """Coalesce visual lines into source-mapped headings and paragraphs."""

    retained = _trim_opening_commentary(lines)
    blocks: list[LogicalBlock] = []
    current_text = ""
    current_fragments: list[SourceFragment] = []
    current_table = False
    previous_line: VisualLine | None = None

    def flush() -> None:
        nonlocal current_text, current_fragments, current_table
        if current_text:
            blocks.append(
                LogicalBlock(
                    text=_normalize_visual_text(current_text),
                    fragments=tuple(current_fragments),
                    table_like=current_table,
                )
            )
        current_text = ""
        current_fragments = []
        current_table = False

    for line in retained:
        text = line.text
        starts = _starts_new_block(text, chapter_number)
        if current_text and current_table and not starts:
            current_text = _join_text(current_text, text)
            current_fragments.extend(line.fragments)
            previous_line = line
            continue
        if starts:
            flush()
            current_text = text
            current_fragments = list(line.fragments)
            current_table = text.startswith("TABLE ")
            previous_line = line
            continue

        gap = 0.0
        if previous_line and previous_line.page_number == line.page_number:
            gap = line.bbox[1] - previous_line.bbox[3]
        paragraph_break = (
            bool(current_text)
            and gap > 5.0
            and current_text.endswith((".", ":", ";"))
            and text[:1].isupper()
        )
        if paragraph_break:
            flush()
            current_text = text
            current_fragments = list(line.fragments)
        elif current_text:
            current_text = _join_text(current_text, text)
            current_fragments.extend(line.fragments)
        else:
            current_text = text
            current_fragments = list(line.fragments)
        previous_line = line
    flush()
    return tuple(blocks)


def extract_ibc2018_layout(
    path: Path | str,
    chapter_numbers: Iterable[str] = ("1", "2", "3"),
) -> IbcLayoutDocument:
    """Extract selected bounded IBC chapters from the supplied PDF."""

    chapters = parse_chapter_numbers(chapter_numbers)
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyMuPDF is required for IBC PDF ingestion; install "
            "building-code-ast[ibc-pdf]"
        ) from exc
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        document = fitz.open(source)
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"unable to open PDF source: {source.name}") from exc
    try:
        if document.page_count < max(
            spec.end_page for spec in CHAPTER_SPECS.values()
        ):
            raise ValueError(
                "the supplied PDF is too short to match the supported IBC 2018 layout"
            )
        extracted: list[ChapterLayout] = []
        for number in chapters:
            spec = CHAPTER_SPECS[number]
            visual: list[VisualLine] = []
            for page_number in range(spec.start_page, spec.end_page + 1):
                visual.extend(
                    _extract_page_lines(document[page_number - 1], page_number)
                )
            blocks = coalesce_visual_lines(visual, chapter_number=number)
            if not blocks or not blocks[0].text.startswith(f"CHAPTER {number}"):
                raise ValueError(
                    f"visible CHAPTER {number} anchor was not reconstructed "
                    f"at physical PDF page {spec.start_page}"
                )
            if not any(block.text.startswith("SECTION ") for block in blocks):
                raise ValueError(
                    f"chapter {number} contains no reconstructed SECTION heading"
                )
            extracted.append(ChapterLayout(spec=spec, blocks=blocks))
        return IbcLayoutDocument(
            file_name=source.name,
            page_count=document.page_count,
            chapters=tuple(extracted),
        )
    finally:
        document.close()


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
            )
        )
    return "".join(chunks), tuple(entries)


def _classify_block(
    text: str,
    *,
    chapter_number: str,
    table_like: bool,
) -> tuple[DocumentNodeType, str | None, dict[str, str], str | None]:
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
        return (
            DocumentNodeType.SECTION,
            text[:180],
            {"kind": "section_heading"},
            None,
        )
    provision = _PROVISION_RE.match(text)
    if provision is not None:
        label = provision.group("section")
        if provision.group("title"):
            label += " " + provision.group("title").strip()
        attributes = {"section": provision.group("section")}
        if provision.group("designation"):
            attributes["committee_designation"] = provision.group(
                "designation"
            )
        return DocumentNodeType.SECTION, label, attributes, None
    definition = _DEFINITION_RE.match(text) if chapter_number == "2" else None
    if definition is not None:
        attributes: dict[str, str] = {}
        if definition.group("designation"):
            attributes["committee_designation"] = definition.group(
                "designation"
            )
        return (
            DocumentNodeType.DEFINITION_ENTRY,
            definition.group("term"),
            attributes,
            None,
        )
    if text.startswith(
        ("Exception:", "Exceptions:", "Informational Note", "Note:")
    ):
        return DocumentNodeType.NOTE, text.split(":", 1)[0], {}, None
    if _LIST_RE.match(text):
        return DocumentNodeType.LIST_ITEM, text.split(" ", 1)[0], {}, None
    if _is_heading(text):
        return DocumentNodeType.HEADING, text[:180], {}, None
    return DocumentNodeType.PARAGRAPH, None, {}, None


def build_chapter_seed(
    layout: IbcLayoutDocument,
    chapter_number: str,
    *,
    source_sha256: str,
    source_size: int,
) -> ChapterSeed:
    digest = source_sha256.lower()
    if _HEX_64_RE.fullmatch(digest) is None:
        raise ValueError(
            "source_sha256 must be 64 lowercase hexadecimal characters"
        )
    if source_size <= 0:
        raise ValueError("source_size must be positive")
    chapter = layout.chapter(chapter_number)
    source_text, source_map = _build_text_and_map(chapter.blocks)
    if not source_text:
        raise ValueError(
            f"chapter {chapter.spec.number} produced empty normalized text"
        )
    artifact = DocumentSourceArtifact(
        artifact_id="icc:ibc",
        edition_id=f"2018:pdf:sha256:{digest}",
    )
    nodes: list[DocumentNode] = []
    diagnostics: list[Diagnostic] = []
    for index, (block, entry) in enumerate(
        zip(chapter.blocks, source_map, strict=True),
        start=1,
    ):
        node_type, label, attributes, diagnostic_code = _classify_block(
            block.text,
            chapter_number=chapter.spec.number,
            table_like=block.table_like,
        )
        span = SourceSpan(
            entry.normalized_start,
            entry.normalized_end,
            entry.normalized_text,
        )
        locator = f"chapter:{chapter.spec.number}/block:{index:05d}"
        pages = sorted(
            {fragment.page_number for fragment in entry.fragments}
        )
        nodes.append(
            make_document_node(
                source_artifact=artifact,
                node_type=node_type,
                locator=locator,
                span=span,
                label=label,
                attributes={
                    **attributes,
                    "pdf_pages": ",".join(str(page) for page in pages),
                    "layout_role": node_type.value,
                },
            )
        )
        if diagnostic_code:
            diagnostics.append(
                Diagnostic(
                    code=diagnostic_code,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "The source text was preserved in reconstructed reading "
                        "order, but the table-like PDF layout was not inferred "
                        "as cells."
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
        label=(
            f"International Building Code (2018), Chapter {chapter.spec.number}"
        ),
        children=(chapter_node,),
    )
    document_ast = DocumentAst(
        source_text=source_text,
        source_artifact=artifact,
        root=root,
        diagnostics=tuple(diagnostics),
    )
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
    )
