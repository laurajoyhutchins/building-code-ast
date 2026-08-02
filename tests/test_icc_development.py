from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    run_evidence_adapter,
)
from building_code_ast.evidence.development import (
    DEVELOPMENT_DISPOSITION_VALUES,
    DEVELOPMENT_KIND_VALUES,
    DEVELOPMENT_RECORD_VERSION,
    DevelopmentDisposition,
    DevelopmentLineage,
    DevelopmentRecord,
    DevelopmentRecordKind,
    IccDevelopmentTextAdapter,
    development_record_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BYTES = b"synthetic ICC development monograph bytes"


def _source() -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id="icc:ibc:2024:group-a-development",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2024:development:sha256:" + "a" * 64,
        ),
        title="Synthetic ICC Group A development records",
        issuing_body="International Code Council",
        evidence_role=EvidenceRole.DEVELOPMENT_HISTORY,
        publication=PublicationIdentity(
            publication_family="IBC development process",
            edition="2024",
            printing=None,
            digital_revision=None,
            correction_set=None,
            published_on="2023-04-01",
            effective_on=None,
        ),
        retrieved_at="2026-08-02T10:00:00-06:00",
        sha256=hashlib.sha256(SOURCE_BYTES).hexdigest(),
        media_type="application/pdf",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://example.invalid/icc-development.pdf",
        jurisdiction=None,
        rights_note=None,
    )


def _record(
    *,
    record_key: str = "G1-24:proposal",
    kind: DevelopmentRecordKind = DevelopmentRecordKind.PROPOSAL,
    disposition: DevelopmentDisposition = DevelopmentDisposition.SUBMITTED,
    sequence: int = 1,
    parent_keys: tuple[str, ...] = (),
    action_date: str | None = None,
) -> DevelopmentRecord:
    return DevelopmentRecord(
        source_id="icc:ibc:2024:group-a-development",
        proposal_id="G1-24",
        record_key=record_key,
        kind=kind,
        disposition=disposition,
        sequence=sequence,
        proponent="Synthetic Proponent" if kind is DevelopmentRecordKind.PROPOSAL else None,
        affected_locators=("202", "303.1"),
        parent_keys=parent_keys,
        action_date=action_date,
        summary="Synthetic process evidence.",
        source_page=1,
        source_anchor=record_key,
    )


