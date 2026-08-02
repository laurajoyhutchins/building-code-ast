from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    ACCESS_SCOPE_VALUES,
    EVIDENCE_ROLE_VALUES,
    RIGHTS_STATUS_VALUES,
    SOURCE_REGISTER_VERSION,
    AccessScope,
    AdapterResult,
    AstSourceIdentity,
    EvidenceDiagnostic,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegion,
    SourceRegister,
    SourceRegisterEntry,
    publication_state_id,
    run_evidence_adapter,
    source_register_from_dict,
)
from building_code_ast.model import DiagnosticSeverity


ROOT = Path(__file__).resolve().parents[1]


def _entry(
    *,
    source_id: str = "icc:ibc:2021:errata:complete",
    printing: str | None = "first-printing",
    correction_set: str | None = "complete-2024-05",
    evidence_role: EvidenceRole = EvidenceRole.OFFICIAL_CORRECTION,
    sha256: str = "b" * 64,
    media_type: str = "application/pdf",
    access_scope: AccessScope = AccessScope.PUBLIC,
    rights_status: RightsStatus = RightsStatus.PUBLIC_OFFICIAL,
    rights_note: str | None = None,
) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id=source_id,
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="2021 International Building Code complete errata",
        issuing_body="International Code Council",
        evidence_role=evidence_role,
        publication=PublicationIdentity(
            publication_family="IBC",
            edition="2021",
            printing=printing,
            digital_revision=None,
            correction_set=correction_set,
            published_on="2020-10-23",
            effective_on=None,
        ),
        retrieved_at="2026-08-02T08:00:00-06:00",
        sha256=sha256,
        media_type=media_type,
        access_scope=access_scope,
        rights_status=rights_status,
        source_url="https://example.invalid/ibc-2021-errata.pdf",
        jurisdiction=None,
        rights_note=rights_note,
    )


class _FakeAdapter:
    adapter_id = "icc-errata-pdf"
    adapter_version = "0.1.0"
    supported_roles = frozenset({EvidenceRole.OFFICIAL_CORRECTION})
    supported_media_types = frozenset({"application/pdf"})

    def __init__(
        self,
        *,
        returned_source_id: str | None = None,
        returned_adapter_id: str | None = None,
        returned_adapter_version: str | None = None,
    ) -> None:
        self.called = False
        self.returned_source_id = returned_source_id
        self.returned_adapter_id = returned_adapter_id
        self.returned_adapter_version = returned_adapter_version

    def extract(
        self,
        source: SourceRegisterEntry,
        content: bytes,
    ) -> AdapterResult[dict[str, str]]:
        self.called = True
        self.seen_content = content
        return AdapterResult(
            source_id=self.returned_source_id or source.source_id,
            adapter_id=self.returned_adapter_id or self.adapter_id,
            adapter_version=self.returned_adapter_version or self.adapter_version,
            records=({"kind": "synthetic_erratum"},),
            diagnostics=(
                EvidenceDiagnostic(
                    code="synthetic-review-note",
                    severity=DiagnosticSeverity.INFO,
                    message="Synthetic adapter result for contract verification.",
                    region=SourceRegion(page=2, anchor="entry:1"),
                ),
            ),
            unsupported_regions=(
                SourceRegion(page=3, bbox=(10.0, 20.0, 30.0, 40.0)),
            ),
        )


