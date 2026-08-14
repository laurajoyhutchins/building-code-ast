"""Publication-neutral provenance for raster/OCR recovery observations.

This module owns only recovery evidence: exact source identity, page/region
coordinates, render and recovery tooling, digests, retention state, operations,
and warnings. It deliberately contains no publication locator grammar, source
role inference, or semantic authority rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
from typing import Iterable


RECOVERY_OBSERVATION_SCHEMA = "recovery-observation-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CoordinateSpace(StrEnum):
    PDF_POINTS = "pdf_points"
    RASTER_PIXELS = "raster_pixels"


class RecoverySourceKind(StrEnum):
    RASTER_RECOVERY = "raster_recovery"
    OCR_RECOVERY = "ocr_recovery"


class RecoveredTextPayloadState(StrEnum):
    """Whether the recovered expression is available for verified private reuse."""

    DIGEST_ONLY = "digest_only"
    PRIVATE_RETRIEVABLE = "private_retrievable"


@dataclass(frozen=True, slots=True)
class RecoverySourceIdentity:
    sha256: str
    size_bytes: int
    page_count: int
    media_type: str

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("source SHA-256 must be lowercase hexadecimal")
        if self.size_bytes < 1:
            raise ValueError("source size_bytes must be positive")
        if self.page_count < 1:
            raise ValueError("source page_count must be positive")
        if not self.media_type.strip():
            raise ValueError("source media_type must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "media_type": self.media_type,
        }


@dataclass(frozen=True, slots=True)
class RecoveryRegion:
    page_number: int
    coordinate_space: CoordinateSpace
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("recovery page_number must be positive")
        if not isinstance(self.coordinate_space, CoordinateSpace):
            object.__setattr__(self, "coordinate_space", CoordinateSpace(self.coordinate_space))
        if self.bbox is None:
            return
        x0, y0, x1, y1 = self.bbox
        if x1 < x0 or y1 < y0:
            raise ValueError("recovery bbox must be ordered as (x0, y0, x1, y1)")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "page_number": self.page_number,
            "scope": "full_page" if self.bbox is None else "region",
            "coordinate_space": self.coordinate_space.value,
        }
        if self.bbox is not None:
            payload["bbox"] = [round(value, 6) for value in self.bbox]
        return payload


def _normalized_parameters(
    parameters: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    normalized = tuple((str(key).strip(), str(value).strip()) for key, value in parameters)
    if any(not key or not value for key, value in normalized):
        raise ValueError("recovery tool parameters require non-empty keys and values")
    keys = [key for key, _value in normalized]
    if len(keys) != len(set(keys)):
        raise ValueError("recovery tool parameter keys must be unique")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class RecoveryTool:
    backend: str
    version: str
    parameters: tuple[tuple[str, str], ...] = ()
    output_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.backend.strip():
            raise ValueError("recovery tool backend must be non-empty")
        if not self.version.strip():
            raise ValueError("recovery tool version must be non-empty")
        object.__setattr__(self, "parameters", _normalized_parameters(self.parameters))
        if self.output_sha256 is not None and _SHA256_RE.fullmatch(self.output_sha256) is None:
            raise ValueError("recovery tool output SHA-256 must be lowercase hexadecimal")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "backend": self.backend,
            "version": self.version,
            "parameters": {key: value for key, value in self.parameters},
        }
        if self.output_sha256 is not None:
            payload["output_sha256"] = self.output_sha256
        return payload


def _validated_strings(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{label} entries must be non-empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} entries must be unique")
    return normalized


@dataclass(frozen=True, slots=True)
class RecoveryObservation:
    source: RecoverySourceIdentity
    region: RecoveryRegion
    source_kind: RecoverySourceKind
    render: RecoveryTool
    recovery: RecoveryTool
    recovered_text_sha256: str
    payload_state: RecoveredTextPayloadState
    performed_operations: tuple[str, ...] = ()
    omitted_operations: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.region.page_number > self.source.page_count:
            raise ValueError("recovery region page exceeds exact source page count")
        if not isinstance(self.source_kind, RecoverySourceKind):
            object.__setattr__(self, "source_kind", RecoverySourceKind(self.source_kind))
        if not isinstance(self.payload_state, RecoveredTextPayloadState):
            object.__setattr__(
                self,
                "payload_state",
                RecoveredTextPayloadState(self.payload_state),
            )
        if _SHA256_RE.fullmatch(self.recovered_text_sha256) is None:
            raise ValueError("recovered-text SHA-256 must be lowercase hexadecimal")
        object.__setattr__(
            self,
            "performed_operations",
            _validated_strings(self.performed_operations, label="performed operation"),
        )
        object.__setattr__(
            self,
            "omitted_operations",
            _validated_strings(self.omitted_operations, label="omitted operation"),
        )
        object.__setattr__(
            self,
            "warnings",
            _validated_strings(self.warnings, label="warning"),
        )

    @property
    def downstream_payload_available(self) -> bool:
        return self.payload_state is RecoveredTextPayloadState.PRIVATE_RETRIEVABLE

    def verify_private_payload(self, recovered_text: str) -> None:
        """Authorize private downstream use only for a retained, digest-bound payload."""

        if self.payload_state is RecoveredTextPayloadState.DIGEST_ONLY:
            raise ValueError("digest-only recovery observation has no retrievable payload authority")
        observed = hashlib.sha256(recovered_text.encode("utf-8")).hexdigest()
        if observed != self.recovered_text_sha256:
            raise ValueError("private recovered-text payload digest does not match observation")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": RECOVERY_OBSERVATION_SCHEMA,
            "source": self.source.to_dict(),
            "region": self.region.to_dict(),
            "source_kind": self.source_kind.value,
            "render": self.render.to_dict(),
            "recovery": self.recovery.to_dict(),
            "recovered_text_sha256": self.recovered_text_sha256,
            "payload_state": self.payload_state.value,
            "performed_operations": list(self.performed_operations),
            "omitted_operations": list(self.omitted_operations),
            "warnings": list(self.warnings),
        }
