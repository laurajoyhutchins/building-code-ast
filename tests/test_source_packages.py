from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.evidence.io import source_register_from_dict
from building_code_ast.evidence.model import (
    AccessScope, AstSourceIdentity, EvidenceRole, PublicationIdentity,
    RightsStatus, SourceRegister, SourceRegisterEntry,
)
from building_code_ast.evidence.source_objects import (
    SourceObjectCatalog, SourceObjectRequirement, source_object_catalog_from_dict,
)
from building_code_ast.evidence.source_packages import (
    Artifact, ArtifactBinding, Derivation, PublicationAssurance, PublicationState,
    SourcePackage, SourceReadiness, legacy_source_package, source_audit,
)

ROOT = Path(__file__).resolve().parents[1]
SHA_A = "a" * 64
SHA_B = "b" * 64


def _entry(source_id: str, *, role: EvidenceRole, correction_set: str | None = None) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id=source_id,
        ast_source=AstSourceIdentity(artifact_id=source_id, edition_id=f"{source_id}:edition"),
        title=source_id,
        issuing_body="Example Standards Body",
        evidence_role=role,
        publication=PublicationIdentity(publication_family="EXAMPLE", edition="2026", correction_set=correction_set),
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
        ) for source_id in source_ids
    ))


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class SourcePackageTests(unittest.TestCase):
    def test_legacy_conversion_collapses_physical_artifact_and_preserves_bindings(self) -> None:
        register = SourceRegister(entries=(
            _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT),
            _entry("example:commentary", role=EvidenceRole.COMMENTARY),
        ))
        package = legacy_source_package(register, _catalog("example:normative", "example:commentary"))
        self.assertEqual(len(package.artifacts), 1)
        self.assertEqual(len(package.bindings), 2)
        artifact = package.artifacts[0]
        self.assertEqual({b.artifact_id for b in package.bindings}, {artifact.artifact_id})
        self.assertEqual({b.legacy_source_id for b in package.bindings}, {"example:normative", "example:commentary"})
        self.assertEqual({b.evidence_role for b in package.bindings}, {EvidenceRole.NORMATIVE_TEXT, EvidenceRole.COMMENTARY})

    def test_all_current_source_registers_convert_deterministically(self) -> None:
        catalog = source_object_catalog_from_dict(_json(ROOT / "corpora" / "source-object-catalog.json"))
        registers = sorted((ROOT / "corpora").glob("**/*-source-register.json"))
        self.assertTrue(registers)
        for path in registers:
            with self.subTest(path=str(path.relative_to(ROOT))):
                register = source_register_from_dict(_json(path))
                first = legacy_source_package(register, catalog)
                second = legacy_source_package(register, catalog)
                self.assertEqual(first.to_dict(), second.to_dict())

    def test_real_aci_and_tms_bundles_have_one_artifact_with_multiple_bindings(self) -> None:
        catalog = source_object_catalog_from_dict(_json(ROOT / "corpora" / "source-object-catalog.json"))
        cases = (
            (ROOT / "corpora" / "aci-318-19" / "aci-318-19-source-register.json", 2),
            (ROOT / "corpora" / "tms-402-602-16" / "tms-402-602-16-source-register.json", 4),
        )
        for path, binding_count in cases:
            with self.subTest(path=str(path.relative_to(ROOT))):
                package = legacy_source_package(source_register_from_dict(_json(path)), catalog)
                self.assertEqual(len(package.artifacts), 1)
                self.assertEqual(len(package.bindings), binding_count)

    def test_unresolved_correction_text_becomes_assurance_not_identity(self) -> None:
        unresolved = "unresolved:retained-artifact-correction-and-addenda-state"
        register = SourceRegister(entries=(
            _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT, correction_set=unresolved),
        ))
        package = legacy_source_package(register, _catalog("example:normative"))
        self.assertIsNone(package.publications[0].correction_set)
        self.assertEqual(package.bindings[0].assurance.correction_completeness, "unknown")
        self.assertEqual(package.bindings[0].assurance.legacy_observations, (unresolved,))

    def test_known_correction_state_remains_publication_identity(self) -> None:
        register = SourceRegister(entries=(
            _entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT, correction_set="errata-through-2026-07-01"),
        ))
        package = legacy_source_package(register, _catalog("example:normative"))
        self.assertEqual(package.publications[0].correction_set, "errata-through-2026-07-01")

    def test_conflicting_physical_identity_fails_closed(self) -> None:
        register = SourceRegister(entries=(_entry("example:normative", role=EvidenceRole.NORMATIVE_TEXT),))
        catalog = SourceObjectCatalog(entries=(SourceObjectRequirement(
            source_id="example:normative", object_key="engineering-sources/example/source.pdf",
            sha256=SHA_B, size=123, media_type="application/pdf",
        ),))
        with self.assertRaisesRegex(ValueError, "sha256 mismatch"):
            legacy_source_package(register, catalog)

    def test_derivation_is_exact_and_cannot_self_derive(self) -> None:
        publication = PublicationState(publication_family="EXAMPLE", edition="2026")
        source = Artifact(object_key="engineering-sources/example/source.pdf", sha256=SHA_A, size=123, media_type="application/pdf")
        derived = Artifact(object_key="engineering-sources/example/derivatives/component.pdf", sha256=SHA_B, size=45, media_type="application/pdf")
        binding = ArtifactBinding(
            artifact_id=source.artifact_id, publication_id=publication.publication_id,
            evidence_role=EvidenceRole.NORMATIVE_TEXT, legacy_source_id="example:normative",
            ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-2026"),
            assurance=PublicationAssurance(),
        )
        derivation = Derivation(
            input_artifact_ids=(source.artifact_id,), output_artifact_id=derived.artifact_id,
            transformation="page_range_extract", recipe="pages:10-20",
        )
        package = SourcePackage(publications=(publication,), artifacts=(source, derived), bindings=(binding,), derivations=(derivation,))
        self.assertEqual(package.derivations, (derivation,))
        with self.assertRaisesRegex(ValueError, "self-derivation"):
            SourcePackage(
                publications=(publication,), artifacts=(source,), bindings=(binding,),
                derivations=(Derivation(
                    input_artifact_ids=(source.artifact_id,), output_artifact_id=source.artifact_id,
                    transformation="ocr", recipe="fixture",
                ),),
            )

    def test_source_audit_is_computed_and_blocks_unverified_authority(self) -> None:
        publication = PublicationState(publication_family="EXAMPLE", edition="2026")
        artifact = Artifact(object_key="engineering-sources/example/source.pdf", sha256=SHA_A, size=123, media_type="application/pdf")
        binding = ArtifactBinding(
            artifact_id=artifact.artifact_id, publication_id=publication.publication_id,
            evidence_role=EvidenceRole.NORMATIVE_TEXT, legacy_source_id="example:normative",
            ast_source=AstSourceIdentity(artifact_id="example:normative", edition_id="example-2026"),
            assurance=PublicationAssurance(
                publication_identity="artifact_self_identified", publisher_equivalence="unverified",
                correction_completeness="unknown",
            ),
        )
        package = SourcePackage(publications=(publication,), artifacts=(artifact,), bindings=(binding,))
        audit = source_audit(package, retrievable_artifact_ids={artifact.artifact_id})
        self.assertEqual(audit[0].artifact_bytes, SourceReadiness.VERIFIED)
        self.assertEqual(audit[0].private_retrievability, SourceReadiness.VERIFIED)
        self.assertEqual(audit[0].normative_authority, SourceReadiness.BLOCKED)
        self.assertIn("publisher equivalence", audit[0].blockers)
        self.assertIn("correction completeness", audit[0].blockers)


if __name__ == "__main__":
    unittest.main()
