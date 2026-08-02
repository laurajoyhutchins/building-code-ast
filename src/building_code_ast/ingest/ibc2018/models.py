"""IBC 2018 private ingestion records and bounded publication metadata."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any, Mapping

from ...document_model import DocumentAst, DocumentNode
from ...model import Diagnostic
from ..layout_analysis import BodyFontProfile, CleanedPage, PageOrderProfile, RecurringMargins, RemovedLine, SourceFragment
from ..table_geometry import TableCandidate

SEED_VERSION = "0.2.0"
LAYOUT_ANALYSIS_VERSION = "0.1.0"
EXTRACTOR_ID = "building-code-ast:ibc2018-glyph-pdf"
EXTRACTOR_VERSION = "0.2.0"


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
class LogicalBlock:
    text: str
    fragments: tuple[SourceFragment, ...]
    table_like: bool = False
    source_line_ids: tuple[str, ...] = ()
    confidence: float = 0.75
    evidence: tuple[str, ...] = ("paragraph_assembly",)
    table: TableCandidate | None = None


@dataclass(frozen=True, slots=True)
class ChapterLayoutAnalysis:
    version: str = LAYOUT_ANALYSIS_VERSION
    body_font: BodyFontProfile = field(
        default_factory=lambda: BodyFontProfile(None, None, 0.0, ("body_font_unknown",))
    )
    margins: RecurringMargins = field(
        default_factory=lambda: RecurringMargins(frozenset(), frozenset(), 0)
    )
    page_profiles: tuple[PageOrderProfile, ...] = ()
    removed_lines: tuple[RemovedLine, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        reason_counts = Counter(item.reason for item in self.removed_lines)
        return {
            "version": self.version,
            "body_font": self.body_font.to_dict(),
            "margins": self.margins.to_dict(),
            "page_profiles": [profile.to_dict() for profile in self.page_profiles],
            "removed_lines": {
                "count": len(self.removed_lines),
                "reason_counts": dict(sorted(reason_counts.items())),
                "line_ids": [item.line.line_id for item in self.removed_lines],
            },
        }


@dataclass(frozen=True, slots=True)
class ChapterLayout:
    spec: ChapterSpec
    blocks: tuple[LogicalBlock, ...]
    cleaned_pages: tuple[CleanedPage, ...] = ()
    analysis: ChapterLayoutAnalysis | None = None

    @property
    def page_profiles(self) -> tuple[PageOrderProfile, ...]:
        return self.analysis.page_profiles if self.analysis else ()


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
    source_line_ids: tuple[str, ...] = ()
    confidence: float = 0.75
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_span": {
                "start": self.normalized_start,
                "end": self.normalized_end,
                "text": self.normalized_text,
            },
            "fragments": [fragment.to_dict() for fragment in self.fragments],
            "source_line_ids": list(self.source_line_ids),
            "confidence": self.confidence,
            "evidence": list(self.evidence),
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
    layout_analysis: ChapterLayoutAnalysis | None = None
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
            "layout_analysis": (
                self.layout_analysis.to_dict()
                if self.layout_analysis is not None
                else ChapterLayoutAnalysis().to_dict()
            ),
            "source_map": [entry.to_dict() for entry in self.source_map],
            "document_ast": self.document_ast.to_dict(),
            "ingestion_diagnostics": [item.to_dict() for item in self.diagnostics],
            "stats": {
                "source_map_entries": len(self.source_map),
                "source_fragments": sum(len(entry.fragments) for entry in self.source_map),
                "node_counts": dict(sorted(counts.items())),
            },
        }

