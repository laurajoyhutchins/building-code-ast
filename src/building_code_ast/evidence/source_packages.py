"""Normalized retained-source provenance.

Publications describe publication facts. Artifacts describe exact bytes. Bindings
state what an artifact evidences. Derivations record exact artifact lineage.
Private provider coordinates remain outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Iterable

from .model import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
)
from .source_objects import SourceObjectCatalog

SOURCE_PACKAGE_VERSION = "0.2.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNRESOLVED_RE = re.compile(
    r"(?:^unresolved:|\bunresolved\b|\bunknown\b|\bnot[_ -]?established\b)",
    re.IGNORECASE,
)


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")
    return value


def _optional_text(value: str | None, label: str) -> str | None:
    if value is not None:
        _text(value, label)
    return value


def _digest(value: str, label: str = "sha256") -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _is_unresolved(value: str | None) -> bool:
    return value is not None and _UNRESOLVED_RE.search(value) is not None


@dataclass(frozen=True, slots=True)
class PublicationState:
    publication_family: str
    edition: str
    printing: str | None = None
    digital_revision: str | None = None
    addenda_set: str | None = None
    correction_set: str | None = None
    published_on: str | None = None
    effective_on: str | None = None

    def __post_init__(self) -> None:
        _text(self.publication_family, "publication_family")
        _text(self.edition, "edition")
        for name in (
            "printing", "digital_revision", "addenda_set", "correction_set",
            "published_on", "effective_on",
        ):
            _optional_text(getattr(self, name), name)

    @property
    def publication_id(self) -> str:
        return _stable_id("publication", self.identity_dict())

    def identity_dict(self) -> dict[str, str | None]:
        return {
            "publication_family": self.publication_family,
            "edition": self.edition,
            "printing": self.printing,
            "digital_revision": self.digital_revision,
            "addenda_set": self.addenda_set,
            "correction_set": self.correction_set,
            "published_on": self.published_on,
            "effective_on": self.effective_on,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"publication_id": self.publication_id, **self.identity_dict()}


@dataclass(frozen=True, slots=True)
class PublicationAssurance:
    publication_identity: str = "unknown"
    publisher_equivalence: str = "unknown"
    correction_completeness: str = "unknown"
    addenda_completeness: str = "unknown"
    legacy_observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "publication_identity", "publisher_equivalence",
            "correction_completeness", "addenda_completeness",
        ):
            _text(getattr(self, name), name)
        if not isinstance(self.legacy_observations, tuple):
            raise ValueError("legacy_observations must be an immutable tuple")
        for observation in self.legacy_observations:
            _text(observation, "legacy_observation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "publication_identity": self.publication_identity,
            "publisher_equivalence": self.publisher_equivalence,
            "correction_completeness": self.correction_completeness,
            "addenda_completeness": self.addenda_completeness,
            "legacy_observations": list(self.legacy_observations),
        }


@dataclass(frozen=True, slots=True)
class Artifact:
    object_key: str
    sha256: str
    size: int
    media_type: str
    access_scope: AccessScope | None = None
    rights_status: RightsStatus | None = None
    rights_note: str | None = None

    def __post_init__(self) -> None:
        _text(self.object_key, "object_key")
        _digest(self.sha256)
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size <= 0:
            raise ValueError("size must be a positive integer")
        _text(self.media_type, "media_type")
        if self.access_scope is not None and not isinstance(self.access_scope, AccessScope):
            raise ValueError("access_scope must be an AccessScope")
        if self.rights_status is not None and not isinstance(self.rights_status, RightsStatus):
            raise ValueError("rights_status must be a RightsStatus")
        _optional_text(self.rights_note, "rights_note")

    @property
    def artifact_id(self) -> str:
        return f"artifact:sha256:{self.sha256}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size": self.size,
            "media_type": self.media_type,
            "access_scope": self.access_scope.value if self.access_scope else None,
            "rights_status": self.rights_status.value if self.rights_status else None,
            "rights_note": self.rights_note,
        }


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    artifact_id: str
    publication_id: str
    evidence_role: EvidenceRole
    legacy_source_id: str
    ast_source: AstSourceIdentity
    assurance: PublicationAssurance = field(default_factory=PublicationAssurance)
    title: str | None = None
    issuing_body: str | None = None
    retrieved_at: str | None = None
    source_url: str | None = None
    jurisdiction: str | None = None
    component_scope: str | None = None

    def __post_init__(self) -> None:
        _text(self.artifact_id, "artifact_id")
        _text(self.publication_id, "publication_id")
        if not isinstance(self.evidence_role, EvidenceRole):
            raise ValueError("evidence_role must be an EvidenceRole")
        _text(self.legacy_source_id, "legacy_source_id")
        if not isinstance(self.ast_source, AstSourceIdentity):
            raise ValueError("ast_source must be an AstSourceIdentity")
        if not isinstance(self.assurance, PublicationAssurance):
            raise ValueError("assurance must be a PublicationAssurance")
        for name in ("title", "issuing_body", "retrieved_at", "source_url", "jurisdiction", "component_scope"):
            _optional_text(getattr(self, name), name)

    @property
    def binding_id(self) -> str:
        return _stable_id("binding", {
            "artifact_id": self.artifact_id,
            "publication_id": self.publication_id,
            "evidence_role": self.evidence_role.value,
            "legacy_source_id": self.legacy_source_id,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "artifact_id": self.artifact_id,
            "publication_id": self.publication_id,
            "evidence_role": self.evidence_role.value,
            "legacy_source_id": self.legacy_source_id,
            "ast_source": self.ast_source.to_dict(),
            "assurance": self.assurance.to_dict(),
            "title": self.title,
            "issuing_body": self.issuing_body,
            "retrieved_at": self.retrieved_at,
            "source_url": self.source_url,
            "jurisdiction": self.jurisdiction,
            "component_scope": self.component_scope,
        }


@dataclass(frozen=True, slots=True)
class Derivation:
    input_artifact_ids: tuple[str, ...]
    output_artifact_id: str
    transformation: str
    recipe: str
    source_region: str | None = None
    verification: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.input_artifact_ids, tuple) or not self.input_artifact_ids:
            raise ValueError("input_artifact_ids must be a non-empty immutable tuple")
        for artifact_id in self.input_artifact_ids:
            _text(artifact_id, "input_artifact_id")
        _text(self.output_artifact_id, "output_artifact_id")
        _text(self.transformation, "transformation")
        _text(self.recipe, "recipe")
        _optional_text(self.source_region, "source_region")
        _optional_text(self.verification, "verification")

    @property
    def derivation_id(self) -> str:
        return _stable_id("derivation", {
            "input_artifact_ids": self.input_artifact_ids,
            "output_artifact_id": self.output_artifact_id,
            "transformation": self.transformation,
            "recipe": self.recipe,
            "source_region": self.source_region,
            "verification": self.verification,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "derivation_id": self.derivation_id,
            "input_artifact_ids": list(self.input_artifact_ids),
            "output_artifact_id": self.output_artifact_id,
            "transformation": self.transformation,
            "recipe": self.recipe,
            "source_region": self.source_region,
            "verification": self.verification,
        }


@dataclass(frozen=True, slots=True)
class SourcePackage:
    publications: tuple[PublicationState, ...]
    artifacts: tuple[Artifact, ...]
    bindings: tuple[ArtifactBinding, ...]
    derivations: tuple[Derivation, ...] = ()
    package_version: str = field(default=SOURCE_PACKAGE_VERSION, init=False)

    def __post_init__(self) -> None:
        for name in ("publications", "artifacts", "bindings", "derivations"):
            if not isinstance(getattr(self, name), tuple):
                raise ValueError(f"{name} must be an immutable tuple")
        publication_ids = [item.publication_id for item in self.publications]
        artifact_ids = [item.artifact_id for item in self.artifacts]
        if len(publication_ids) != len(set(publication_ids)):
            raise ValueError("duplicate publication identity")
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("duplicate artifact identity")
        publications = set(publication_ids)
        artifacts = set(artifact_ids)
        for binding in self.bindings:
            if binding.publication_id not in publications:
                raise ValueError(f"unknown binding publication_id: {binding.publication_id}")
            if binding.artifact_id not in artifacts:
                raise ValueError(f"unknown binding artifact_id: {binding.artifact_id}")
        for derivation in self.derivations:
            if derivation.output_artifact_id not in artifacts:
                raise ValueError(f"unknown derivation output: {derivation.output_artifact_id}")
            for input_id in derivation.input_artifact_ids:
                if input_id not in artifacts:
                    raise ValueError(f"unknown derivation input: {input_id}")
            if derivation.output_artifact_id in derivation.input_artifact_ids:
                raise ValueError("self-derivation is not allowed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_version": self.package_version,
            "type": "source_package",
            "publications": [item.to_dict() for item in self.publications],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "bindings": [item.to_dict() for item in self.bindings],
            "derivations": [item.to_dict() for item in self.derivations],
        }


def _publication_from_legacy(publication: PublicationIdentity) -> tuple[PublicationState, PublicationAssurance]:
    observations: list[str] = []
    correction_set = publication.correction_set
    addenda_set = publication.addenda_set
    correction_completeness = "declared" if correction_set else "unknown"
    addenda_completeness = "declared" if addenda_set else "unknown"
    if _is_unresolved(correction_set):
        observations.append(correction_set or "")
        correction_set = None
        correction_completeness = "unknown"
    if _is_unresolved(addenda_set):
        observations.append(addenda_set or "")
        addenda_set = None
        addenda_completeness = "unknown"
    return PublicationState(
        publication_family=publication.publication_family,
        edition=publication.edition,
        printing=publication.printing,
        digital_revision=publication.digital_revision,
        addenda_set=addenda_set,
        correction_set=correction_set,
        published_on=publication.published_on,
        effective_on=publication.effective_on,
    ), PublicationAssurance(
        publication_identity="legacy_registered",
        publisher_equivalence="unknown",
        correction_completeness=correction_completeness,
        addenda_completeness=addenda_completeness,
        legacy_observations=tuple(observations),
    )


def legacy_source_package(register: SourceRegister, catalog: SourceObjectCatalog) -> SourcePackage:
    """Deterministically normalize v0.1 register/catalog authority."""
    if not isinstance(register, SourceRegister):
        raise TypeError("register must be a SourceRegister")
    if not isinstance(catalog, SourceObjectCatalog):
        raise TypeError("catalog must be a SourceObjectCatalog")
    publications: dict[str, PublicationState] = {}
    artifacts: dict[str, Artifact] = {}
    bindings: list[ArtifactBinding] = []
    for entry in register.entries:
        try:
            requirement = catalog.requirement_for_source(entry.source_id)
        except KeyError as exc:
            raise ValueError(f"missing source object for source_id: {entry.source_id}") from exc
        if requirement.sha256 != entry.sha256:
            raise ValueError(f"sha256 mismatch for source_id: {entry.source_id}")
        if requirement.media_type != entry.media_type:
            raise ValueError(f"media_type mismatch for source_id: {entry.source_id}")
        publication, assurance = _publication_from_legacy(entry.publication)
        publications.setdefault(publication.publication_id, publication)
        artifact = Artifact(
            object_key=requirement.object_key,
            sha256=requirement.sha256,
            size=requirement.size,
            media_type=requirement.media_type,
            access_scope=entry.access_scope,
            rights_status=entry.rights_status,
            rights_note=entry.rights_note,
        )
        prior = artifacts.get(artifact.artifact_id)
        if prior is not None and (
            prior.object_key != artifact.object_key
            or prior.size != artifact.size
            or prior.media_type != artifact.media_type
        ):
            raise ValueError(f"conflicting exact artifact identity: {artifact.artifact_id}")
        artifacts.setdefault(artifact.artifact_id, artifact)
        bindings.append(ArtifactBinding(
            artifact_id=artifact.artifact_id,
            publication_id=publication.publication_id,
            evidence_role=entry.evidence_role,
            legacy_source_id=entry.source_id,
            ast_source=entry.ast_source,
            assurance=assurance,
            title=entry.title,
            issuing_body=entry.issuing_body,
            retrieved_at=entry.retrieved_at,
            source_url=entry.source_url,
            jurisdiction=entry.jurisdiction,
        ))
    return SourcePackage(
        publications=tuple(sorted(publications.values(), key=lambda item: item.publication_id)),
        artifacts=tuple(sorted(artifacts.values(), key=lambda item: item.artifact_id)),
        bindings=tuple(sorted(bindings, key=lambda item: item.binding_id)),
    )


class SourceReadiness(StrEnum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SourceAuditRecord:
    binding_id: str
    legacy_source_id: str
    publication_id: str
    artifact_id: str
    evidence_role: EvidenceRole
    artifact_bytes: SourceReadiness
    private_retrievability: SourceReadiness
    publication_identity: str
    publisher_equivalence: str
    correction_completeness: str
    addenda_completeness: str
    normative_authority: SourceReadiness
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "legacy_source_id": self.legacy_source_id,
            "publication_id": self.publication_id,
            "artifact_id": self.artifact_id,
            "evidence_role": self.evidence_role.value,
            "artifact_bytes": self.artifact_bytes.value,
            "private_retrievability": self.private_retrievability.value,
            "publication_identity": self.publication_identity,
            "publisher_equivalence": self.publisher_equivalence,
            "correction_completeness": self.correction_completeness,
            "addenda_completeness": self.addenda_completeness,
            "normative_authority": self.normative_authority.value,
            "blockers": list(self.blockers),
        }


def source_audit(package: SourcePackage, *, retrievable_artifact_ids: Iterable[str] = ()) -> tuple[SourceAuditRecord, ...]:
    """Compute source readiness without introducing mutable status authority."""
    if not isinstance(package, SourcePackage):
        raise TypeError("package must be a SourcePackage")
    retrievable = set(retrievable_artifact_ids)
    rows: list[SourceAuditRecord] = []
    for binding in package.bindings:
        assurance = binding.assurance
        blockers: list[str] = []
        if assurance.publisher_equivalence not in {"verified", "publisher_supplied", "official"}:
            blockers.append("publisher equivalence")
        if assurance.correction_completeness not in {"verified", "declared", "not_applicable"}:
            blockers.append("correction completeness")
        if assurance.addenda_completeness not in {"verified", "declared", "not_applicable"}:
            blockers.append("addenda completeness")
        if binding.artifact_id not in retrievable:
            blockers.append("private retrievability")
        normative = SourceReadiness.VERIFIED if (
            binding.evidence_role is not EvidenceRole.NORMATIVE_TEXT or not blockers
        ) else SourceReadiness.BLOCKED
        rows.append(SourceAuditRecord(
            binding_id=binding.binding_id,
            legacy_source_id=binding.legacy_source_id,
            publication_id=binding.publication_id,
            artifact_id=binding.artifact_id,
            evidence_role=binding.evidence_role,
            artifact_bytes=SourceReadiness.VERIFIED,
            private_retrievability=(
                SourceReadiness.VERIFIED if binding.artifact_id in retrievable else SourceReadiness.UNKNOWN
            ),
            publication_identity=assurance.publication_identity,
            publisher_equivalence=assurance.publisher_equivalence,
            correction_completeness=assurance.correction_completeness,
            addenda_completeness=assurance.addenda_completeness,
            normative_authority=normative,
            blockers=tuple(blockers),
        ))
    return tuple(sorted(rows, key=lambda item: item.binding_id))
