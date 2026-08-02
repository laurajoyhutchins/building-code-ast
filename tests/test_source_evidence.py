from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    ACCESS_SCOPE_VALUES,
    EVIDENCE_ROLE_VALUES,
    RIGHTS_STATUS_VALUES,
    SOURCE_REGISTER_VERSION,
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    publication_state_id,
    source_register_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]


def _entry(
    *,
    source_id: str = "icc:ibc:2021:errata:complete",
    printing: str | None = "first-printing",
    correction_set: str | None = "complete-2024-05",
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
        evidence_role=EvidenceRole.OFFICIAL_CORRECTION,
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
        sha256="b" * 64,
        media_type="application/pdf",
        access_scope=access_scope,
        rights_status=rights_status,
        source_url="https://example.invalid/ibc-2021-errata.pdf",
        jurisdiction=None,
        rights_note=rights_note,
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


if __name__ == "__main__":
    unittest.main()
