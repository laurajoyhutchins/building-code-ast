from __future__ import annotations

from building_code_ast.evidence import (
    AccessScope,
    Artifact,
    ArtifactBinding,
    AstSourceIdentity,
    BoundArtifact,
    EvidenceRole,
    PublicationAssurance,
    PublicationState,
    RightsStatus,
)


def bound_source(
    *,
    source_id: str,
    ast_source: AstSourceIdentity,
    title: str,
    issuing_body: str,
    evidence_role: EvidenceRole,
    publication: PublicationState,
    retrieved_at: str,
    sha256: str,
    media_type: str,
    access_scope: AccessScope,
    rights_status: RightsStatus,
    source_url: str | None = None,
    jurisdiction: str | None = None,
    rights_note: str | None = None,
) -> BoundArtifact:
    artifact = Artifact(
        object_key=f"tests/{sha256}",
        sha256=sha256,
        size=1,
        media_type=media_type,
        access_scope=access_scope,
        rights_status=rights_status,
        rights_note=rights_note,
    )
    binding = ArtifactBinding(
        artifact_id=artifact.artifact_id,
        publication_id=publication.publication_id,
        evidence_role=evidence_role,
        source_id=source_id,
        ast_source=ast_source,
        assurance=PublicationAssurance(),
        title=title,
        issuing_body=issuing_body,
        retrieved_at=retrieved_at,
        source_url=source_url,
        jurisdiction=jurisdiction,
    )
    return BoundArtifact(publication=publication, artifact=artifact, binding=binding)
