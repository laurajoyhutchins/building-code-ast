"""Strict JSON-compatible input handling for source registers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .model import (
    SOURCE_REGISTER_VERSION,
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    publication_state_id,
)


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")


def _keys_with_optional(
    value: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required - optional
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _enum(enum_type, value: Any, label: str):
    try:
        return enum_type(_string(value, label))
    except ValueError as exc:
        raise ValueError(f"{label} is unsupported") from exc


def _ast_source(value: Any, label: str) -> AstSourceIdentity:
    obj = _object(value, label)
    _exact_keys(obj, {"artifact_id", "edition_id"}, label)
    return AstSourceIdentity(
        artifact_id=_string(obj["artifact_id"], f"{label}.artifact_id"),
        edition_id=_string(obj["edition_id"], f"{label}.edition_id"),
    )


def _publication(value: Any, label: str) -> PublicationIdentity:
    obj = _object(value, label)
    _keys_with_optional(
        obj,
        {
            "state_id",
            "publication_family",
            "edition",
            "printing",
            "digital_revision",
            "correction_set",
            "published_on",
            "effective_on",
        },
        {"addenda_set"},
        label,
    )
    publication = PublicationIdentity(
        publication_family=_string(
            obj["publication_family"], f"{label}.publication_family"
        ),
        edition=_string(obj["edition"], f"{label}.edition"),
        printing=_optional_string(obj["printing"], f"{label}.printing"),
        digital_revision=_optional_string(
            obj["digital_revision"], f"{label}.digital_revision"
        ),
        addenda_set=_optional_string(obj.get("addenda_set"), f"{label}.addenda_set"),
        correction_set=_optional_string(
            obj["correction_set"], f"{label}.correction_set"
        ),
        published_on=_optional_string(obj["published_on"], f"{label}.published_on"),
        effective_on=_optional_string(obj["effective_on"], f"{label}.effective_on"),
    )
    supplied_state_id = _string(obj["state_id"], f"{label}.state_id")
    expected_state_id = publication_state_id(publication)
    if supplied_state_id != expected_state_id:
        raise ValueError(f"{label}.state_id does not match deterministic identity")
    return publication


def _entry(value: Any, index: int) -> SourceRegisterEntry:
    label = f"entries[{index}]"
    obj = _object(value, label)
    _exact_keys(
        obj,
        {
            "source_id",
            "ast_source",
            "title",
            "issuing_body",
            "evidence_role",
            "publication",
            "retrieved_at",
            "sha256",
            "media_type",
            "access_scope",
            "rights_status",
            "source_url",
            "jurisdiction",
            "rights_note",
        },
        label,
    )
    return SourceRegisterEntry(
        source_id=_string(obj["source_id"], f"{label}.source_id"),
        ast_source=_ast_source(obj["ast_source"], f"{label}.ast_source"),
        title=_string(obj["title"], f"{label}.title"),
        issuing_body=_string(obj["issuing_body"], f"{label}.issuing_body"),
        evidence_role=_enum(
            EvidenceRole, obj["evidence_role"], f"{label}.evidence_role"
        ),
        publication=_publication(obj["publication"], f"{label}.publication"),
        retrieved_at=_string(obj["retrieved_at"], f"{label}.retrieved_at"),
        sha256=_string(obj["sha256"], f"{label}.sha256"),
        media_type=_string(obj["media_type"], f"{label}.media_type"),
        access_scope=_enum(
            AccessScope, obj["access_scope"], f"{label}.access_scope"
        ),
        rights_status=_enum(
            RightsStatus, obj["rights_status"], f"{label}.rights_status"
        ),
        source_url=_optional_string(obj["source_url"], f"{label}.source_url"),
        jurisdiction=_optional_string(
            obj["jurisdiction"], f"{label}.jurisdiction"
        ),
        rights_note=_optional_string(obj["rights_note"], f"{label}.rights_note"),
    )


def source_register_from_dict(value: Mapping[str, Any]) -> SourceRegister:
    """Read and validate a JSON-compatible source register mapping."""

    obj = _object(value, "source register")
    _exact_keys(obj, {"register_version", "type", "entries"}, "source register")
    if obj["register_version"] != SOURCE_REGISTER_VERSION:
        raise ValueError(
            f"source register register_version must be {SOURCE_REGISTER_VERSION}"
        )
    if obj["type"] != "source_register":
        raise ValueError("source register type must be 'source_register'")
    entries_value = obj["entries"]
    if not isinstance(entries_value, list):
        raise ValueError("source register entries must be an array")
    return SourceRegister(
        entries=tuple(_entry(entry, index) for index, entry in enumerate(entries_value))
    )
