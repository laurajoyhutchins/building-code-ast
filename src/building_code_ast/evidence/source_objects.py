"""Privacy-preserving source object location contracts.

Public source requirements bind logical object keys to exact registered source
identity. Private locator registries map those logical keys to provider object
IDs without making storage location part of source identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any

from .model import SourceRegister


SOURCE_OBJECT_CATALOG_VERSION = "0.1.0"
PRIVATE_SOURCE_OBJECT_LOCATOR_VERSION = "0.1.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJECT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class ObjectProvider(StrEnum):
    GOOGLE_DRIVE = "google_drive"


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _require_object_key(value: str, label: str) -> None:
    _require_text(value, label)
    if _OBJECT_KEY_RE.fullmatch(value) is None:
        raise ValueError(f"{label} contains unsupported characters")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{label} must be a normalized relative logical key")


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


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class SourceObjectRequirement:
    source_id: str
    object_key: str
    sha256: str
    size: int
    media_type: str

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_object_key(self.object_key, "object_key")
        _require_sha256(self.sha256, "sha256")
        _positive_int(self.size, "size")
        _require_text(self.media_type, "media_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size": self.size,
            "media_type": self.media_type,
        }


@dataclass(frozen=True, slots=True)
class SourceObjectCatalog:
    entries: tuple[SourceObjectRequirement, ...]
    catalog_version: str = field(default=SOURCE_OBJECT_CATALOG_VERSION, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise ValueError("entries must be an immutable tuple")
        if not self.entries:
            raise ValueError("entries must not be empty")
        source_ids: set[str] = set()
        object_keys: set[str] = set()
        for entry in self.entries:
            if not isinstance(entry, SourceObjectRequirement):
                raise ValueError("entries must contain SourceObjectRequirement values")
            if entry.source_id in source_ids:
                raise ValueError(f"duplicate source_id: {entry.source_id}")
            if entry.object_key in object_keys:
                raise ValueError(f"duplicate object_key: {entry.object_key}")
            source_ids.add(entry.source_id)
            object_keys.add(entry.object_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "type": "source_object_catalog",
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def requirement_for_source(self, source_id: str) -> SourceObjectRequirement:
        _require_text(source_id, "source_id")
        for entry in self.entries:
            if entry.source_id == source_id:
                return entry
        raise KeyError(source_id)


@dataclass(frozen=True, slots=True)
class PrivateSourceObjectLocator:
    object_key: str
    provider: ObjectProvider
    object_id: str
    path_hint: str | None = None

    def __post_init__(self) -> None:
        _require_object_key(self.object_key, "object_key")
        if not isinstance(self.provider, ObjectProvider):
            raise ValueError("provider must be an ObjectProvider")
        _require_text(self.object_id, "object_id")
        if self.path_hint is not None:
            _require_text(self.path_hint, "path_hint")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_key": self.object_key,
            "provider": self.provider.value,
            "object_id": self.object_id,
            "path_hint": self.path_hint,
        }


@dataclass(frozen=True, slots=True)
class PrivateSourceObjectLocatorRegistry:
    locators: tuple[PrivateSourceObjectLocator, ...]
    locator_version: str = field(
        default=PRIVATE_SOURCE_OBJECT_LOCATOR_VERSION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.locators, tuple):
            raise ValueError("locators must be an immutable tuple")
        if not self.locators:
            raise ValueError("locators must not be empty")
        keys: set[str] = set()
        provider_objects: set[tuple[ObjectProvider, str]] = set()
        for locator in self.locators:
            if not isinstance(locator, PrivateSourceObjectLocator):
                raise ValueError("locators must contain PrivateSourceObjectLocator values")
            if locator.object_key in keys:
                raise ValueError(f"duplicate object_key: {locator.object_key}")
            provider_object = (locator.provider, locator.object_id)
            if provider_object in provider_objects:
                raise ValueError("duplicate provider/object_id locator")
            keys.add(locator.object_key)
            provider_objects.add(provider_object)

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator_version": self.locator_version,
            "type": "private_source_object_locators",
            "locators": [locator.to_dict() for locator in self.locators],
        }

    def resolve(self, object_key: str) -> PrivateSourceObjectLocator:
        _require_object_key(object_key, "object_key")
        for locator in self.locators:
            if locator.object_key == object_key:
                return locator
        raise KeyError(object_key)


def validate_source_object_catalog(
    catalog: SourceObjectCatalog,
    source_register: SourceRegister,
) -> None:
    """Require public object requirements to agree with source authority."""

    if not isinstance(catalog, SourceObjectCatalog):
        raise TypeError("catalog must be a SourceObjectCatalog")
    if not isinstance(source_register, SourceRegister):
        raise TypeError("source_register must be a SourceRegister")
    registered = {entry.source_id: entry for entry in source_register.entries}
    for requirement in catalog.entries:
        source = registered.get(requirement.source_id)
        if source is None:
            raise ValueError(f"unregistered source_id: {requirement.source_id}")
        if requirement.sha256 != source.sha256:
            raise ValueError(f"sha256 mismatch for source_id: {requirement.source_id}")
        if requirement.media_type != source.media_type:
            raise ValueError(f"media_type mismatch for source_id: {requirement.source_id}")


def source_object_catalog_from_dict(value: Mapping[str, Any]) -> SourceObjectCatalog:
    obj = _object(value, "source object catalog")
    _exact_keys(obj, {"catalog_version", "type", "entries"}, "source object catalog")
    if obj["catalog_version"] != SOURCE_OBJECT_CATALOG_VERSION:
        raise ValueError(
            f"source object catalog catalog_version must be {SOURCE_OBJECT_CATALOG_VERSION}"
        )
    if obj["type"] != "source_object_catalog":
        raise ValueError("source object catalog type must be 'source_object_catalog'")
    entries_value = obj["entries"]
    if not isinstance(entries_value, list):
        raise ValueError("source object catalog entries must be an array")
    entries: list[SourceObjectRequirement] = []
    for index, raw_entry in enumerate(entries_value):
        label = f"entries[{index}]"
        entry = _object(raw_entry, label)
        _exact_keys(
            entry,
            {"source_id", "object_key", "sha256", "size", "media_type"},
            label,
        )
        entries.append(
            SourceObjectRequirement(
                source_id=_string(entry["source_id"], f"{label}.source_id"),
                object_key=_string(entry["object_key"], f"{label}.object_key"),
                sha256=_string(entry["sha256"], f"{label}.sha256"),
                size=_positive_int(entry["size"], f"{label}.size"),
                media_type=_string(entry["media_type"], f"{label}.media_type"),
            )
        )
    return SourceObjectCatalog(entries=tuple(entries))


def private_source_object_locator_registry_from_dict(
    value: Mapping[str, Any],
) -> PrivateSourceObjectLocatorRegistry:
    obj = _object(value, "private source object locator registry")
    _exact_keys(
        obj,
        {"locator_version", "type", "locators"},
        "private source object locator registry",
    )
    if obj["locator_version"] != PRIVATE_SOURCE_OBJECT_LOCATOR_VERSION:
        raise ValueError(
            "private source object locator registry locator_version must be "
            f"{PRIVATE_SOURCE_OBJECT_LOCATOR_VERSION}"
        )
    if obj["type"] != "private_source_object_locators":
        raise ValueError(
            "private source object locator registry type must be "
            "'private_source_object_locators'"
        )
    locators_value = obj["locators"]
    if not isinstance(locators_value, list):
        raise ValueError("private source object locators must be an array")
    locators: list[PrivateSourceObjectLocator] = []
    for index, raw_locator in enumerate(locators_value):
        label = f"locators[{index}]"
        locator = _object(raw_locator, label)
        _exact_keys(
            locator,
            {"object_key", "provider", "object_id", "path_hint"},
            label,
        )
        try:
            provider = ObjectProvider(_string(locator["provider"], f"{label}.provider"))
        except ValueError as exc:
            raise ValueError(f"{label}.provider is unsupported") from exc
        locators.append(
            PrivateSourceObjectLocator(
                object_key=_string(locator["object_key"], f"{label}.object_key"),
                provider=provider,
                object_id=_string(locator["object_id"], f"{label}.object_id"),
                path_hint=_optional_string(locator["path_hint"], f"{label}.path_hint"),
            )
        )
    return PrivateSourceObjectLocatorRegistry(locators=tuple(locators))
