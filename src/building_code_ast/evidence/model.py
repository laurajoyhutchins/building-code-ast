"""Publication-neutral source evidence metadata.

This layer identifies exact source artifacts and their evidentiary role without
storing or interpreting source prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
import hashlib
import json
import re
from typing import Any


SOURCE_REGISTER_VERSION = "0.1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _require_optional_text(value: str | None, label: str) -> None:
    if value is not None:
        _require_text(value, label)


def _require_date(value: str | None, label: str) -> None:
    if value is None:
        return
    _require_text(value, label)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 date") from exc


def _require_timestamp(value: str, label: str) -> None:
    _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include a timezone offset")


@dataclass(frozen=True, slots=True)
class AstSourceIdentity:
    artifact_id: str
    edition_id: str

    def __post_init__(self) -> None:
        _require_text(self.artifact_id, "artifact_id")
        _require_text(self.edition_id, "edition_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_id": self.artifact_id,
            "edition_id": self.edition_id,
        }


@dataclass(frozen=True, slots=True)
class PublicationIdentity:
    publication_family: str
    edition: str
    printing: str | None = None
    digital_revision: str | None = None
    correction_set: str | None = None
    published_on: str | None = None
    effective_on: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.publication_family, "publication_family")
        _require_text(self.edition, "edition")
        _require_optional_text(self.printing, "printing")
        _require_optional_text(self.digital_revision, "digital_revision")
        _require_optional_text(self.correction_set, "correction_set")
        _require_date(self.published_on, "published_on")
        _require_date(self.effective_on, "effective_on")

    def identity_dict(self) -> dict[str, str | None]:
        return {
            "publication_family": self.publication_family,
            "edition": self.edition,
            "printing": self.printing,
            "digital_revision": self.digital_revision,
            "correction_set": self.correction_set,
            "published_on": self.published_on,
            "effective_on": self.effective_on,
        }

    def to_dict(self) -> dict[str, str | None]:
        return {
            "state_id": publication_state_id(self),
            **self.identity_dict(),
        }


def publication_state_id(publication: PublicationIdentity) -> str:
    """Return a deterministic identity for one publication state."""

    if not isinstance(publication, PublicationIdentity):
        raise TypeError("publication must be a PublicationIdentity")
    canonical = json.dumps(
        publication.identity_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"publication:{digest}"


@dataclass(frozen=True, slots=True)
class SourceRegisterEntry:
    source_id: str
    ast_source: AstSourceIdentity
    title: str
    issuing_body: str
    evidence_role: EvidenceRole
    publication: PublicationIdentity
    retrieved_at: str
    sha256: str
    media_type: str
    access_scope: AccessScope
    rights_status: RightsStatus
    source_url: str | None = None
    jurisdiction: str | None = None
    rights_note: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if not isinstance(self.ast_source, AstSourceIdentity):
            raise ValueError("ast_source must be an AstSourceIdentity")
        _require_text(self.title, "title")
        _require_text(self.issuing_body, "issuing_body")
        if not isinstance(self.evidence_role, EvidenceRole):
            raise ValueError("evidence_role must be an EvidenceRole")
        if not isinstance(self.publication, PublicationIdentity):
            raise ValueError("publication must be a PublicationIdentity")
        _require_timestamp(self.retrieved_at, "retrieved_at")
        if not isinstance(self.sha256, str) or _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("sha256 must be a lowercase SHA-256 digest")
        _require_text(self.media_type, "media_type")
        if not isinstance(self.access_scope, AccessScope):
            raise ValueError("access_scope must be an AccessScope")
        if not isinstance(self.rights_status, RightsStatus):
            raise ValueError("rights_status must be a RightsStatus")
        _require_optional_text(self.source_url, "source_url")
        _require_optional_text(self.jurisdiction, "jurisdiction")
        _require_optional_text(self.rights_note, "rights_note")

        restricted_access = self.access_scope is not AccessScope.PUBLIC
        restricted_rights = self.rights_status in {
            RightsStatus.LICENSED,
            RightsStatus.UNCERTAIN_RESTRICTED,
        }
        if (restricted_access or restricted_rights) and self.rights_note is None:
            raise ValueError("rights_note is required for restricted source material")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ast_source": self.ast_source.to_dict(),
            "title": self.title,
            "issuing_body": self.issuing_body,
            "evidence_role": self.evidence_role.value,
            "publication": self.publication.to_dict(),
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "access_scope": self.access_scope.value,
            "rights_status": self.rights_status.value,
            "source_url": self.source_url,
            "jurisdiction": self.jurisdiction,
            "rights_note": self.rights_note,
        }


@dataclass(frozen=True, slots=True)
class SourceRegister:
    entries: tuple[SourceRegisterEntry, ...]
    register_version: str = field(default=SOURCE_REGISTER_VERSION, init=False)

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("entries must not be empty")
        seen: set[str] = set()
        for entry in self.entries:
            if not isinstance(entry, SourceRegisterEntry):
                raise ValueError("entries must contain SourceRegisterEntry values")
            if entry.source_id in seen:
                raise ValueError(f"duplicate source_id: {entry.source_id}")
            seen.add(entry.source_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "register_version": self.register_version,
            "type": "source_register",
            "entries": [entry.to_dict() for entry in self.entries],
        }
