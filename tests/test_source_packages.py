from __future__ import annotations

import unittest

from building_code_ast.evidence.model import AccessScope, AstSourceIdentity, EvidenceRole, RightsStatus
from building_code_ast.evidence.source_packages import Artifact, ArtifactBinding, Derivation, PublicationAssurance, PublicationState, SourcePackage, SourceReadiness, source_audit, source_package_from_dict

SHA_A = "a" * 64
SHA_B = "b" * 64


def _package() -> SourcePackage:
    publication = PublicationState(publication_family="EXAMPLE", edition="2026")
    artifact = Artifact(object_key="engineering-sources/example/source.pdf", sha256=SHA_A, size=123, media_type="application/pdf", access_scope=AccessScope.LICENSED_LOCAL, rights_status=RightsStatus.LICENSED, rights_note="Licensed test fixture.")
    binding = ArtifactBinding(artifact_id=artifact.artifact_id, publication_id=publication.publication_id, evidence_role=EvidenceRole.NORMATIVE_TEXT, source_id="example:normative", ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-2026"), assurance=PublicationAssurance(publication_identity="artifact_self_identified", publisher_equivalence="unverified", correction_completeness="unknown"))
    return SourcePackage(package_id="example", publications=(publication,), artifacts=(artifact,), bindings=(binding,))


class SourcePackageTests(unittest.TestCase):
    def test_round_trip_validates_generated_identity(self) -> None:
        package = _package()
        self.assertEqual(source_package_from_dict(package.to_dict()).to_dict(), package.to_dict())

    def test_one_artifact_can_have_multiple_publication_bindings(self) -> None:
        package = _package()
        other = PublicationState(publication_family="EXAMPLE Commentary", edition="2026")
        commentary = ArtifactBinding(artifact_id=package.artifacts[0].artifact_id, publication_id=other.publication_id, evidence_role=EvidenceRole.COMMENTARY, source_id="example:commentary", ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-commentary"))
        combined = SourcePackage(package_id="combined", publications=(package.publications[0], other), artifacts=package.artifacts, bindings=(package.bindings[0], commentary))
        self.assertEqual(len(combined.artifacts), 1)
        self.assertEqual(len(combined.bindings), 2)

    def test_derivation_is_exact_and_cannot_self_derive(self) -> None:
        package = _package()
        derived = Artifact(object_key="engineering-sources/example/derivatives/component.pdf", sha256=SHA_B, size=45, media_type="application/pdf")
        derivation = Derivation(input_artifact_ids=(package.artifacts[0].artifact_id,), output_artifact_id=derived.artifact_id, transformation="page_range_extract", recipe="pages:10-20")
        SourcePackage(package_id="derived", publications=package.publications, artifacts=(package.artifacts[0], derived), bindings=package.bindings, derivations=(derivation,))
        with self.assertRaisesRegex(ValueError, "self-derivation"):
            SourcePackage(package_id="bad", publications=package.publications, artifacts=package.artifacts, bindings=package.bindings, derivations=(Derivation(input_artifact_ids=(package.artifacts[0].artifact_id,), output_artifact_id=package.artifacts[0].artifact_id, transformation="ocr", recipe="fixture"),))

    def test_source_audit_is_computed_and_blocks_unverified_authority(self) -> None:
        package = _package()
        artifact_id = package.artifacts[0].artifact_id
        audit = source_audit(package, retrievable_artifact_ids={artifact_id})
        self.assertEqual(audit[0].artifact_bytes, SourceReadiness.VERIFIED)
        self.assertEqual(audit[0].private_retrievability, SourceReadiness.VERIFIED)
        self.assertEqual(audit[0].normative_authority, SourceReadiness.BLOCKED)
        self.assertIn("publisher equivalence", audit[0].blockers)
        self.assertIn("correction completeness", audit[0].blockers)

    def test_missing_derived_input_retrievability_blocks_reproducibility(self) -> None:
        package = _package()
        derived = Artifact(object_key="engineering-sources/example/derivatives/component.pdf", sha256=SHA_B, size=45, media_type="application/pdf")
        binding = ArtifactBinding(artifact_id=derived.artifact_id, publication_id=package.publications[0].publication_id, evidence_role=EvidenceRole.NORMATIVE_TEXT, source_id="example:derived", ast_source=AstSourceIdentity(artifact_id="example:derived", edition_id="example-2026"), assurance=PublicationAssurance(publisher_equivalence="verified", correction_completeness="verified", addenda_completeness="not_applicable"))
        derived_package = SourcePackage(package_id="derived", publications=package.publications, artifacts=(package.artifacts[0], derived), bindings=(binding,), derivations=(Derivation(input_artifact_ids=(package.artifacts[0].artifact_id,), output_artifact_id=derived.artifact_id, transformation="page_range_extract", recipe="pages:10-20"),))
        audit = source_audit(derived_package, retrievable_artifact_ids={derived.artifact_id})
        self.assertEqual(audit[0].derivation_reproducibility, SourceReadiness.BLOCKED)
        self.assertIn("derivation input retrievability", audit[0].blockers)


if __name__ == "__main__":
    unittest.main()
