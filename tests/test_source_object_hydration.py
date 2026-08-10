from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    ObjectProvider,
    PrivateSourceObjectLocator,
    PrivateSourceObjectLocatorRegistry,
    PublicationIdentity,
    RightsStatus,
    SourceObjectCatalog,
    SourceObjectRequirement,
    SourceRegister,
    SourceRegisterEntry,
)
from building_code_ast.evidence.source_object_hydration import (
    HydrationStatus,
    hydrate_source_object,
    validate_source_object_requirement,
    verify_local_source_object,
)


class RecordingFetcher:
    provider = ObjectProvider.GOOGLE_DRIVE

    def __init__(self, payload: bytes, *, fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail
        self.called = False
        self.seen_object_id: str | None = None

    def fetch(self, locator: PrivateSourceObjectLocator, destination: Path) -> None:
        self.called = True
        self.seen_object_id = locator.object_id
        if self.fail:
            raise RuntimeError("synthetic fetch failure")
        destination.write_bytes(self.payload)


class WrongProviderFetcher(RecordingFetcher):
    provider = "unsupported-provider"


class SourceObjectHydrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = b"synthetic private source bytes\n"
        digest = hashlib.sha256(self.payload).hexdigest()
        self.source = SourceRegisterEntry(
            source_id="source:synthetic:2026:pdf:hydration",
            ast_source=AstSourceIdentity(
                artifact_id="sha256:" + digest,
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
            sha256=digest,
            media_type="application/pdf",
            access_scope=AccessScope.LICENSED_LOCAL,
            rights_status=RightsStatus.LICENSED,
            rights_note="Synthetic restricted fixture; no source expression is committed.",
        )
        self.register = SourceRegister(entries=(self.source,))
        self.requirement = SourceObjectRequirement(
            source_id=self.source.source_id,
            object_key="building-code-ast/synthetic-2026/source",
            sha256=digest,
            size=len(self.payload),
            media_type=self.source.media_type,
        )
        self.catalog = SourceObjectCatalog(entries=(self.requirement,))
        self.locator = PrivateSourceObjectLocator(
            object_key=self.requirement.object_key,
            provider=ObjectProvider.GOOGLE_DRIVE,
            object_id="opaque-private-provider-object-id",
            path_hint="private/source.pdf",
        )
        self.locators = PrivateSourceObjectLocatorRegistry(locators=(self.locator,))

    def test_hydration_fetches_private_locator_and_atomically_places_verified_bytes(self) -> None:
        fetcher = RecordingFetcher(self.payload)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source.pdf"
            destination.write_bytes(b"old verified object")

            receipt = hydrate_source_object(
                self.catalog,
                self.register,
                self.locators,
                source_id=self.source.source_id,
                destination=destination,
                fetcher=fetcher,
            )

            self.assertEqual(destination.read_bytes(), self.payload)
            self.assertEqual(list(Path(directory).iterdir()), [destination])

        self.assertTrue(fetcher.called)
        self.assertEqual(fetcher.seen_object_id, self.locator.object_id)
        self.assertIs(receipt.status, HydrationStatus.VERIFIED)
        self.assertEqual(
            set(receipt.to_dict()),
            {
                "receipt_version",
                "type",
                "status",
                "source_id",
                "object_key",
                "sha256",
                "size",
                "media_type",
            },
        )
        rendered = json.dumps(receipt.to_dict(), sort_keys=True)
        self.assertNotIn("provider", rendered)
        self.assertNotIn("object_id", rendered)
        self.assertNotIn("path_hint", rendered)
        self.assertNotIn("destination", rendered)
        self.assertNotIn("opaque-private-provider-object-id", rendered)

    def test_digest_mismatch_preserves_existing_destination_and_cleans_partial(self) -> None:
        corrupted = bytes([self.payload[0] ^ 1]) + self.payload[1:]
        self.assertEqual(len(corrupted), len(self.payload))
        fetcher = RecordingFetcher(corrupted)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source.pdf"
            destination.write_bytes(b"old verified object")

            with self.assertRaisesRegex(ValueError, "sha256"):
                hydrate_source_object(
                    self.catalog,
                    self.register,
                    self.locators,
                    source_id=self.source.source_id,
                    destination=destination,
                    fetcher=fetcher,
                )

            self.assertEqual(destination.read_bytes(), b"old verified object")
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_fetch_failure_preserves_existing_destination_and_cleans_partial(self) -> None:
        fetcher = RecordingFetcher(self.payload, fail=True)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source.pdf"
            destination.write_bytes(b"old verified object")

            with self.assertRaisesRegex(RuntimeError, "synthetic fetch failure"):
                hydrate_source_object(
                    self.catalog,
                    self.register,
                    self.locators,
                    source_id=self.source.source_id,
                    destination=destination,
                    fetcher=fetcher,
                )

            self.assertEqual(destination.read_bytes(), b"old verified object")
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_selected_requirement_is_validated_before_private_fetch(self) -> None:
        bad_requirement = SourceObjectRequirement(
            source_id=self.source.source_id,
            object_key=self.requirement.object_key,
            sha256="b" * 64,
            size=self.requirement.size,
            media_type=self.requirement.media_type,
        )
        fetcher = RecordingFetcher(self.payload)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "sha256"):
                hydrate_source_object(
                    SourceObjectCatalog(entries=(bad_requirement,)),
                    self.register,
                    self.locators,
                    source_id=self.source.source_id,
                    destination=Path(directory) / "source.pdf",
                    fetcher=fetcher,
                )

        self.assertFalse(fetcher.called)

    def test_selected_requirement_does_not_require_artificial_union_register(self) -> None:
        unrelated = SourceObjectRequirement(
            source_id="source:other:2026:pdf:bbbbbbbb",
            object_key="building-code-ast/other-2026/source",
            sha256="b" * 64,
            size=99,
            media_type="application/pdf",
        )
        catalog = SourceObjectCatalog(entries=(self.requirement, unrelated))

        validate_source_object_requirement(self.requirement, self.register)

        fetcher = RecordingFetcher(self.payload)
        with tempfile.TemporaryDirectory() as directory:
            receipt = hydrate_source_object(
                catalog,
                self.register,
                self.locators,
                source_id=self.source.source_id,
                destination=Path(directory) / "source.pdf",
                fetcher=fetcher,
            )

        self.assertEqual(receipt.source_id, self.source.source_id)
        self.assertTrue(fetcher.called)

    def test_provider_mismatch_fails_before_fetch(self) -> None:
        fetcher = WrongProviderFetcher(self.payload)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "provider"):
                hydrate_source_object(
                    self.catalog,
                    self.register,
                    self.locators,
                    source_id=self.source.source_id,
                    destination=Path(directory) / "source.pdf",
                    fetcher=fetcher,
                )
        self.assertFalse(fetcher.called)

    def test_local_verification_accepts_exact_regular_file_and_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.pdf"
            source_path.write_bytes(self.payload)
            receipt = verify_local_source_object(
                self.catalog,
                self.register,
                source_id=self.source.source_id,
                path=source_path,
            )
            self.assertIs(receipt.status, HydrationStatus.VERIFIED)

            link = Path(directory) / "source-link.pdf"
            try:
                os.symlink(source_path, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_local_source_object(
                    self.catalog,
                    self.register,
                    source_id=self.source.source_id,
                    path=link,
                )

    def test_receipt_schema_is_source_safe(self) -> None:
        root = Path(__file__).resolve().parents[1]
        schema = json.loads(
            (root / "schemas" / "source-object-hydration-receipt.schema.json").read_text()
        )
        properties = set(schema["properties"])

        self.assertEqual(
            properties,
            {
                "receipt_version",
                "type",
                "status",
                "source_id",
                "object_key",
                "sha256",
                "size",
                "media_type",
            },
        )
        rendered = json.dumps(schema, sort_keys=True)
        self.assertNotIn("object_id", rendered)
        self.assertNotIn("path_hint", rendered)
        self.assertNotIn("access_token", rendered)
        self.assertNotIn("destination", rendered)


if __name__ == "__main__":
    unittest.main()
