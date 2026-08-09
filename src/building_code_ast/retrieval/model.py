"""Publication-neutral addressable evidence for local source retrieval.

The source register remains authoritative for source provenance, rights, and
publication state. These types add only the local byte/page geometry needed to
address searchable observations from an exact artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Mapping, TypeAlias


SOURCE_EVIDENCE_IDENTITY_VERSION = "source-evidence/0.1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MetadataValue: TypeAlias = str | int | float | bool | None
MetadataItems: TypeAlias = tuple[tuple[str, MetadataValue], ...]
BoundingBox: TypeAlias = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class SourceArtifactIdentity:
    """Retrieval-local coordinates for one exact registered source artifact.

    ``source_id`` is the provenance link to the repository source register when
    the artifact is registered there. ``publication_key`` is a retrieval filter,
    not an independent publication-authority assertion.
    """

    source_id: str
    publication_key: str
    sha256: str
    size: int
    page_count: int

    def __post_init__(self) -> None:
        _require_trimmed_text(self.source_id, "source_id")
        _require_trimmed_text(self.publication_key, "publication_key")
        _require_sha256(self.sha256, "sha256")
        _require_positive_int(self.size, "size")
        _require_positive_int(self.page_count, "page_count")

    def to_dict(self) -> dict[str, str | int]:
        return {
            "source_id": self.source_id,
            "publication_key": self.publication_key,
            "sha256": self.sha256,
            "size": self.size,
            "page_count": self.page_count,
        }


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """One searchable source observation tied to exact physical coordinates."""

    evidence_id: str
    source_id: str
    publication_key: str
    source_sha256: str
    pdf_page: int
    block_index: int
    text: str
    bbox: BoundingBox | None
    extraction_method: str
    printed_page: str | None = None
    observed_metadata: MetadataItems = ()
    derived_metadata: MetadataItems = ()

    def __post_init__(self) -> None:
        _require_trimmed_text(self.source_id, "source_id")
        _require_trimmed_text(self.publication_key, "publication_key")
        _require_sha256(self.source_sha256, "source_sha256")
        _require_positive_int(self.pdf_page, "pdf_page")
        _require_nonnegative_int(self.block_index, "block_index")
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        _require_trimmed_text(self.extraction_method, "extraction_method")
        if self.printed_page is not None:
            _require_trimmed_text(self.printed_page, "printed_page")
        normalized_bbox = _normalize_bbox(self.bbox)
        if normalized_bbox != self.bbox:
            raise ValueError("bbox must use normalized finite float coordinates")
        _validate_metadata_items(self.observed_metadata, "observed_metadata")
        _validate_metadata_items(self.derived_metadata, "derived_metadata")
        expected_id = source_evidence_id(
            source_sha256=self.source_sha256,
            pdf_page=self.pdf_page,
            block_index=self.block_index,
            bbox=self.bbox,
        )
        if self.evidence_id != expected_id:
            raise ValueError("evidence_id does not match exact source coordinates")

    @classmethod
    def create(
        cls,
        *,
        artifact: SourceArtifactIdentity,
        pdf_page: int,
        block_index: int,
        text: str,
        extraction_method: str,
        bbox: tuple[float, float, float, float] | None = None,
        printed_page: str | None = None,
        observed_metadata: Mapping[str, MetadataValue] | None = None,
        derived_metadata: Mapping[str, MetadataValue] | None = None,
    ) -> "SourceEvidence":
        if not isinstance(artifact, SourceArtifactIdentity):
            raise ValueError("artifact must be a SourceArtifactIdentity")
        _require_positive_int(pdf_page, "pdf_page")
        if pdf_page > artifact.page_count:
            raise ValueError("pdf_page must fall within the source artifact page range")
        _require_nonnegative_int(block_index, "block_index")
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        _require_trimmed_text(extraction_method, "extraction_method")
        if printed_page is not None:
            _require_trimmed_text(printed_page, "printed_page")

        normalized_bbox = _normalize_bbox(bbox)
        normalized_observed = _normalize_metadata(observed_metadata, "observed_metadata")
        normalized_derived = _normalize_metadata(derived_metadata, "derived_metadata")
        return cls(
            evidence_id=source_evidence_id(
                source_sha256=artifact.sha256,
                pdf_page=pdf_page,
                block_index=block_index,
                bbox=normalized_bbox,
            ),
            source_id=artifact.source_id,
            publication_key=artifact.publication_key,
            source_sha256=artifact.sha256,
            pdf_page=pdf_page,
            block_index=block_index,
            text=text,
            bbox=normalized_bbox,
            extraction_method=extraction_method,
            printed_page=printed_page,
            observed_metadata=normalized_observed,
            derived_metadata=normalized_derived,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "publication_key": self.publication_key,
            "source_sha256": self.source_sha256,
            "pdf_page": self.pdf_page,
            "printed_page": self.printed_page,
            "block_index": self.block_index,
            "text": self.text,
            "bbox": list(self.bbox) if self.bbox is not None else None,
            "extraction_method": self.extraction_method,
            "observed_metadata": dict(self.observed_metadata),
            "derived_metadata": dict(self.derived_metadata),
        }


def source_evidence_id(
    *,
    source_sha256: str,
    pdf_page: int,
    block_index: int,
    bbox: BoundingBox | None,
) -> str:
    """Return deterministic evidence identity from exact bytes and coordinates."""

    _require_sha256(source_sha256, "source_sha256")
    _require_positive_int(pdf_page, "pdf_page")
    _require_nonnegative_int(block_index, "block_index")
    normalized_bbox = _normalize_bbox(bbox)
    canonical = json.dumps(
        {
            "identity_version": SOURCE_EVIDENCE_IDENTITY_VERSION,
            "source_sha256": source_sha256,
            "pdf_page": pdf_page,
            "block_index": block_index,
            "bbox": list(normalized_bbox) if normalized_bbox is not None else None,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"evidence:sha256:{digest}"


def _require_trimmed_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty trimmed string")


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _require_positive_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_nonnegative_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _normalize_bbox(
    bbox: tuple[float, float, float, float] | None,
) -> BoundingBox | None:
    if bbox is None:
        return None
    if not isinstance(bbox, tuple) or len(bbox) != 4:
        raise ValueError("bbox must be a four-value tuple")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in bbox):
        raise ValueError("bbox values must be finite numbers")
    normalized = tuple(float(value) for value in bbox)
    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("bbox values must be finite numbers")
    x0, y0, x1, y1 = normalized
    if x1 <= x0 or y1 <= y0:
        raise ValueError("bbox must have positive area")
    return (x0, y0, x1, y1)


def _normalize_metadata(
    metadata: Mapping[str, MetadataValue] | None,
    label: str,
) -> MetadataItems:
    if metadata is None:
        return ()
    if not isinstance(metadata, Mapping):
        raise ValueError(f"{label} must be a mapping")
    normalized = tuple(sorted(metadata.items()))
    _validate_metadata_items(normalized, label)
    return normalized


def _validate_metadata_items(items: MetadataItems, label: str) -> None:
    if not isinstance(items, tuple):
        raise ValueError(f"{label} must be an immutable tuple")
    if tuple(sorted(items)) != items:
        raise ValueError(f"{label} must be sorted by key")
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(f"{label} entries must be key/value tuples")
        key, value = item
        _require_trimmed_text(key, f"{label} key")
        if key in seen:
            raise ValueError(f"{label} contains duplicate key: {key}")
        seen.add(key)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{label} values must be finite JSON scalars")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"{label} values must be JSON scalar values")
