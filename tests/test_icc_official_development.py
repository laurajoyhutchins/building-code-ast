from __future__ import annotations

import hashlib
import unittest

from provenance_fixtures import bound_source

from building_code_ast.evidence import (
    PublicationState,
    BoundArtifact,
    AccessScope,
    AstSourceIdentity,
    DevelopmentDisposition,
    DevelopmentLineage,
    DevelopmentRecordKind,
    EvidenceRole,
    IccActionStage,
    IccCommitteeActionPdfAdapter,
    IccProposalMonographPdfAdapter,
    RightsStatus,
    run_evidence_adapter,
)


PROPOSAL_BYTES = b"official-shaped proposal bytes"
ACTION_BYTES = b"official-shaped action bytes"


def _source(source_id: str, content: bytes) -> BoundArtifact:
    return bound_source(
        source_id=source_id,
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2024:development:sha256:" + "a" * 64,
        ),
        title="Official-shaped ICC development artifact",
        issuing_body="International Code Council",
        evidence_role=EvidenceRole.DEVELOPMENT_HISTORY,
        publication=PublicationState(
            publication_family="IBC development process",
            edition="2024",
            published_on="2024-03-01",
        ),
        retrieved_at="2026-08-02T11:30:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type="application/pdf",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://example.invalid/official-development.pdf",
    )


class IccOfficialDevelopmentTests(unittest.TestCase):
    def test_monograph_adapter_extracts_single_part_proposal(self) -> None:
        pages = (
            """2024 GROUP A PROPOSED CHANGES
FS1-24
IBC: 703.2.1, 703.2.2
Proponents: Example Proponent, Example Organization
2024 International Building Code
Revise as follows:
""",
        )
        adapter = IccProposalMonographPdfAdapter(page_text_extractor=lambda _: pages)
        result = run_evidence_adapter(adapter, _source("icc:proposal", PROPOSAL_BYTES), PROPOSAL_BYTES)

        self.assertEqual(len(result.records), 1)
        record = result.records[0]
        self.assertEqual(record.proposal_id, "FS1-24")
        self.assertEqual(record.affected_locators, ("703.2.1", "703.2.2"))
        self.assertEqual(record.record_key, "FS1-24:proposal")
        self.assertEqual(result.diagnostics, ())

    def test_monograph_adapter_fails_closed_on_multipart_proposal(self) -> None:
        pages = (
            """G1-24 Part I
IBC: 701.1, 801.1
Proponents: Example Proponent
""",
        )
        adapter = IccProposalMonographPdfAdapter(page_text_extractor=lambda _: pages)
        result = run_evidence_adapter(adapter, _source("icc:multipart", PROPOSAL_BYTES), PROPOSAL_BYTES)

        self.assertEqual(result.records, ())
        self.assertEqual(
            result.diagnostics[0].code,
            "unsupported-multipart-development-proposal",
        )

    def test_action_adapter_maps_official_committee_vocabulary(self) -> None:
        pages = (
            """2024 Group A - Report of the Committee Action Hearing Results
FS1-24
Committee Action: As Modified by Committee (AMC1)
Committee Reason: Example reason.
FS1-24
""",
        )
        adapter = IccCommitteeActionPdfAdapter(
            stage=IccActionStage(
                record_kind=DevelopmentRecordKind.COMMITTEE_ACTION,
                record_key_suffix="cah1",
                parent_key_suffix="proposal",
                sequence=2,
                action_date="2024-04-14",
            ),
            affected_locators_by_proposal={"FS1-24": ("703.2.1", "703.2.2")},
            page_text_extractor=lambda _: pages,
        )
        result = run_evidence_adapter(adapter, _source("icc:cah1", ACTION_BYTES), ACTION_BYTES)

        self.assertEqual(len(result.records), 1)
        record = result.records[0]
        self.assertEqual(record.disposition, DevelopmentDisposition.APPROVED_AS_MODIFIED)
        self.assertEqual(record.parent_keys, ("FS1-24:proposal",))
        self.assertEqual(record.record_key, "FS1-24:cah1")

    def test_action_adapter_requires_registered_proposal_locators(self) -> None:
        pages = ("FS2-24\nCommittee Action: Disapproved\n",)
        adapter = IccCommitteeActionPdfAdapter(
            stage=IccActionStage(
                record_kind=DevelopmentRecordKind.COMMITTEE_ACTION,
                record_key_suffix="cah1",
                parent_key_suffix="proposal",
                sequence=2,
            ),
            affected_locators_by_proposal={},
            page_text_extractor=lambda _: pages,
        )
        result = run_evidence_adapter(adapter, _source("icc:cah1", ACTION_BYTES), ACTION_BYTES)

        self.assertEqual(result.records, ())
        self.assertEqual(
            result.diagnostics[0].code,
            "unresolved-development-proposal-locators",
        )

    def test_proposal_and_action_records_form_one_lineage(self) -> None:
        proposal_pages = (
            "FS1-24\nIBC: 703.2.1\nProponent: Example Proponent\n",
        )
        action_pages = (
            "FS1-24\nCommittee Action: As Submitted\nCommittee Reason: Example.\n",
        )
        proposal_result = run_evidence_adapter(
            IccProposalMonographPdfAdapter(page_text_extractor=lambda _: proposal_pages),
            _source("icc:proposal", PROPOSAL_BYTES),
            PROPOSAL_BYTES,
        )
        action_result = run_evidence_adapter(
            IccCommitteeActionPdfAdapter(
                stage=IccActionStage(
                    record_kind=DevelopmentRecordKind.COMMITTEE_ACTION,
                    record_key_suffix="cah1",
                    parent_key_suffix="proposal",
                    sequence=2,
                ),
                affected_locators_by_proposal={"FS1-24": ("703.2.1",)},
                page_text_extractor=lambda _: action_pages,
            ),
            _source("icc:cah1", ACTION_BYTES),
            ACTION_BYTES,
        )

        lineage = DevelopmentLineage(proposal_result.records + action_result.records)
        self.assertEqual(
            lineage.controlling_record("FS1-24").disposition,
            DevelopmentDisposition.APPROVED,
        )


if __name__ == "__main__":
    unittest.main()
