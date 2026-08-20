"""Private artifact locator contracts.

Provider object IDs are custody coordinates only. They never establish artifact
identity, publication identity, or evidentiary authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any

PRIVATE_ARTIFACT_LOCATOR_VERSION = "0.2.0"
_OBJECT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class ObjectProvider(StrEnum):
    GOOGLE_DRIVE = "google_drive"


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_object_key(value: str, label: str) -> None:
    _require_text(value, label)
    if _OBJECT_KEY_RE.fullmatch(value) is None:
        raise ValueError(f"{label} contains unsupported characters")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{label} must be a normalized relative logical key")


@dataclass(frozen=True, slots=True)
class PrivateArtifactLocator:
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
        return {"object_key": self.object_key, "provider": self.provider.value, "object_id": self.object_id, "path_hint": self.path_hint}


@dataclass(frozen=True, slots=True)
class PrivateArtifactLocatorRegistry:
    locators: tuple[PrivateArtifactLocator, ...]
    locator_version: str = field(default=PRIVATE_ARTIFACT_LOCATOR_VERSION, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.locators, tuple) or not self.locators:
            raise ValueError("locators must be a non-empty immutable tuple")
        keys: set[str] = set()
        provider_objects: set[tuple[ObjectProvider, str]] = set()
        for locator in self.locators:
            if not isinstance(locator, PrivateArtifactLocator):
                raise ValueError("locators must contain PrivateArtifactLocator values")
            if locator.object_key in keys:
                raise ValueError(f"duplicate object_key: {locator.object_key}")
            provider_object = (locator.provider, locator.object_id)
            if provider_object in provider_objects:
                raise ValueError("duplicate provider/object_id locator")
            keys.add(locator.object_key)
            provider_objects.add(provider_object)

    def resolve(self, object_key: str) -> PrivateArtifactLocator:
        _require_object_key(object_key, "object_key")
        for locator in self.locators:
            if locator.object_key == object_key:
                return locator
        raise KeyError(object_key)

    def to_dict(self) -> dict[str, Any]:
        return {"locator_version": self.locator_version, "type": "private_artifact_locators", "locators": [item.to_dict() for item in self.locators]}


def private_artifact_locator_registry_from_dict(value: Mapping[str, Any]) -> PrivateArtifactLocatorRegistry:
    if not isinstance(value, Mapping):
        raise ValueError("private artifact locator registry must be an object")
    if value.get("locator_version") != PRIVATE_ARTIFACT_LOCATOR_VERSION:
        raise ValueError(f"private artifact locator registry locator_version must be {PRIVATE_ARTIFACT_LOCATOR_VERSION}")
    if value.get("type") != "private_artifact_locators":
        raise ValueError("private artifact locator registry type must be 'private_artifact_locators'")
    raw_locators = value.get("locators")
    if not isinstance(raw_locators, list):
        raise ValueError("private artifact locators must be an array")
    locators: list[PrivateArtifactLocator] = []
    for index, raw in enumerate(raw_locators):
        if not isinstance(raw, Mapping):
            raise ValueError(f"locators[{index}] must be an object")
        try:
            provider = ObjectProvider(raw.get("provider"))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"locators[{index}].provider is unsupported") from exc
        locators.append(PrivateArtifactLocator(object_key=raw.get("object_key"), provider=provider, object_id=raw.get("object_id"), path_hint=raw.get("path_hint")))
    return PrivateArtifactLocatorRegistry(locators=tuple(locators))