class IccDevelopmentTests(unittest.TestCase):
    def test_record_round_trips_with_deterministic_identity(self) -> None:
        record = _record()
        payload = record.to_dict()
        restored = development_record_from_dict(payload)

        self.assertEqual(restored, record)
        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(payload["record_version"], DEVELOPMENT_RECORD_VERSION)
        self.assertRegex(payload["record_id"], r"^development:[0-9a-f]{64}$")

    def test_record_identity_changes_with_disposition_and_parents(self) -> None:
        first = _record()
        modified = _record(disposition=DevelopmentDisposition.APPROVED_AS_MODIFIED)
        linked = _record(parent_keys=("G1-24:origin",))

        self.assertNotEqual(first.record_id, modified.record_id)
        self.assertNotEqual(first.record_id, linked.record_id)

    def test_strict_deserialization_rejects_unknown_fields_and_bad_identity(self) -> None:
        payload = _record().to_dict()
        payload["invented"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            development_record_from_dict(payload)

        payload = _record().to_dict()
        payload["record_id"] = "development:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "record_id"):
            development_record_from_dict(payload)

    def test_deserialization_does_not_mutate_input(self) -> None:
        payload = _record().to_dict()
        before = copy.deepcopy(payload)
        development_record_from_dict(payload)
        self.assertEqual(payload, before)

    def test_schema_matches_runtime_enums(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/icc-development-record.schema.json").read_text(encoding="utf-8")
        )
        properties = schema["properties"]
        self.assertEqual(properties["record_version"]["const"], DEVELOPMENT_RECORD_VERSION)
        self.assertEqual(set(properties["kind"]["enum"]), DEVELOPMENT_KIND_VALUES)
        self.assertEqual(
            set(properties["disposition"]["enum"]), DEVELOPMENT_DISPOSITION_VALUES
        )

    def test_lineage_resolves_controlling_final_action(self) -> None:
        proposal = _record()
        committee = _record(
            record_key="G1-24:committee-action",
            kind=DevelopmentRecordKind.COMMITTEE_ACTION,
            disposition=DevelopmentDisposition.DISAPPROVED,
            sequence=2,
            parent_keys=(proposal.record_key,),
            action_date="2023-04-15",
        )
        final = _record(
            record_key="G1-24:final-action",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            disposition=DevelopmentDisposition.APPROVED_AS_MODIFIED,
            sequence=3,
            parent_keys=(committee.record_key,),
            action_date="2023-10-20",
        )
        lineage = DevelopmentLineage(records=(proposal, committee, final))

        self.assertEqual(lineage.controlling_record("G1-24"), final)
        self.assertEqual(lineage.records_for("G1-24"), (proposal, committee, final))

    def test_lineage_fails_closed_for_unresolved_parent_and_conflicting_finals(self) -> None:
        with self.assertRaisesRegex(ValueError, "unresolved parent"):
            DevelopmentLineage(
                records=(
                    _record(
                        record_key="G1-24:committee-action",
                        kind=DevelopmentRecordKind.COMMITTEE_ACTION,
                        disposition=DevelopmentDisposition.DISAPPROVED,
                        sequence=2,
                        parent_keys=("G1-24:missing",),
                    ),
                )
            )

        proposal = _record()
        final_a = _record(
            record_key="G1-24:final-a",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            disposition=DevelopmentDisposition.APPROVED,
            sequence=2,
            parent_keys=(proposal.record_key,),
        )
        final_b = _record(
            record_key="G1-24:final-b",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            disposition=DevelopmentDisposition.DISAPPROVED,
            sequence=3,
            parent_keys=(proposal.record_key,),
        )
        with self.assertRaisesRegex(ValueError, "conflicting final actions"):
            DevelopmentLineage(records=(proposal, final_a, final_b))

    def test_lineage_preserves_withdrawn_and_superseded_chains(self) -> None:
        proposal = _record()
        withdrawn = _record(
            record_key="G1-24:withdrawal",
            kind=DevelopmentRecordKind.HEARING_ACTION,
            disposition=DevelopmentDisposition.WITHDRAWN,
            sequence=2,
            parent_keys=(proposal.record_key,),
        )
        replacement = _record(
            record_key="G2-24:proposal",
            kind=DevelopmentRecordKind.PROPOSAL,
            disposition=DevelopmentDisposition.SUPERSEDED,
            sequence=1,
            parent_keys=(proposal.record_key,),
        )
        lineage = DevelopmentLineage(records=(proposal, withdrawn, replacement))

        self.assertEqual(lineage.controlling_record("G1-24"), withdrawn)
        self.assertEqual(lineage.records_for("G2-24"), (replacement,))

    def test_adapter_extracts_proposals_and_actions(self) -> None:
        pages = (
            """G1-24
Proponent: Synthetic Proponent
Affected: 202, 303.1
Proposal: Synthetic proposal summary.
Committee Action: Disapproved
Assembly Action: Approved as Modified
Final Action: Approved as Modified

G2-24
Proponent: Another Proponent
Affected: 404.2
Proposal: Synthetic second proposal.
Final Action: Withdrawn
""",
        )
        adapter = IccDevelopmentTextAdapter(page_text_extractor=lambda _: pages)
        result = run_evidence_adapter(adapter, _source(), SOURCE_BYTES)

        self.assertEqual(len(result.records), 6)
        lineage = DevelopmentLineage(records=result.records)
        self.assertEqual(
            lineage.controlling_record("G1-24").disposition,
            DevelopmentDisposition.APPROVED_AS_MODIFIED,
        )
        self.assertEqual(
            lineage.controlling_record("G2-24").disposition,
            DevelopmentDisposition.WITHDRAWN,
        )
        self.assertEqual(result.diagnostics, ())

    def test_adapter_retains_unknown_action_as_diagnostic(self) -> None:
        pages = (
            """G3-24
Proponent: Synthetic Proponent
Affected: 505.1
Proposal: Synthetic third proposal.
Committee Action: Reconsidered with conditions
""",
        )
        adapter = IccDevelopmentTextAdapter(page_text_extractor=lambda _: pages)
        result = run_evidence_adapter(adapter, _source(), SOURCE_BYTES)

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.diagnostics[0].code, "unsupported-development-action")
        self.assertEqual(result.unsupported_regions[0].page, 1)


if __name__ == "__main__":
    unittest.main()
