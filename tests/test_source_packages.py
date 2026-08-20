from __future__ import annotations

import pytest

from building_code_ast.evidence.model import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
)
from building_code_ast.evidence.source_objects import SourceObjectCatalog, SourceObjectRequirement
from building_code_ast.evidence.source_packages import (
    Artifact,
    ArtifactBinding,
    Derivation,
    PublicationAssurance,
    PublicationState,
    SourcePackage,
    SourceReadiness,
    legacy_source_package,
    source_audit,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def _entry(source_id: str, *, role: EvidenceRole, correction_set: str | None = None) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id=source_id,
        ast_source=AstSourceIdentity(artifact_id=source_id, edition_id=f"{source_id}:edition"),
        title=source_id,
        issuing_body="Example Standards Body",
        evidence_role=role,
        publication=PublicationIdentity(
            publication_family="EXAMPLE",
            edition="2026",
            correction_set=correction_set,
        ),
        retrieved_at="2026-08-20T00:00:00+00:00",
        sha256=SHA_A,
        media_type="application/pdf",
        access_scope=AccessScope.LICENSED_LOCAL,
        rights_status=RightsStatus.LICENSED,
        rights_note="Licensed test fixture.",
    )


def _catalog(*source_ids: str) -> SourceObjectCatalog:
    return SourceObjectCatalog(entries=tuple(
        SourceObjectRequirement(
            source_id=source_id,
            object_key="engineering-sources/example/source.pdf",
            sha256=SHA_A,
            size=123,
            media_type="application/pdf",
        )
        for source_id in source_ids
    ))


def test_legacy_conversion_collapses_physical_artifact_and_preserves_bindings() -> None:
    register = SourceRegister(entries=(
        _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT),
        _entry("example:commentary", role=EvidenceRole.COMMENTARY),
    ))

    package = legacy_source_package(register, _catalog("example:normative", "example:commentary"))

    assert len(package.artifacts) == 1
    assert len(package.bindings) == 2
    artifact = package.artifacts[0]
    assert {binding.artifact_id for binding in package.bindings} == {artifact.artifact_id}
    assert {binding.legacy_source_id for binding in package.bindings} == {
        "example:normative", "example:commentary"
    }
    assert {binding.evidence_role for binding in package.bindings} == {
        EvidenceRole.NORMATIVE_TEXT, EvidenceRole.COMMENTARY
    }


def test_unresolved_correction_text_becomes_assurance_not_identity() -> None:
    unresolved = "unresolved:retained-artifact-correction-and-addenda-state"
    register = SourceRegister(entries=(
        _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT, correction_set=unresolved),
    ))

    package = legacy_source_package(register, _catalog("example:normative"))

    assert package.publications[0].correction_set is None
    assert package.bindings[0].assurance.correction_completeness == "unknown"
    assert package.bindings[0].assurance.legacy_observations == (unresolved,)


def test_known_correction_state_remains_publication_identity() -> None:
    register = SourceRegister(entries=(
        _entry(
            "example:normative",
            role=EvidenceRole.NORMATIVE_TEXT,
            correction_set="errata-through-2026-07-01",
        ),
    ))

    package = legacy_source_package(register, _catalog("example:normative"))
    assert package.publications[0].correction_set == "errata-through-2026-07-01"


def test_conflicting_physical_identity_fails_closed() -> None:
    register = SourceRegister(entries=(
        _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT),
    ))
    catalog = SourceObjectCatalog(entries=(SourceObjectRequirement(
        source_id="example:normative",
        object_key="engineering-sources/example/source.pdf",
        sha256=SHA_B,
        size=123,
        media_type="application/pdf",
    ),))

    with pytest.raises(ValueError, match="sha256 mismatch"):
        legacy_source_package(register, catalog)


def test_derivation_is_exact_and_cannot_self_derive() -> None:
    publication = PublicationState(publication_family="EXAMPLE", edition="2026")
    source = Artifact(
        object_key="engineering-sources/example/source.pdf",
        sha256=SHA_A,
        size=123,
        media_type="application/pdf",
    )
    derived = Artifact(
        object_key="engineering-sources/example/derivatives/component.pdf",
        sha256=SHA_B,
        size=45,
        media_type="application/pdf",
    )
    binding = ArtifactBinding(
        artifact_id=source.artifact_id,
        publication_id=publication.publication_id,
        evidence_role=EvidenceRole.NORMATIVE_TEXT,
        legacy_source_id="example:normative",
        ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-2026"),
        assurance=PublicationAssurance(),
    )
    derivation = Derivation(
        input_artifact_ids=(source.artifact_id,),
        output_artifact_id=derived.artifact_id,
        transformation="page_range_extract",
        recipe="pages:10-20",
    )

    assert SourcePackage(
        publications=(publication,), artifacts=(source, derived), bindings=(binding,), derivations=(derivation,)
    ).derivations == (derivation,)

    with pytest.raises(ValueError, match="self-derivation"):
        SourcePackage(
            publications=(publication,),
            artifacts=(source,),
            bindings=(binding,),
            derivations=(Derivation(
                input_artifact_ids=(source.artifact_id,),
                output_artifact_id=source.artifact_id,
                transformation="ocr",
                recipe="fixture",
            ),),
        )


def test_source_audit_is_computed_and_blocks_unverified_authority() -> None:
    publication = PublicationState(publication_family="EXAMPLE", edition="2026")
    artifact = Artifact(
        object_key="engineering-sources/example/source.pdf", sha256=SHA_A, size=123, media_type="application/pdf"
    )
    binding = ArtifactBinding(
        artifact_id=artifact.artifact_id,
        publication_id=publication.publication_id,
        evidence_role=EvidenceRole.NORMATIVE_TEXT,
        legacy_source_id="example:normative",
        ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-2026"),
        assurance=PublicationAssurance(
            publication_identity="artifact_self_identified",
            publisher_equivalence="unverified",
            correction_completeness="unknown",
        ),
    )
    package = SourcePackage(publications=(publication,), artifacts=(artifact,), bindings=(binding,))

    audit = source_audit(package, retrievable_artifact_ids={artifact.artifact_id})

    assert audit[0].artifact_bytes == SourceReadiness.VERIFIED
    assert audit[0].private_retrievability == SourceReadiness.VERIFIED
    assert audit[0].normative_authority == SourceReadiness.BLOCKED
    assert "publisher equivalence" in audit[0].blockers
    assert "correction completeness" in audit[0].blockers
