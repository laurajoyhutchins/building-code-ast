"""Guarded execution boundary for source-family evidence adapters."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Generic, Protocol, TypeVar

from ..model import DiagnosticSeverity
from .model import EvidenceRole, SourceRegisterEntry


RecordT = TypeVar("RecordT")


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _coordinate(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{label} must be a finite number")
    return normalized


@dataclass(frozen=True, slots=True)
class SourceRegion:
    """A reviewable location inside one registered source artifact."""

    page: int | None = None
    anchor: str | None = None
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.page is None and self.anchor is None and self.bbox is None:
            raise ValueError("source region must contain at least one locator")
        if self.page is not None and (
            isinstance(self.page, bool) or not isinstance(self.page, int) or self.page < 1
        ):
            raise ValueError("page must be a positive integer or null")
        if self.anchor is not None:
            _require_text(self.anchor, "anchor")
        if self.bbox is not None:
            if self.page is None:
                raise ValueError("page is required when bbox is present")
            if not isinstance(self.bbox, tuple) or len(self.bbox) != 4:
                raise ValueError("bbox must contain four coordinates")
            x0, y0, x1, y1 = (
                _coordinate(value, f"bbox[{index}]")
                for index, value in enumerate(self.bbox)
            )
            if x1 <= x0 or y1 <= y0:
                raise ValueError("bbox must have positive area")

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "anchor": self.anchor,
            "bbox": list(self.bbox) if self.bbox is not None else None,
        }


@dataclass(frozen=True, slots=True)
class EvidenceDiagnostic:
    """One source-located adapter diagnostic."""

    code: str
    severity: DiagnosticSeverity
    message: str
    region: SourceRegion | None = None

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise ValueError("severity must be a DiagnosticSeverity")
        _require_text(self.message, "message")
        if self.region is not None and not isinstance(self.region, SourceRegion):
            raise ValueError("region must be a SourceRegion or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "region": self.region.to_dict() if self.region is not None else None,
        }


@dataclass(frozen=True, slots=True)
class AdapterResult(Generic[RecordT]):
    """Typed records and review evidence emitted by one adapter invocation."""

    source_id: str
    adapter_id: str
    adapter_version: str
    records: tuple[RecordT, ...]
    diagnostics: tuple[EvidenceDiagnostic, ...] = ()
    unsupported_regions: tuple[SourceRegion, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.adapter_id, "adapter_id")
        _require_text(self.adapter_version, "adapter_version")
        if not isinstance(self.records, tuple):
            raise ValueError("records must be a tuple")
        if not isinstance(self.diagnostics, tuple) or any(
            not isinstance(item, EvidenceDiagnostic) for item in self.diagnostics
        ):
            raise ValueError("diagnostics must contain EvidenceDiagnostic values")
        if not isinstance(self.unsupported_regions, tuple) or any(
            not isinstance(item, SourceRegion) for item in self.unsupported_regions
        ):
            raise ValueError("unsupported_regions must contain SourceRegion values")


class EvidenceAdapter(Protocol[RecordT]):
    """Contract implemented by one source-family extraction adapter."""

    adapter_id: str
    adapter_version: str
    supported_roles: frozenset[EvidenceRole]
    supported_media_types: frozenset[str]

    def extract(
        self,
        source: SourceRegisterEntry,
        content: bytes,
    ) -> AdapterResult[RecordT]: ...


def _adapter_metadata(
    adapter: EvidenceAdapter[RecordT],
) -> tuple[str, str, frozenset[EvidenceRole], frozenset[str]]:
    adapter_id = getattr(adapter, "adapter_id", None)
    adapter_version = getattr(adapter, "adapter_version", None)
    supported_roles = getattr(adapter, "supported_roles", None)
    supported_media_types = getattr(adapter, "supported_media_types", None)

    _require_text(adapter_id, "adapter_id")
    _require_text(adapter_version, "adapter_version")
    if not isinstance(supported_roles, frozenset) or not supported_roles:
        raise ValueError("supported_roles must be a nonempty frozenset")
    if any(not isinstance(role, EvidenceRole) for role in supported_roles):
        raise ValueError("supported_roles must contain EvidenceRole values")
    if not isinstance(supported_media_types, frozenset) or not supported_media_types:
        raise ValueError("supported_media_types must be a nonempty frozenset")
    for media_type in supported_media_types:
        _require_text(media_type, "supported media type")

    return adapter_id, adapter_version, supported_roles, supported_media_types


def run_evidence_adapter(
    adapter: EvidenceAdapter[RecordT],
    source: SourceRegisterEntry,
    content: bytes,
) -> AdapterResult[RecordT]:
    """Verify source identity and adapter compatibility before extraction."""

    if not isinstance(source, SourceRegisterEntry):
        raise ValueError("source must be a SourceRegisterEntry")
    if not isinstance(content, bytes):
        raise ValueError("content must be bytes")

    adapter_id, adapter_version, supported_roles, supported_media_types = (
        _adapter_metadata(adapter)
    )
    if source.evidence_role not in supported_roles:
        raise ValueError(
            f"adapter {adapter_id} does not support evidence role "
            f"{source.evidence_role.value}"
        )
    if source.media_type not in supported_media_types:
        raise ValueError(
            f"adapter {adapter_id} does not support media type {source.media_type}"
        )

    actual_digest = hashlib.sha256(content).hexdigest()
    if actual_digest != source.sha256:
        raise ValueError(
            "source content SHA-256 does not match the registered source artifact"
        )

    result = adapter.extract(source, content)
    if not isinstance(result, AdapterResult):
        raise ValueError("adapter extract must return an AdapterResult")
    if result.source_id != source.source_id:
        raise ValueError("adapter result source_id does not match the source invocation")
    if result.adapter_id != adapter_id:
        raise ValueError("adapter result adapter_id does not match the adapter invocation")
    if result.adapter_version != adapter_version:
        raise ValueError(
            "adapter result adapter_version does not match the adapter invocation"
        )
    return result
