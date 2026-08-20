"""Verified hydration for exact artifacts independent of source IDs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Protocol

from .artifact_locators import ObjectProvider, PrivateArtifactLocator, PrivateArtifactLocatorRegistry
from .source_packages import Artifact

ARTIFACT_HYDRATION_RECEIPT_VERSION = "0.2.0"
_HASH_CHUNK_SIZE = 1024 * 1024


class ArtifactHydrationStatus(StrEnum):
    VERIFIED = "verified"


class ArtifactFetcher(Protocol):
    provider: ObjectProvider
    def fetch(self, locator: PrivateArtifactLocator, destination: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class ArtifactHydrationReceipt:
    artifact_id: str
    object_key: str
    sha256: str
    size: int
    media_type: str
    status: ArtifactHydrationStatus = ArtifactHydrationStatus.VERIFIED
    receipt_version: str = field(default=ARTIFACT_HYDRATION_RECEIPT_VERSION, init=False)

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "ArtifactHydrationReceipt":
        return cls(artifact_id=artifact.artifact_id, object_key=artifact.object_key, sha256=artifact.sha256, size=artifact.size, media_type=artifact.media_type)

    def to_dict(self) -> dict[str, Any]:
        return {"receipt_version": self.receipt_version, "type": "artifact_hydration_receipt", "status": self.status.value, "artifact_id": self.artifact_id, "object_key": self.object_key, "sha256": self.sha256, "size": self.size, "media_type": self.media_type}


def _verify_path(path: Path, artifact: Artifact) -> None:
    try:
        link_stat = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError("artifact file does not exist") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise ValueError("artifact path must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError("artifact file could not be opened safely") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("artifact path must be a regular file")
        if before.st_size != artifact.size:
            raise ValueError(f"artifact size mismatch: expected {artifact.size}, observed {before.st_size}")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, _HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(fd)
        before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if before_identity != after_identity:
            raise ValueError("artifact changed during verification")
    finally:
        os.close(fd)
    observed = digest.hexdigest()
    if observed != artifact.sha256:
        raise ValueError(f"artifact sha256 mismatch: expected {artifact.sha256}, observed {observed}")


def _validate_destination(destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError("hydration destination must not be a symlink")
    if destination.exists() and not destination.is_file():
        raise ValueError("hydration destination must be a regular file path")


def verify_local_artifact(artifact: Artifact, path: str | os.PathLike[str]) -> ArtifactHydrationReceipt:
    if not isinstance(artifact, Artifact):
        raise TypeError("artifact must be an Artifact")
    _verify_path(Path(path), artifact)
    return ArtifactHydrationReceipt.from_artifact(artifact)


def hydrate_artifact(artifact: Artifact, locator_registry: PrivateArtifactLocatorRegistry, *, destination: str | os.PathLike[str], fetcher: ArtifactFetcher) -> ArtifactHydrationReceipt:
    if not isinstance(artifact, Artifact):
        raise TypeError("artifact must be an Artifact")
    if not isinstance(locator_registry, PrivateArtifactLocatorRegistry):
        raise TypeError("locator_registry must be a PrivateArtifactLocatorRegistry")
    locator = locator_registry.resolve(artifact.object_key)
    if getattr(fetcher, "provider", None) != locator.provider:
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
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination_path.name}.", suffix=".partial", dir=parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        fetch(locator, temporary_path)
        _verify_path(temporary_path, artifact)
        _validate_destination(destination_path)
        os.replace(temporary_path, destination_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return ArtifactHydrationReceipt.from_artifact(artifact)
