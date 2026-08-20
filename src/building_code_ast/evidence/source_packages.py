"""Canonical retained-source provenance.

Publications describe publication facts. Artifacts describe exact bytes. Bindings
state what an artifact evidences. Derivations record exact artifact lineage.
Private provider coordinates remain outside this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .model import AccessScope, AstSourceIdentity, EvidenceRole, RightsStatus

SOURCE_PACKAGE_VERSION = "0.2.0"
SOURCE_INDEX_VERSION = "0.2.0"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{prefix}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


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
        for name in ("printing", "digital_revision", "addenda_set", "correction_set", "published_on", "effective_on"):
            _optional_text(getattr(self, name), name)

    @property
    def publication_id(self) -> str:
        return _stable_id("publication", self.identity_dict())

    def identity_dict(self) -> dict[str, str | None]:
        return {"publication_family": self.publication_family, "edition": self.edition, "printing": self.printing, "digital_revision": self.digital_revision, "addenda_set": self.addenda_set, "correction_set": self.correction_set, "published_on": self.published_on, "effective_on": self.effective_on}

    def to_dict(self) -> dict[str, Any]:
        return {"publication_id": self.publication_id, **self.identity_dict()}


@dataclass(frozen=True, slots=True)
class PublicationAssurance:
    publication_identity: str = "unknown"
    publisher_equivalence: str = "unknown"
    correction_completeness: str = "unknown"
    addenda_completeness: str = "unknown"
    observations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("publication_identity", "publisher_equivalence", "correction_completeness", "addenda_completeness"):
            _text(getattr(self, name), name)
        if not isinstance(self.observations, tuple):
            raise ValueError("observations must be an immutable tuple")
        for observation in self.observations:
            _text(observation, "observation")

    def to_dict(self) -> dict[str, Any]:
        return {"publication_identity": self.publication_identity, "publisher_equivalence": self.publisher_equivalence, "correction_completeness": self.correction_completeness, "addenda_completeness": self.addenda_completeness, "observations": list(self.observations)}


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
        return {"artifact_id": self.artifact_id, "object_key": self.object_key, "sha256": self.sha256, "size": self.size, "media_type": self.media_type, "access_scope": self.access_scope.value if self.access_scope else None, "rights_status": self.rights_status.value if self.rights_status else None, "rights_note": self.rights_note}


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    artifact_id: str
    publication_id: str
    evidence_role: EvidenceRole
    source_id: str
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
        _text(self.source_id, "source_id")
        if not isinstance(self.ast_source, AstSourceIdentity):
            raise ValueError("ast_source must be an AstSourceIdentity")
        if not isinstance(self.assurance, PublicationAssurance):
            raise ValueError("assurance must be a PublicationAssurance")
        for name in ("title", "issuing_body", "retrieved_at", "source_url", "jurisdiction", "component_scope"):
            _optional_text(getattr(self, name), name)

    @property
    def binding_id(self) -> str:
        return _stable_id("binding", {"artifact_id": self.artifact_id, "publication_id": self.publication_id, "evidence_role": self.evidence_role.value, "source_id": self.source_id})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, "artifact_id": self.artifact_id, "publication_id": self.publication_id, "evidence_role": self.evidence_role.value, "source_id": self.source_id, "ast_source": self.ast_source.to_dict(), "assurance": self.assurance.to_dict(), "title": self.title, "issuing_body": self.issuing_body, "retrieved_at": self.retrieved_at, "source_url": self.source_url, "jurisdiction": self.jurisdiction, "component_scope": self.component_scope}


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
        return _stable_id("derivation", {"input_artifact_ids": self.input_artifact_ids, "output_artifact_id": self.output_artifact_id, "transformation": self.transformation, "recipe": self.recipe, "source_region": self.source_region, "verification": self.verification})

    def to_dict(self) -> dict[str, Any]:
        return {"derivation_id": self.derivation_id, "input_artifact_ids": list(self.input_artifact_ids), "output_artifact_id": self.output_artifact_id, "transformation": self.transformation, "recipe": self.recipe, "source_region": self.source_region, "verification": self.verification}


@dataclass(frozen=True, slots=True)
class SourcePackage:
    package_id: str
    publications: tuple[PublicationState, ...]
    artifacts: tuple[Artifact, ...]
    bindings: tuple[ArtifactBinding, ...]
    derivations: tuple[Derivation, ...] = ()
    package_version: str = field(default=SOURCE_PACKAGE_VERSION, init=False)

    def __post_init__(self) -> None:
        _text(self.package_id, "package_id")
        for name in ("publications", "artifacts", "bindings", "derivations"):
            if not isinstance(getattr(self, name), tuple):
                raise ValueError(f"{name} must be an immutable tuple")
        publication_ids = [item.publication_id for item in self.publications]
        artifact_ids = [item.artifact_id for item in self.artifacts]
        binding_ids = [item.binding_id for item in self.bindings]
        if len(publication_ids) != len(set(publication_ids)):
            raise ValueError("duplicate publication identity")
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("duplicate artifact identity")
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("duplicate binding identity")
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

    @property
    def version(self) -> str:
        return self.package_version

    def artifact(self, artifact_id: str) -> Artifact:
        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise KeyError(artifact_id)

    def binding_for_source(self, source_id: str) -> ArtifactBinding:
        matches = [item for item in self.bindings if item.source_id == source_id]
        if len(matches) != 1:
            raise KeyError(source_id)
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {"package_version": self.package_version, "type": "source_package", "package_id": self.package_id, "publications": [item.to_dict() for item in sorted(self.publications, key=lambda x: x.publication_id)], "artifacts": [item.to_dict() for item in sorted(self.artifacts, key=lambda x: x.artifact_id)], "bindings": [item.to_dict() for item in sorted(self.bindings, key=lambda x: x.binding_id)], "derivations": [item.to_dict() for item in sorted(self.derivations, key=lambda x: x.derivation_id)]}


def _enum_optional(enum_type: type[StrEnum], value: Any, label: str):
    if value is None:
        return None
    try:
        return enum_type(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} is unsupported") from exc


def source_package_from_dict(value: Mapping[str, Any]) -> SourcePackage:
    obj = _mapping(value, "source package")
    if obj.get("package_version") != SOURCE_PACKAGE_VERSION:
        raise ValueError(f"source package package_version must be {SOURCE_PACKAGE_VERSION}")
    if obj.get("type") != "source_package":
        raise ValueError("source package type must be 'source_package'")
    package_id = _text(obj.get("package_id"), "package_id")
    publications: list[PublicationState] = []
    for index, raw in enumerate(_array(obj.get("publications"), "publications")):
        item = _mapping(raw, f"publications[{index}]")
        publication = PublicationState(publication_family=item.get("publication_family"), edition=item.get("edition"), printing=item.get("printing"), digital_revision=item.get("digital_revision"), addenda_set=item.get("addenda_set"), correction_set=item.get("correction_set"), published_on=item.get("published_on"), effective_on=item.get("effective_on"))
        declared = item.get("publication_id")
        if declared is not None and declared != publication.publication_id:
            raise ValueError(f"publications[{index}].publication_id does not match identity")
        publications.append(publication)
    artifacts: list[Artifact] = []
    for index, raw in enumerate(_array(obj.get("artifacts"), "artifacts")):
        item = _mapping(raw, f"artifacts[{index}]")
        artifact = Artifact(object_key=item.get("object_key"), sha256=item.get("sha256"), size=item.get("size"), media_type=item.get("media_type"), access_scope=_enum_optional(AccessScope, item.get("access_scope"), f"artifacts[{index}].access_scope"), rights_status=_enum_optional(RightsStatus, item.get("rights_status"), f"artifacts[{index}].rights_status"), rights_note=item.get("rights_note"))
        declared = item.get("artifact_id")
        if declared is not None and declared != artifact.artifact_id:
            raise ValueError(f"artifacts[{index}].artifact_id does not match exact bytes")
        artifacts.append(artifact)
    bindings: list[ArtifactBinding] = []
    for index, raw in enumerate(_array(obj.get("bindings"), "bindings")):
        item = _mapping(raw, f"bindings[{index}]")
        ast = _mapping(item.get("ast_source"), f"bindings[{index}].ast_source")
        assurance_raw = _mapping(item.get("assurance"), f"bindings[{index}].assurance")
        binding = ArtifactBinding(artifact_id=item.get("artifact_id"), publication_id=item.get("publication_id"), evidence_role=EvidenceRole(item.get("evidence_role")), source_id=item.get("source_id"), ast_source=AstSourceIdentity(artifact_id=ast.get("artifact_id"), edition_id=ast.get("edition_id")), assurance=PublicationAssurance(publication_identity=assurance_raw.get("publication_identity", "unknown"), publisher_equivalence=assurance_raw.get("publisher_equivalence", "unknown"), correction_completeness=assurance_raw.get("correction_completeness", "unknown"), addenda_completeness=assurance_raw.get("addenda_completeness", "unknown"), observations=tuple(assurance_raw.get("observations", []))), title=item.get("title"), issuing_body=item.get("issuing_body"), retrieved_at=item.get("retrieved_at"), source_url=item.get("source_url"), jurisdiction=item.get("jurisdiction"), component_scope=item.get("component_scope"))
        declared = item.get("binding_id")
        if declared is not None and declared != binding.binding_id:
            raise ValueError(f"bindings[{index}].binding_id does not match binding identity")
        bindings.append(binding)
    derivations: list[Derivation] = []
    for index, raw in enumerate(_array(obj.get("derivations", []), "derivations")):
        item = _mapping(raw, f"derivations[{index}]")
        derivation = Derivation(input_artifact_ids=tuple(item.get("input_artifact_ids", [])), output_artifact_id=item.get("output_artifact_id"), transformation=item.get("transformation"), recipe=item.get("recipe"), source_region=item.get("source_region"), verification=item.get("verification"))
        declared = item.get("derivation_id")
        if declared is not None and declared != derivation.derivation_id:
            raise ValueError(f"derivations[{index}].derivation_id does not match lineage identity")
        derivations.append(derivation)
    return SourcePackage(package_id=package_id, publications=tuple(publications), artifacts=tuple(artifacts), bindings=tuple(bindings), derivations=tuple(derivations))


def load_source_package(path: str | Path) -> SourcePackage:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return source_package_from_dict(_mapping(value, "source package"))


def build_source_index(packages: Iterable[SourcePackage]) -> dict[str, Any]:
    package_list = sorted(tuple(packages), key=lambda item: item.package_id)
    ids = [item.package_id for item in package_list]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source package_id")
    return {"index_version": SOURCE_INDEX_VERSION, "type": "source_index", "packages": [{"package_id": package.package_id, "publication_ids": sorted(item.publication_id for item in package.publications), "artifact_ids": sorted(item.artifact_id for item in package.artifacts), "binding_ids": sorted(item.binding_id for item in package.bindings), "derivation_ids": sorted(item.derivation_id for item in package.derivations)} for package in package_list]}


class SourceReadiness(StrEnum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SourceAuditRecord:
    binding_id: str
    source_id: str
    publication_id: str
    artifact_id: str
    evidence_role: EvidenceRole
    artifact_bytes: SourceReadiness
    private_retrievability: SourceReadiness
    publication_identity: str
    publisher_equivalence: str
    correction_completeness: str
    addenda_completeness: str
    derivation_reproducibility: SourceReadiness
    normative_authority: SourceReadiness
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, "source_id": self.source_id, "publication_id": self.publication_id, "artifact_id": self.artifact_id, "evidence_role": self.evidence_role.value, "artifact_bytes": self.artifact_bytes.value, "private_retrievability": self.private_retrievability.value, "publication_identity": self.publication_identity, "publisher_equivalence": self.publisher_equivalence, "correction_completeness": self.correction_completeness, "addenda_completeness": self.addenda_completeness, "derivation_reproducibility": self.derivation_reproducibility.value, "normative_authority": self.normative_authority.value, "blockers": list(self.blockers)}


def source_audit(package: SourcePackage, *, retrievable_artifact_ids: Iterable[str] = ()) -> tuple[SourceAuditRecord, ...]:
    if not isinstance(package, SourcePackage):
        raise TypeError("package must be a SourcePackage")
    retrievable = set(retrievable_artifact_ids)
    derived_outputs = {item.output_artifact_id for item in package.derivations}
    derivation_by_output = {item.output_artifact_id: item for item in package.derivations}
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
        derivation_state = SourceReadiness.VERIFIED
        if binding.artifact_id in derived_outputs:
            derivation = derivation_by_output[binding.artifact_id]
            if any(item not in retrievable for item in derivation.input_artifact_ids):
                derivation_state = SourceReadiness.BLOCKED
                blockers.append("derivation input retrievability")
        normative = SourceReadiness.VERIFIED if binding.evidence_role is not EvidenceRole.NORMATIVE_TEXT or not blockers else SourceReadiness.BLOCKED
        rows.append(SourceAuditRecord(binding_id=binding.binding_id, source_id=binding.source_id, publication_id=binding.publication_id, artifact_id=binding.artifact_id, evidence_role=binding.evidence_role, artifact_bytes=SourceReadiness.VERIFIED, private_retrievability=SourceReadiness.VERIFIED if binding.artifact_id in retrievable else SourceReadiness.UNKNOWN, publication_identity=assurance.publication_identity, publisher_equivalence=assurance.publisher_equivalence, correction_completeness=assurance.correction_completeness, addenda_completeness=assurance.addenda_completeness, derivation_reproducibility=derivation_state, normative_authority=normative, blockers=tuple(blockers)))
    return tuple(sorted(rows, key=lambda item: item.binding_id))
