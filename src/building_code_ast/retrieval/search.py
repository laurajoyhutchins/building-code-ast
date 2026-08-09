"""Publication-neutral lexical retrieval over the local source evidence store."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
import sqlite3

from .model import SourceArtifactIdentity, SourceEvidence
from .store import read_evidence_store


class LexicalSearchMode(StrEnum):
    EXACT = "exact"
    PHRASE = "phrase"
    TOKEN = "token"


@dataclass(frozen=True, slots=True)
class LexicalSearchResult:
    evidence: SourceEvidence
    mode: LexicalSearchMode
    retrieval_score: float
    score_method: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, SourceEvidence):
            raise ValueError("evidence must be SourceEvidence")
        if not isinstance(self.mode, LexicalSearchMode):
            raise ValueError("mode must be a LexicalSearchMode")
        if isinstance(self.retrieval_score, bool) or not isinstance(self.retrieval_score, (int, float)):
            raise ValueError("retrieval_score must be numeric")
        if not isinstance(self.score_method, str) or not self.score_method.strip():
            raise ValueError("score_method must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence.evidence_id,
            "source_id": self.evidence.source_id,
            "publication_key": self.evidence.publication_key,
            "source_sha256": self.evidence.source_sha256,
            "pdf_page": self.evidence.pdf_page,
            "printed_page": self.evidence.printed_page,
            "block_index": self.evidence.block_index,
            "bbox": None if self.evidence.bbox is None else list(self.evidence.bbox),
            "text": self.evidence.text,
            "extraction_method": self.evidence.extraction_method,
            "mode": self.mode.value,
            "retrieval_score": float(self.retrieval_score),
            "score_method": self.score_method,
        }


def search_evidence_store(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    query: str,
    mode: LexicalSearchMode | str = LexicalSearchMode.TOKEN,
    source_id: str | None = None,
    publication_key: str | None = None,
    limit: int = 20,
) -> tuple[LexicalSearchResult, ...]:
    """Search one validated local evidence store without assigning semantic confidence.

    Results are returned in deterministic physical source order. Retrieval score is
    metadata about the matching method only and does not affect source authority.
    """

    if not isinstance(artifact, SourceArtifactIdentity):
        raise ValueError("artifact must be a SourceArtifactIdentity")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must not be empty")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    try:
        normalized_mode = mode if isinstance(mode, LexicalSearchMode) else LexicalSearchMode(mode)
    except (TypeError, ValueError) as exc:
        raise ValueError("mode must be exact, phrase, or token") from exc

    records = read_evidence_store(path, artifact=artifact)
    if source_id is not None and source_id != artifact.source_id:
        return ()
    if publication_key is not None and publication_key != artifact.publication_key:
        return ()

    needle = query.strip()
    if normalized_mode is LexicalSearchMode.EXACT:
        matched = _literal_matches(records, needle, case_sensitive=True)
        results = [
            LexicalSearchResult(
                evidence=item,
                mode=normalized_mode,
                retrieval_score=float(item.text.count(needle)),
                score_method="literal_occurrence_count",
            )
            for item in matched
        ]
    elif normalized_mode is LexicalSearchMode.PHRASE:
        folded = needle.casefold()
        matched = _literal_matches(records, folded, case_sensitive=False)
        results = [
            LexicalSearchResult(
                evidence=item,
                mode=normalized_mode,
                retrieval_score=float(item.text.casefold().count(folded)),
                score_method="casefold_phrase_occurrence_count",
            )
            for item in matched
        ]
    else:
        results = list(_token_results(records, needle))

    results.sort(key=lambda result: (
        result.evidence.pdf_page,
        result.evidence.block_index,
        result.evidence.evidence_id,
    ))
    return tuple(results[:limit])


def _literal_matches(
    records: tuple[SourceEvidence, ...],
    needle: str,
    *,
    case_sensitive: bool,
) -> tuple[SourceEvidence, ...]:
    if case_sensitive:
        return tuple(item for item in records if needle in item.text)
    return tuple(item for item in records if needle in item.text.casefold())


def _token_results(
    records: tuple[SourceEvidence, ...],
    query: str,
) -> tuple[LexicalSearchResult, ...]:
    tokens = tuple(re.findall(r"\w+", query.casefold(), flags=re.UNICODE))
    if not tokens:
        raise ValueError("query must contain searchable tokens for token mode")

    try:
        return _fts5_token_results(records, tokens)
    except sqlite3.OperationalError:
        return _fallback_token_results(records, tokens)


def _fts5_token_results(
    records: tuple[SourceEvidence, ...],
    tokens: tuple[str, ...],
) -> tuple[LexicalSearchResult, ...]:
    with sqlite3.connect(":memory:") as database:
        database.execute(
            "CREATE VIRTUAL TABLE evidence_fts USING fts5(evidence_id UNINDEXED, text)"
        )
        database.executemany(
            "INSERT INTO evidence_fts(evidence_id, text) VALUES (?, ?)",
            ((item.evidence_id, item.text) for item in records),
        )
        fts_query = " ".join(f'"{token}"' for token in tokens)
        rows = database.execute(
            "SELECT evidence_id, bm25(evidence_fts) FROM evidence_fts WHERE evidence_fts MATCH ?",
            (fts_query,),
        ).fetchall()

    ranks = {str(evidence_id): float(rank) for evidence_id, rank in rows}
    by_id = {item.evidence_id: item for item in records}
    return tuple(
        LexicalSearchResult(
            evidence=by_id[evidence_id],
            mode=LexicalSearchMode.TOKEN,
            retrieval_score=max(0.0, -rank),
            score_method="sqlite_fts5_bm25",
        )
        for evidence_id, rank in ranks.items()
        if evidence_id in by_id
    )


def _fallback_token_results(
    records: tuple[SourceEvidence, ...],
    tokens: tuple[str, ...],
) -> tuple[LexicalSearchResult, ...]:
    results: list[LexicalSearchResult] = []
    for item in records:
        folded = item.text.casefold()
        if not all(token in folded for token in tokens):
            continue
        score = sum(folded.count(token) for token in tokens) / len(tokens)
        results.append(
            LexicalSearchResult(
                evidence=item,
                mode=LexicalSearchMode.TOKEN,
                retrieval_score=float(score),
                score_method="token_coverage_fallback",
            )
        )
    return tuple(results)
