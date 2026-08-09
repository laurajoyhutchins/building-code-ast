"""Deterministic navigation through persisted source evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import SourceArtifactIdentity, SourceEvidence
from .store import read_evidence_store


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    previous: tuple[SourceEvidence, ...]
    center: SourceEvidence
    next: tuple[SourceEvidence, ...]
    page_local: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.previous, tuple) or not all(isinstance(item, SourceEvidence) for item in self.previous):
            raise ValueError("previous must be an immutable tuple of SourceEvidence")
        if not isinstance(self.center, SourceEvidence):
            raise ValueError("center must be SourceEvidence")
        if not isinstance(self.next, tuple) or not all(isinstance(item, SourceEvidence) for item in self.next):
            raise ValueError("next must be an immutable tuple of SourceEvidence")
        if not isinstance(self.page_local, bool):
            raise ValueError("page_local must be boolean")
        if self.page_local:
            page = self.center.pdf_page
            if any(item.pdf_page != page for item in (*self.previous, *self.next)):
                raise ValueError("page-local context cannot contain evidence from another page")

    def to_dict(self) -> dict[str, object]:
        return {
            "previous": [item.to_dict() for item in self.previous],
            "center": self.center.to_dict(),
            "next": [item.to_dict() for item in self.next],
            "page_local": self.page_local,
        }


def get_evidence_by_id(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    evidence_id: str,
) -> SourceEvidence:
    """Return one exact evidence record by durable evidence identity."""

    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ValueError("evidence_id must not be empty")
    for item in read_evidence_store(path, artifact=artifact):
        if item.evidence_id == evidence_id:
            return item
    raise KeyError(f"evidence_id not found: {evidence_id}")


def get_page_evidence(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    pdf_page: int,
) -> tuple[SourceEvidence, ...]:
    """Return all persisted evidence for one physical PDF page in source order."""

    if isinstance(pdf_page, bool) or not isinstance(pdf_page, int) or pdf_page <= 0:
        raise ValueError("pdf_page must be a positive integer")
    if pdf_page > artifact.page_count:
        raise ValueError("pdf_page exceeds source artifact page_count")
    return tuple(
        item
        for item in read_evidence_store(path, artifact=artifact)
        if item.pdf_page == pdf_page
    )


def expand_evidence_context(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    evidence_id: str,
    before: int = 1,
    after: int = 1,
    page_local: bool = False,
) -> EvidenceContext:
    """Expand one evidence identity into deterministic neighboring source evidence."""

    _require_nonnegative(before, "before")
    _require_nonnegative(after, "after")
    if not isinstance(page_local, bool):
        raise ValueError("page_local must be boolean")

    records = read_evidence_store(path, artifact=artifact)
    center = None
    for item in records:
        if item.evidence_id == evidence_id:
            center = item
            break
    if center is None:
        raise KeyError(f"evidence_id not found: {evidence_id}")

    candidates = (
        tuple(item for item in records if item.pdf_page == center.pdf_page)
        if page_local
        else records
    )
    center_index = next(
        index
        for index, item in enumerate(candidates)
        if item.evidence_id == center.evidence_id
    )
    previous = candidates[max(0, center_index - before):center_index]
    next_items = candidates[center_index + 1:center_index + 1 + after]
    return EvidenceContext(
        previous=previous,
        center=center,
        next=next_items,
        page_local=page_local,
    )


def _require_nonnegative(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