class SourceEvidenceTests(unittest.TestCase):
    def test_source_register_round_trips_with_publication_state(self) -> None:
        register = SourceRegister(entries=(_entry(),))

        payload = register.to_dict()
        restored = source_register_from_dict(payload)

        self.assertEqual(restored, register)
        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(payload["register_version"], SOURCE_REGISTER_VERSION)
        self.assertEqual(payload["type"], "source_register")
        self.assertEqual(
            payload["entries"][0]["publication"]["state_id"],
            publication_state_id(register.entries[0].publication),
        )
        self.assertNotIn("source_text", json.dumps(payload))

    def test_publication_state_identity_is_stable_and_printing_sensitive(self) -> None:
        first = _entry().publication
        repeated = _entry().publication
        third = _entry(printing="third-printing").publication
        corrected = _entry(correction_set="complete-2025-01").publication

        self.assertEqual(publication_state_id(first), publication_state_id(repeated))
        self.assertNotEqual(publication_state_id(first), publication_state_id(third))
        self.assertNotEqual(publication_state_id(first), publication_state_id(corrected))
        self.assertRegex(publication_state_id(first), r"^publication:[0-9a-f]{64}$")

    def test_source_ids_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate source_id"):
            SourceRegister(entries=(_entry(), _entry()))

    def test_source_register_requires_an_immutable_entry_tuple(self) -> None:
        with self.assertRaisesRegex(ValueError, "tuple"):
            SourceRegister(entries=[_entry()])  # type: ignore[arg-type]

    def test_restricted_sources_require_a_rights_note(self) -> None:
        with self.assertRaisesRegex(ValueError, "rights_note"):
            _entry(
                access_scope=AccessScope.LICENSED_LOCAL,
                rights_status=RightsStatus.LICENSED,
            )

        entry = _entry(
            access_scope=AccessScope.LICENSED_LOCAL,
            rights_status=RightsStatus.LICENSED,
            rights_note="Locally held under an owner-provided license; do not redistribute.",
        )
        self.assertEqual(entry.rights_status, RightsStatus.LICENSED)

    def test_invalid_digest_is_rejected(self) -> None:
        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["sha256"] = "not-a-digest"

        with self.assertRaisesRegex(ValueError, "sha256"):
            source_register_from_dict(payload)

    def test_dates_and_retrieval_timestamp_are_strict(self) -> None:
        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["publication"]["published_on"] = "2021-99-99"

        with self.assertRaisesRegex(ValueError, "published_on"):
            source_register_from_dict(payload)

        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["retrieved_at"] = "2026-08-02T08:00:00"

        with self.assertRaisesRegex(ValueError, "timezone"):
            source_register_from_dict(payload)

    def test_unknown_fields_and_enum_values_are_rejected(self) -> None:
        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["publication"]["invented"] = True

        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            source_register_from_dict(payload)

        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["evidence_role"] = "helpful_document"

        with self.assertRaisesRegex(ValueError, "evidence_role is unsupported"):
            source_register_from_dict(payload)

    def test_serialized_state_id_must_match_deterministic_identity(self) -> None:
        payload = SourceRegister(entries=(_entry(),)).to_dict()
        payload["entries"][0]["publication"]["state_id"] = "publication:" + "0" * 64

        with self.assertRaisesRegex(ValueError, "state_id"):
            source_register_from_dict(payload)

    def test_schema_matches_runtime_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/source-register.schema.json").read_text(encoding="utf-8")
        )
        entry = schema["$defs"]["sourceRegisterEntry"]["properties"]

        self.assertEqual(schema["properties"]["register_version"]["const"], SOURCE_REGISTER_VERSION)
        self.assertEqual(set(entry["evidence_role"]["enum"]), EVIDENCE_ROLE_VALUES)
        self.assertEqual(set(entry["access_scope"]["enum"]), ACCESS_SCOPE_VALUES)
        self.assertEqual(set(entry["rights_status"]["enum"]), RIGHTS_STATUS_VALUES)

    def test_deserialization_does_not_mutate_input(self) -> None:
        payload = SourceRegister(entries=(_entry(),)).to_dict()
        before = copy.deepcopy(payload)

        source_register_from_dict(payload)

        self.assertEqual(payload, before)

    def test_digest_mismatch_prevents_adapter_execution(self) -> None:
        adapter = _FakeAdapter()

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            run_evidence_adapter(adapter, _entry(), b"different bytes")

        self.assertFalse(adapter.called)

    def test_adapter_role_and_media_type_must_match(self) -> None:
        content = b"synthetic source bytes"
        digest = hashlib.sha256(content).hexdigest()
        adapter = _FakeAdapter()

        with self.assertRaisesRegex(ValueError, "evidence role"):
            run_evidence_adapter(
                adapter,
                _entry(evidence_role=EvidenceRole.DEVELOPMENT_HISTORY, sha256=digest),
                content,
            )
        self.assertFalse(adapter.called)

        with self.assertRaisesRegex(ValueError, "media type"):
            run_evidence_adapter(
                adapter,
                _entry(sha256=digest, media_type="text/html"),
                content,
            )
        self.assertFalse(adapter.called)

    def test_guarded_adapter_execution_preserves_result(self) -> None:
        content = b"synthetic source bytes"
        source = _entry(sha256=hashlib.sha256(content).hexdigest())
        adapter = _FakeAdapter()

        result = run_evidence_adapter(adapter, source, content)

        self.assertTrue(adapter.called)
        self.assertEqual(adapter.seen_content, content)
        self.assertEqual(result.records, ({"kind": "synthetic_erratum"},))
        self.assertEqual(result.diagnostics[0].code, "synthetic-review-note")
        self.assertEqual(result.unsupported_regions[0].page, 3)
        self.assertEqual(
            result.unsupported_regions[0].to_dict()["bbox"],
            [10.0, 20.0, 30.0, 40.0],
        )

    def test_adapter_result_identity_must_match_invocation(self) -> None:
        content = b"synthetic source bytes"
        source = _entry(sha256=hashlib.sha256(content).hexdigest())

        with self.assertRaisesRegex(ValueError, "source_id"):
            run_evidence_adapter(
                _FakeAdapter(returned_source_id="other-source"),
                source,
                content,
            )
        with self.assertRaisesRegex(ValueError, "adapter_id"):
            run_evidence_adapter(
                _FakeAdapter(returned_adapter_id="other-adapter"),
                source,
                content,
            )
        with self.assertRaisesRegex(ValueError, "adapter_version"):
            run_evidence_adapter(
                _FakeAdapter(returned_adapter_version="9.9.9"),
                source,
                content,
            )

    def test_source_regions_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one locator"):
            SourceRegion()
        with self.assertRaisesRegex(ValueError, "positive integer"):
            SourceRegion(page=0)
        with self.assertRaisesRegex(ValueError, "page is required"):
            SourceRegion(bbox=(1.0, 2.0, 3.0, 4.0))
        with self.assertRaisesRegex(ValueError, "positive area"):
            SourceRegion(page=1, bbox=(3.0, 2.0, 1.0, 4.0))

    def test_evidence_diagnostic_serializes_region(self) -> None:
        diagnostic = EvidenceDiagnostic(
            code="unsupported-table",
            severity=DiagnosticSeverity.WARNING,
            message="Table structure is retained for review.",
            region=SourceRegion(page=4, anchor="table:1"),
        )

        self.assertEqual(
            diagnostic.to_dict(),
            {
                "code": "unsupported-table",
                "severity": "warning",
                "message": "Table structure is retained for review.",
                "region": {"page": 4, "anchor": "table:1", "bbox": None},
            },
        )


if __name__ == "__main__":
    unittest.main()
