"""Shared value types for normalized source provenance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceRole(StrEnum):
    NORMATIVE_TEXT = "normative_text"
    OFFICIAL_CORRECTION = "official_correction"
    DEVELOPMENT_HISTORY = "development_history"
    JURISDICTIONAL_LAW = "jurisdictional_law"
    ADMINISTRATIVE_GUIDANCE = "administrative_guidance"
    OFFICIAL_INTERPRETATION = "official_interpretation"
    COMMENTARY = "commentary"
    SECONDARY_ANALYSIS = "secondary_analysis"


class AccessScope(StrEnum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    LICENSED_LOCAL = "licensed_local"
    PRIVATE_LOCAL = "private_local"


class RightsStatus(StrEnum):
    PUBLIC_OFFICIAL = "public_official"
    PUBLIC_DOMAIN = "public_domain"
    LICENSED = "licensed"
    PROJECT_AUTHORED = "project_authored"
    UNCERTAIN_RESTRICTED = "uncertain_restricted"


EVIDENCE_ROLE_VALUES = frozenset(item.value for item in EvidenceRole)
ACCESS_SCOPE_VALUES = frozenset(item.value for item in AccessScope)
RIGHTS_STATUS_VALUES = frozenset(item.value for item in RightsStatus)


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


@dataclass(frozen=True, slots=True)
class AstSourceIdentity:
    """Stable AST-facing identity, independent of storage coordinates."""

    artifact_id: str
    edition_id: str

    def __post_init__(self) -> None:
        _require_text(self.artifact_id, "artifact_id")
        _require_text(self.edition_id, "edition_id")

    def to_dict(self) -> dict[str, str]:
        return {"artifact_id": self.artifact_id, "edition_id": self.edition_id}
