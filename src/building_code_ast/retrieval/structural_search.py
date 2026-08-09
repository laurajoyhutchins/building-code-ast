"""Publication-neutral structural filtering over lexical source retrieval.

Structural filters constrain source observations only. They do not alter lexical
retrieval scores or assign semantic confidence, authority, or AST meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from pathlib import Path

from .model import SourceArtifactIdentity, SourceEvidence
from .search import (
    LexicalSearchMode,
    LexicalSearchResult,
    search_evidence_store,
)
from .store import read_evidence_store


class StructuralCandidate(StrEnum):
    HEADING = "heading"
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"


@dataclass(frozen=True, slots=True)
class StructuralSearchFilters:
    candidate: StructuralCandidate | str | None = None
    pdf_page_min: int | None = None
    pdf_page_max: int | None = None
    min_font_size: float | None = None
    max_font_size: float | None = None
    min_relative_font_size: float | None = None
    max_relative_font_size: float | None = None

    def __post_init__(self) -> None:
        if self.candidate is not None:
            try:
                candidate = (
                    self.candidate
                    if isinstance(self.candidate, StructuralCandidate)
                    else StructuralCandidate(self.candidate)
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "candidate must be heading, table, figure, or equation"
                ) from exc
            object.__setattr__(self, "candidate", candidate)

        page_min = _optional_positive_int(self.pdf_page_min, "minimum page")
        page_max = _optional_positive_int(self.pdf_page_max, "maximum page")
        if page_min is not None and page_max is not None and page_min > page_max:
            raise ValueError("page range minimum must not exceed maximum")

        font_min = _optional_positive_float(self.min_font_size, "minimum font size")
        font_max = _optional_positive_float(self.max_font_size, "maximum font size")
        if font_min is not None and font_max is not None and font_min > font_max:
            raise ValueError("font size range minimum must not exceed maximum")

        relative_min = _optional_positive_float(
            self.min_relative_font_size,
            "minimum relative font size",
        )
        relative_max = _optional_positive_float(
            self.max_relative_font_size,
            "maximum relative font size",
        )
        if (
            relative_min is not None
            and relative_max is not None
            and relative_min > relative_max
        ):
            raise ValueError(
                "relative font size range minimum must not exceed maximum"
            )

        object.__setattr__(self, "pdf_page_min", page_min)
        object.__setattr__(self, "pdf_page_max", page_max)
        object.__setattr__(self, "min_font_size", font_min)
        object.__setattr__(self, "max_font_size", font_max)
        object.__setattr__(self, "min_relative_font_size", relative_min)
        object.__setattr__(self, "max_relative_font_size", relative_max)


def structural_search_evidence_store(
    path: Path | str,
    *,
    artifact: SourceArtifactIdentity,
    query: str,
    mode: LexicalSearchMode | str = LexicalSearchMode.TOKEN,
    source_id: str | None = None,
    publication_key: str | None = None,
    filters: StructuralSearchFilters | None = None,
    limit: int = 20,
) -> tuple[LexicalSearchResult, ...]:
    """Apply structural observation filters to lexical retrieval results.

    Lexical matching and score calculation remain owned by ``search_evidence_store``.
    The lexical match set is obtained before structural filtering so ``limit`` is
    applied only after the structural constraints have been evaluated.
    """

    if filters is not None and not isinstance(filters, StructuralSearchFilters):
        raise ValueError("filters must be StructuralSearchFilters")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    records = read_evidence_store(path, artifact=artifact)
    lexical_results = search_evidence_store(
        path,
        artifact=artifact,
        query=query,
        mode=mode,
        source_id=source_id,
        publication_key=publication_key,
        limit=max(1, len(records)),
    )

    if filters is None:
        return lexical_results[:limit]

    filtered = tuple(
        result
        for result in lexical_results
        if _matches_filters(result.evidence, filters)
    )
    return filtered[:limit]


def _matches_filters(
    evidence: SourceEvidence,
    filters: StructuralSearchFilters,
) -> bool:
    if filters.pdf_page_min is not None and evidence.pdf_page < filters.pdf_page_min:
        return False
    if filters.pdf_page_max is not None and evidence.pdf_page > filters.pdf_page_max:
        return False

    observed = dict(evidence.observed_metadata)
    derived = dict(evidence.derived_metadata)

    if filters.candidate is not None:
        candidate = filters.candidate
        if not isinstance(candidate, StructuralCandidate):
            raise ValueError("candidate filter was not normalized")
        if derived.get(f"candidate.{candidate.value}") is not True:
            return False

    if not _numeric_metadata_in_range(
        observed.get("font.size"),
        minimum=filters.min_font_size,
        maximum=filters.max_font_size,
    ):
        return False
    if not _numeric_metadata_in_range(
        derived.get("font.relative_size"),
        minimum=filters.min_relative_font_size,
        maximum=filters.max_relative_font_size,
    ):
        return False
    return True


def _numeric_metadata_in_range(
    value: object,
    *,
    minimum: float | None,
    maximum: float | None,
) -> bool:
    if minimum is None and maximum is None:
        return True
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    if not math.isfinite(number):
        return False
    if minimum is not None and number < minimum:
        return False
    if maximum is not None and number > maximum:
        return False
    return True


def _optional_positive_int(value: int | None, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _optional_positive_float(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive finite number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return normalized
