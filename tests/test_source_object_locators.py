from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    source_register_from_dict,
)
from building_code_ast.evidence.source_objects import (
    ObjectProvider,
    PrivateSourceObjectLocator,
    PrivateSourceObjectLocatorRegistry,
    SourceObjectCatalog,
    SourceObjectRequirement,
    private_source_object_locator_registry_from_dict,
    source_object_catalog_from_dict,
    validate_source_object_catalog,
)


class SourceObjectLocatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SourceRegisterEntry(
            source_id="source:synthetic:2026:pdf:aaaa1111",
            ast_source=AstSourceIdentity(
                artifact_id="sha256:" + "a" * 64,
                edition_id="synthetic-2026",
            ),
            title="Synthetic retained source",
            issuing_body="Synthetic Issuer",
            evidence_role=EvidenceRole.NORMATIVE_TEXT,
            publication=PublicationIdentity(
                publication_family="Synthetic Standard",
                edition="2026",
            ),
            retrieved_at="2026-08-10T08:00:00-06:00",
            sha256="a" * 64,
            media_type="application/pdf",
            access_scope=AccessScope.LICENSED_LOCAL,
            rights_status=RightsStatus.LICENSED,
            rights_note="Synthetic restricted fixture; no source expression is committed.",
        )
        self.requirement = SourceObjectRequirement(
            source_id=self.source.source_id,
            object_key="building-code-ast/synthetic-2026/source",
            sha256=self.source.sha256,
            size=12345,
            media_type=self.source.media_type,
        )

    def test_public_requirement_serialization_contains_no_private_locator(self) -> None:
        payload = self.requirement.to_dict()

        self.assertEqual(payload["object_key"], "building-code-ast/synthetic-2026/source")
        self.assertNotIn("provider", payload)
        self.assertNotIn("object_id", payload)
        self.assertNotIn("path_hint", payload)
        self.assertNotIn("credentials", payload)

    def test_catalog_cross_validates_against_authoritative_source_register(self) -> None:
        catalog = SourceObjectCatalog(entries=(self.requirement,))
        register = SourceRegister(entries=(self.source,))

        validate_source_object_catalog(catalog, register)

        bad = SourceObjectCatalog(
            entries=(
                SourceObjectRequirement(
                    source_id=self.source.source_id,
                    object_key=self.requirement.object_key,
                    sha256="b" * 64,
                    size=self.requirement.size,
                    media_type=self.requirement.media_type,
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_source_object_catalog(bad, register)

    def test_multiple_source_identities_can_share_one_exact_logical_object(self) -> None:
        commentary = SourceObjectRequirement(
            source_id="source:synthetic:2026:pdf:aaaa1111:commentary",
            object_key=self.requirement.object_key,
            sha256=self.requirement.sha256,
            size=self.requirement.size,
            media_type=self.requirement.media_type,
        )

        catalog = SourceObjectCatalog(entries=(self.requirement, commentary))

        self.assertEqual(len(catalog.entries), 2)
        self.assertEqual(
            {entry.object_key for entry in catalog.entries},
            {self.requirement.object_key},
        )

    def test_shared_logical_object_rejects_conflicting_byte_identity(self) -> None:
        conflict = SourceObjectRequirement(
            source_id="source:synthetic:2026:pdf:bbbb2222",
            object_key=self.requirement.object_key,
            sha256="b" * 64,
            size=self.requirement.size,
            media_type=self.requirement.media_type,
        )

        with self.assertRaisesRegex(ValueError, "conflicting identity"):
            SourceObjectCatalog(entries=(self.requirement, conflict))

    def test_private_locator_is_keyed_by_logical_object_key_not_source_identity(self) -> None:
        locator = PrivateSourceObjectLocator(
            object_key=self.requirement.object_key,
            provider=ObjectProvider.GOOGLE_DRIVE,
            object_id="opaque-private-drive-id",
            path_hint="Building Code AST/00_sources/synthetic-2026/source.pdf",
        )
        registry = PrivateSourceObjectLocatorRegistry(locators=(locator,))

        self.assertIs(registry.resolve(self.requirement.object_key), locator)
        self.assertNotIn("sha256", locator.to_dict())
        self.assertNotIn("source_id", locator.to_dict())

    def test_private_locator_parser_rejects_credential_fields(self) -> None:
        payload = {
            "locator_version": "0.1.0",
            "type": "private_source_object_locators",
            "locators": [
                {
                    "object_key": self.requirement.object_key,
                    "provider": "google_drive",
                    "object_id": "opaque-private-drive-id",
                    "path_hint": None,
                    "access_token": "must-never-be-accepted",
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            private_source_object_locator_registry_from_dict(payload)

    def test_catalog_parser_is_strict_and_round_trips(self) -> None:
        catalog = SourceObjectCatalog(entries=(self.requirement,))
        payload = catalog.to_dict()

        self.assertEqual(source_object_catalog_from_dict(payload), catalog)
        payload["entries"][0]["object_id"] = "private-id-must-not-fit-public-schema"
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            source_object_catalog_from_dict(payload)

    def test_repository_catalog_contains_only_registered_source_safe_fields(self) -> None:
        root = Path(__file__).resolve().parents[1]
        payload = json.loads((root / "corpora" / "source-object-catalog.json").read_text())
        catalog = source_object_catalog_from_dict(payload)

        self.assertEqual(len(catalog.entries), 14)
        for entry in payload["entries"]:
            self.assertEqual(
                set(entry),
                {"source_id", "object_key", "sha256", "size", "media_type"},
            )
        rendered = json.dumps(payload, sort_keys=True)
        self.assertNotIn("google_drive", rendered)
        self.assertNotIn("object_id", rendered)
        self.assertNotIn("drive.google.com", rendered)

    def test_repository_catalog_cross_validates_all_durable_source_registers(self) -> None:
        root = Path(__file__).resolve().parents[1]
        register_paths = (
            "corpora/aci-318-19/aci-318-19-source-register.json",
            "corpora/aisc-scm-15/aisc-scm-15-source-register.json",
            "corpora/asce-7-22/asce-7-22-source-register.json",
            "corpora/ashrae-62.1-2016/ashrae-62.1-2016-source-register.json",
            "corpora/ashrae-90.1-2016/ashrae-90.1-2016-source-register.json",
            "corpora/ibc-2018/ibc-2018-source-register.json",
            "corpora/nds-2018/nds-2018-source-register.json",
            "corpora/nec-2017/nec-2017-source-register.json",
            "corpora/nfpa-13-2019/nfpa-13-2019-source-register.json",
            "corpora/tms-402-602-16/tms-402-602-16-source-register.json",
        )
        authoritative_entries = []
        for path in register_paths:
            payload = json.loads((root / path).read_text())
            authoritative_entries.extend(source_register_from_dict(payload).entries)
        source_register = SourceRegister(entries=tuple(authoritative_entries))

        catalog_payload = json.loads(
            (root / "corpora" / "source-object-catalog.json").read_text()
        )
        catalog = source_object_catalog_from_dict(catalog_payload)

        self.assertEqual(
            {entry.source_id for entry in catalog.entries},
            {entry.source_id for entry in source_register.entries},
        )
        validate_source_object_catalog(catalog, source_register)


if __name__ == "__main__":
    unittest.main()
