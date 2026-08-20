"""Guarded execution boundary for normalized source evidence adapters."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Generic, Protocol, TypeVar

from ..model import DiagnosticSeverity
from .model import EvidenceRole
from .source_packages import Artifact, ArtifactBinding

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
class BoundArtifact:
    binding: ArtifactBinding
    artifact: Artifact

    def __post_init__(self) -> None:
        if not isinstance(self.binding, ArtifactBinding) or not isinstance(self.artifact, Artifact):
            raise ValueError("binding and artifact must use normalized provenance types")
        if self.binding.artifact_id != self.artifact.artifact_id:
            raise ValueError("binding artifact_id does not match artifact identity")

    @property
    def source_id(self) -> str:
        return self.binding.source_id

    @property
    def evidence_role(self) -> EvidenceRole:
        return self.binding.evidence_role

    @property
    def media_type(self) -> str:
        return self.artifact.media_type

    @property
    def sha256(self) -> str:
        return self.artifact.sha256

    @property
    def ast_source(self):
        return self.binding.ast_source


@dataclass(frozen=True, slots=True)
class SourceRegion:
    page: int | None = None
    anchor: str | None = None
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.page is None and self.anchor is None and self.bbox is None:
            raise ValueError("source region must contain at least one locator")
        if self.page is not None and (isinstance(self.page, bool) or not isinstance(self.page, int) or self.page < 1):
            raise ValueError("page must be a positive integer or null")
        if self.anchor is not None:
            _require_text(self.anchor, "anchor")
        if self.bbox is not None:
            if self.page is None or not isinstance(self.bbox, tuple) or len(self.bbox) != 4:
                raise ValueError("page and four-coordinate bbox are required")
            x0, y0, x1, y1 = (_coordinate(value, f"bbox[{index}]") for index, value in enumerate(self.bbox))
            if x1 <= x0 or y1 <= y0:
                raise ValueError("bbox must have positive area")

    def to_dict(self) -> dict[str, Any]:
        return {"page": self.page, "anchor": self.anchor, "bbox": list(self.bbox) if self.bbox is not None else None}


@dataclass(frozen=True, slots=True)
class EvidenceDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    region: SourceRegion | None = None

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise ValueError("severity must be a DiagnosticSeverity")
        _require_text(self.message, "message")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity.value, "message": self.message, "region": self.region.to_dict() if self.region is not None else None}


@dataclass(frozen=True, slots=True)
class AdapterResult(Generic[RecordT]):
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


class EvidenceAdapter(Protocol[RecordT]):
    adapter_id: str
    adapter_version: str
    supported_roles: frozenset[EvidenceRole]
    supported_media_types: frozenset[str]
    def extract(self, source: BoundArtifact, content: bytes) -> AdapterResult[RecordT]: ...


def _adapter_metadata(adapter: EvidenceAdapter[RecordT]):
    adapter_id = getattr(adapter, "adapter_id", None)
    adapter_version = getattr(adapter, "adapter_version", None)
    supported_roles = getattr(adapter, "supported_roles", None)
    supported_media_types = getattr(adapter, "supported_media_types", None)
    _require_text(adapter_id, "adapter_id")
    _require_text(adapter_version, "adapter_version")
    if not isinstance(supported_roles, frozenset) or not supported_roles or any(not isinstance(role, EvidenceRole) for role in supported_roles):
        raise ValueError("supported_roles must be a nonempty EvidenceRole frozenset")
    if not isinstance(supported_media_types, frozenset) or not supported_media_types:
        raise ValueError("supported_media_types must be a nonempty frozenset")
    return adapter_id, adapter_version, supported_roles, supported_media_types


def run_evidence_adapter(adapter: EvidenceAdapter[RecordT], binding: ArtifactBinding, artifact: Artifact, content: bytes) -> AdapterResult[RecordT]:
    source = BoundArtifact(binding=binding, artifact=artifact)
    if not isinstance(content, bytes):
        raise ValueError("content must be bytes")
    adapter_id, adapter_version, supported_roles, supported_media_types = _adapter_metadata(adapter)
    if source.evidence_role not in supported_roles:
        raise ValueError(f"adapter {adapter_id} does not support evidence role {source.evidence_role.value}")
    if source.media_type not in supported_media_types:
        raise ValueError(f"adapter {adapter_id} does not support media type {source.media_type}")
    if hashlib.sha256(content).hexdigest() != source.sha256:
        raise ValueError("source content SHA-256 does not match the canonical artifact")
    result = adapter.extract(source, content)
    if not isinstance(result, AdapterResult):
        raise ValueError("adapter extract must return an AdapterResult")
    if result.source_id != source.source_id or result.adapter_id != adapter_id or result.adapter_version != adapter_version:
        raise ValueError("adapter result identity does not match invocation")
    return result
