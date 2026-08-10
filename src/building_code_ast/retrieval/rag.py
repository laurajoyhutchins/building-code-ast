"""Provider-neutral retrieval-augmented generation grounding contracts.

This module prepares exact local source evidence for a caller-controlled generator.
It does not select a model provider, transmit source text, infer authority, or decide
compliance. Generated text is accepted only when its citations resolve to evidence
that was actually present in the grounding packet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable

from .context import EvidenceContext, expand_evidence_context
from .model import SourceArtifactIdentity, SourceEvidence
from .search import LexicalSearchMode, LexicalSearchResult, search_evidence_store
from .structural_search import StructuralSearchFilters, structural_search_evidence_store


@dataclass(frozen=True, slots=True)
class GroundingChunk:
    """One retrieval hit plus deterministic neighboring source context."""

    result: LexicalSearchResult
    context: EvidenceContext

    def __post_init__(self) -> None:
        if not isinstance(self.result, LexicalSearchResult):
            raise ValueError("result must be a LexicalSearchResult")
        if not isinstance(self.context, EvidenceContext):
            raise ValueError("context must be EvidenceContext")
        if self.result.evidence.evidence_id != self.context.center.evidence_id:
            raise ValueError("grounding context center must match retrieval evidence")

    def evidence(self) -> tuple[SourceEvidence, ...]:
        return (*self.context.previous, self.context.center, *self.context.next)

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result.to_dict(),
            "context": self.context.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GroundingPacket:
    """Deterministic local evidence supplied to a generation boundary."""

    artifact: SourceArtifactIdentity
    query: str
    mode: LexicalSearchMode
    chunks: tuple[GroundingChunk, ...]
    page_local: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, SourceArtifactIdentity):
            raise ValueError("artifact must be a SourceArtifactIdentity")
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("query must not be empty")
        if self.query != self.query.strip():
            raise ValueError("query must be trimmed")
        if not isinstance(self.mode, LexicalSearchMode):
            raise ValueError("mode must be a LexicalSearchMode")
        if not isinstance(self.chunks, tuple) or not all(
            isinstance(chunk, GroundingChunk) for chunk in self.chunks
        ):
            raise ValueError("chunks must be an immutable tuple of GroundingChunk")
        if not isinstance(self.page_local, bool):
            raise ValueError("page_local must be boolean")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return every evidence identity visible to the generator once."""

        seen: set[str] = set()
        ordered: list[str] = []
        for chunk in self.chunks:
            for evidence in chunk.evidence():
                if evidence.evidence_id in seen:
                    continue
                seen.add(evidence.evidence_id)
                ordered.append(evidence.evidence_id)
        return tuple(ordered)

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact": self.artifact.to_dict(),
            "query": self.query,
            "mode": self.mode.value,
            "page_local": self.page_local,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


@dataclass(frozen=True, slots=True)
class GeneratedDraft:
    """Caller-supplied generated text with explicit source-evidence citations."""

    generator_id: str
    text: str
    cited_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.generator_id, str) or not self.generator_id.strip():
            raise ValueError("generator_id must not be empty")
        if self.generator_id != self.generator_id.strip():
            raise ValueError("generator_id must be trimmed")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("generated text must not be empty")
        if not isinstance(self.cited_evidence_ids, tuple) or not all(
            isinstance(evidence_id, str) and evidence_id.strip()
            for evidence_id in self.cited_evidence_ids
        ):
            raise ValueError("citations must be an immutable tuple of evidence IDs")
        if len(set(self.cited_evidence_ids)) != len(self.cited_evidence_ids):
            raise ValueError("citations must not contain duplicate evidence IDs")


class GroundedAnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class GroundedGenerationResult:
    """Validated output of one caller-controlled grounded generation attempt."""

    status: GroundedAnswerStatus
    packet: GroundingPacket
    answer_text: str | None = None
    generator_id: str | None = None
    cited_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, GroundedAnswerStatus):
            raise ValueError("status must be a GroundedAnswerStatus")
        if not isinstance(self.packet, GroundingPacket):
            raise ValueError("packet must be a GroundingPacket")
        if not isinstance(self.cited_evidence_ids, tuple):
            raise ValueError("cited_evidence_ids must be an immutable tuple")

        if self.status is GroundedAnswerStatus.ANSWERED:
            if not isinstance(self.answer_text, str) or not self.answer_text.strip():
                raise ValueError("answered generation requires answer_text")
            if not isinstance(self.generator_id, str) or not self.generator_id.strip():
                raise ValueError("answered generation requires generator_id")
            if not self.cited_evidence_ids:
                raise ValueError("answered generation requires at least one citation")
        else:
            if self.answer_text is not None or self.generator_id is not None:
                raise ValueError("insufficient evidence cannot contain generated text")
            if self.cited_evidence_ids:
                raise ValueError("insufficient evidence cannot contain citations")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "packet": self.packet.to_dict(),
            "answer_text": self.answer_text,
            "generator_id": self.generator_id,
            "cited_evidence_ids": list(self.cited_evidence_ids),
        }


Generator = Callable[[GroundingPacket], GeneratedDraft]


def build_grounding_packet(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    query: str,
    mode: LexicalSearchMode | str = LexicalSearchMode.TOKEN,
    filters: StructuralSearchFilters | None = None,
    limit: int = 5,
    before: int = 1,
    after: int = 1,
    page_local: bool = True,
) -> GroundingPacket:
    """Retrieve exact evidence and expand each hit into bounded source context."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    _require_nonnegative(before, "before")
    _require_nonnegative(after, "after")
    if not isinstance(page_local, bool):
        raise ValueError("page_local must be boolean")
    if filters is not None and not isinstance(filters, StructuralSearchFilters):
        raise ValueError("filters must be StructuralSearchFilters")
    try:
        normalized_mode = mode if isinstance(mode, LexicalSearchMode) else LexicalSearchMode(mode)
    except (TypeError, ValueError) as exc:
        raise ValueError("mode must be exact, phrase, or token") from exc

    normalized_query = query.strip()
    if filters is None:
        results = search_evidence_store(
            path,
            artifact=artifact,
            query=normalized_query,
            mode=normalized_mode,
            limit=limit,
        )
    else:
        results = structural_search_evidence_store(
            path,
            artifact=artifact,
            query=normalized_query,
            mode=normalized_mode,
            filters=filters,
            limit=limit,
        )

    chunks = tuple(
        GroundingChunk(
            result=result,
            context=expand_evidence_context(
                path,
                artifact=artifact,
                evidence_id=result.evidence.evidence_id,
                before=before,
                after=after,
                page_local=page_local,
            ),
        )
        for result in results
    )
    return GroundingPacket(
        artifact=artifact,
        query=normalized_query,
        mode=normalized_mode,
        chunks=chunks,
        page_local=page_local,
    )


def run_grounded_generation(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    query: str,
    generator: Generator,
    mode: LexicalSearchMode | str = LexicalSearchMode.TOKEN,
    filters: StructuralSearchFilters | None = None,
    limit: int = 5,
    before: int = 1,
    after: int = 1,
    page_local: bool = True,
) -> GroundedGenerationResult:
    """Run a caller-controlled generator and validate its evidence citations."""

    if not callable(generator):
        raise ValueError("generator must be callable")
    packet = build_grounding_packet(
        path,
        artifact=artifact,
        query=query,
        mode=mode,
        filters=filters,
        limit=limit,
        before=before,
        after=after,
        page_local=page_local,
    )
    if not packet.chunks:
        return GroundedGenerationResult(
            status=GroundedAnswerStatus.INSUFFICIENT_EVIDENCE,
            packet=packet,
        )

    draft = generator(packet)
    if not isinstance(draft, GeneratedDraft):
        raise ValueError("generator must return a GeneratedDraft")
    if not draft.cited_evidence_ids:
        raise ValueError("generated answer requires at least one grounded citation")

    allowed = set(packet.evidence_ids)
    unknown = tuple(
        evidence_id
        for evidence_id in draft.cited_evidence_ids
        if evidence_id not in allowed
    )
    if unknown:
        raise ValueError("generated citation is not present in the grounding packet")

    return GroundedGenerationResult(
        status=GroundedAnswerStatus.ANSWERED,
        packet=packet,
        answer_text=draft.text,
        generator_id=draft.generator_id,
        cited_evidence_ids=draft.cited_evidence_ids,
    )


def _require_nonnegative(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
