"""Publication-neutral source evidence identity and serialization.

This module describes addressable observations from an exact source artifact.
It deliberately does not assign AST meaning or retrieval confidence.
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
    """Exact private/publication artifact identity used by source evidence."""

    publication_key: str
    sha256: str
    size: int
    page_count: int

    def __post_init__(self) -> None:
        if not self.publication_key or self.publication_key != self.publication_key.strip():
            raise ValueError("publication_key must be non-empty and trimmed")
        if not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be a lowercase 64-character hexadecimal digest")
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size <= 0:
            raise ValueError("size must be a positive integer")
        if (
            isinstance(self.page_count, bool)
            or not isinstance(self.page_count, int)
            or self.page_count <= 0
        ):
            raise ValueError("page_count must be a positive integer")

    def to_dict(self) -> dict[str, str | int]:
        return {
            "publication_key": self.publication_key,
            "sha256": self.sha256,
            "size": self.size,
            "page_count": self.page_count,
        }


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """One addressable source observation with provenance-preserving coordinates."""

    evidence_id: str
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
        if isinstance(pdf_page, bool) or not isinstance(pdf_page, int):
            raise ValueError("pdf_page must be an integer")
        if not 1 <= pdf_page <= artifact.page_count:
            raise ValueError("pdf_page must fall within the source artifact page range")
        if isinstance(block_index, bool) or not isinstance(block_index, int) or block_index < 0:
            raise ValueError("block_index must be a non-negative integer")
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        if not extraction_method or extraction_method != extraction_method.strip():
            raise ValueError("extraction_method must be non-empty and trimmed")
        if printed_page is not None and (
            not isinstance(printed_page, str)
            or not printed_page
            or printed_page != printed_page.strip()
        ):
            raise ValueError("printed_page must be a non-empty trimmed string when supplied")

        normalized_bbox = _normalize_bbox(bbox)
        normalized_observed = _normalize_metadata(observed_metadata, name="observed_metadata")
        normalized_derived = _normalize_metadata(derived_metadata, name="derived_metadata")
        evidence_id = source_evidence_id(
            source_sha256=artifact.sha256,
            pdf_page=pdf_page,
            block_index=block_index,
            bbox=normalized_bbox,
        )
        return cls(
            evidence_id=evidence_id,
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
    """Return a stable ID based only on exact artifact and source coordinates."""

    if not _SHA256_RE.fullmatch(source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
    canonical = json.dumps(
        {
            "identity_version": SOURCE_EVIDENCE_IDENTITY_VERSION,
            "source_sha256": source_sha256,
            "pdf_page": pdf_page,
            "block_index": block_index,
            "bbox": list(bbox) if bbox is not None else None,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"evidence:sha256:{digest}"


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
    *,
    name: str,
) -> MetadataItems:
    if metadata is None:
        return ()
    if not isinstance(metadata, Mapping):
        raise ValueError(f"{name} must be a mapping")

    items: list[tuple[str, MetadataValue]] = []
    for key, value in metadata.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError(f"{name} keys must be non-empty trimmed strings")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{name} values must be finite JSON scalar values")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"{name} values must be JSON scalar values")
        items.append((key, value))
    return tuple(sorted(items))
