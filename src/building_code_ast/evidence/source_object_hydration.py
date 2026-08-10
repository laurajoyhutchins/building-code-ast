"""Verified local hydration for privately located source objects.

The compiler core does not authenticate to storage providers. Callers supply a
provider-specific fetcher; this module validates public source requirements,
verifies fetched bytes, and atomically places only exact artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Protocol

from .model import SourceRegister
from .source_objects import (
    ObjectProvider,
    PrivateSourceObjectLocator,
    PrivateSourceObjectLocatorRegistry,
    SourceObjectCatalog,
    SourceObjectRequirement,
)


SOURCE_OBJECT_HYDRATION_RECEIPT_VERSION = "0.1.0"
_HASH_CHUNK_SIZE = 1024 * 1024


class HydrationStatus(StrEnum):
    VERIFIED = "verified"


class SourceObjectFetcher(Protocol):
    """Caller-owned provider adapter.

    Authentication and provider SDK behavior live behind this interface. The
    core receives only a private locator and a local temporary destination.
    """

    provider: ObjectProvider

    def fetch(self, locator: PrivateSourceObjectLocator, destination: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class SourceObjectHydrationReceipt:
    source_id: str
    object_key: str
    sha256: str
    size: int
    media_type: str
    status: HydrationStatus = HydrationStatus.VERIFIED
    receipt_version: str = field(
        default=SOURCE_OBJECT_HYDRATION_RECEIPT_VERSION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.status, HydrationStatus):
            raise ValueError("status must be a HydrationStatus")
        requirement = SourceObjectRequirement(
            source_id=self.source_id,
            object_key=self.object_key,
            sha256=self.sha256,
            size=self.size,
            media_type=self.media_type,
        )
        if requirement.source_id != self.source_id:
            raise AssertionError("unreachable source requirement normalization")

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_version": self.receipt_version,
            "type": "source_object_hydration_receipt",
            "status": self.status.value,
            "source_id": self.source_id,
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size": self.size,
            "media_type": self.media_type,
        }


def validate_source_object_requirement(
    requirement: SourceObjectRequirement,
    source_register: SourceRegister,
) -> None:
    """Validate one selected requirement against its authoritative register.

    Source registers are publication-scoped while the public object catalog can
    span publications, so hydration validates the selected source rather than
    requiring callers to manufacture a cross-publication union register.
    """

    if not isinstance(requirement, SourceObjectRequirement):
        raise TypeError("requirement must be a SourceObjectRequirement")
    if not isinstance(source_register, SourceRegister):
        raise TypeError("source_register must be a SourceRegister")

    source = next(
        (entry for entry in source_register.entries if entry.source_id == requirement.source_id),
        None,
    )
    if source is None:
        raise ValueError(f"unregistered source_id: {requirement.source_id}")
    if requirement.sha256 != source.sha256:
        raise ValueError(f"sha256 mismatch for source_id: {requirement.source_id}")
    if requirement.media_type != source.media_type:
        raise ValueError(f"media_type mismatch for source_id: {requirement.source_id}")


def _receipt(requirement: SourceObjectRequirement) -> SourceObjectHydrationReceipt:
    return SourceObjectHydrationReceipt(
        source_id=requirement.source_id,
        object_key=requirement.object_key,
        sha256=requirement.sha256,
        size=requirement.size,
        media_type=requirement.media_type,
    )


def _verified_digest(path: Path, requirement: SourceObjectRequirement) -> str:
    try:
        link_stat = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError("source object file does not exist") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise ValueError("source object path must not be a symlink")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("source object file could not be opened safely") from exc

    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("source object path must be a regular file")
        if before.st_size != requirement.size:
            raise ValueError(
                f"source object size mismatch: expected {requirement.size}, observed {before.st_size}"
            )

        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, _HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

        after = os.fstat(fd)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity:
            raise ValueError("source object changed during verification")
    finally:
        os.close(fd)

    observed = digest.hexdigest()
    if observed != requirement.sha256:
        raise ValueError(
            f"source object sha256 mismatch: expected {requirement.sha256}, observed {observed}"
        )
    return observed


def _validate_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError("hydration destination must not be a symlink")
    if destination.exists() and not destination.is_file():
        raise ValueError("hydration destination must be a regular file path")


def verify_local_source_object(
    catalog: SourceObjectCatalog,
    source_register: SourceRegister,
    *,
    source_id: str,
    path: str | os.PathLike[str],
) -> SourceObjectHydrationReceipt:
    """Verify an already-local object against public and authoritative identity."""

    if not isinstance(catalog, SourceObjectCatalog):
        raise TypeError("catalog must be a SourceObjectCatalog")
    requirement = catalog.requirement_for_source(source_id)
    validate_source_object_requirement(requirement, source_register)
    _verified_digest(Path(path), requirement)
    return _receipt(requirement)


def hydrate_source_object(
    catalog: SourceObjectCatalog,
    source_register: SourceRegister,
    locator_registry: PrivateSourceObjectLocatorRegistry,
    *,
    source_id: str,
    destination: str | os.PathLike[str],
    fetcher: SourceObjectFetcher,
) -> SourceObjectHydrationReceipt:
    """Fetch, verify, and atomically place one private source object.

    The selected public requirement is checked against source authority before
    private resolution or provider work. Existing destination bytes survive any
    fetch or verification failure.
    """

    if not isinstance(catalog, SourceObjectCatalog):
        raise TypeError("catalog must be a SourceObjectCatalog")
    if not isinstance(locator_registry, PrivateSourceObjectLocatorRegistry):
        raise TypeError("locator_registry must be a PrivateSourceObjectLocatorRegistry")

    requirement = catalog.requirement_for_source(source_id)
    validate_source_object_requirement(requirement, source_register)
    locator = locator_registry.resolve(requirement.object_key)

    provider = getattr(fetcher, "provider", None)
    if provider != locator.provider:
        raise ValueError("fetcher provider does not match private locator provider")
    fetch = getattr(fetcher, "fetch", None)
    if not callable(fetch):
        raise TypeError("fetcher must provide a callable fetch method")

    destination_path = Path(destination)
    _validate_destination(destination_path)
    parent = destination_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        raise ValueError("hydration destination parent must not be a symlink")

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.",
        suffix=".partial",
        dir=parent,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)

    try:
        fetch(locator, temporary_path)
        _verified_digest(temporary_path, requirement)
        _validate_destination(destination_path)
        os.replace(temporary_path, destination_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return _receipt(requirement)
