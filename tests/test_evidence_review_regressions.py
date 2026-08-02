from __future__ import annotations

import hashlib
import unittest

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    publication_state_id,
    run_evidence_adapter,
)
from building_code_ast.evidence.amendments import (
    AmendmentOperation,
    NormalizedWashingtonWacHtmlAdapter,
    WashingtonWacHtmlAdapter,
)
from building_code_ast.evidence.development import (
    DevelopmentDisposition,
    DevelopmentLineage,
    DevelopmentRecord,
    DevelopmentRecordKind,
)


BASE_STATE = PublicationIdentity(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    published_on="2020-10-23",
)


def _development_record(
    *,
    key: str,
    kind: DevelopmentRecordKind,
    sequence: int,
    parents: tuple[str, ...],
) -> DevelopmentRecord:
    return DevelopmentRecord(
        source_id="icc:synthetic:development",
        proposal_id="G1-24",
        record_key=key,
        kind=kind,
        disposition=(
            DevelopmentDisposition.SUBMITTED
            if kind is DevelopmentRecordKind.PROPOSAL
            else DevelopmentDisposition.APPROVED
        ),
        sequence=sequence,
        proponent="Synthetic Proponent" if kind is DevelopmentRecordKind.PROPOSAL else None,
        affected_locators=("107.2",),
        parent_keys=parents,
        action_date=None,
        summary="Synthetic process evidence.",
        source_page=1,
        source_anchor=key,
    )


def _source(content: bytes) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id="wa:wac:51-50:synthetic-review",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="Synthetic official-style Washington WAC HTML",
        issuing_body="Washington State Building Code Council",
        evidence_role=EvidenceRole.JURISDICTIONAL_LAW,
        publication=PublicationIdentity(
            publication_family="WAC 51-50",
            edition="2021 IBC adoption",
            digital_revision="synthetic-review",
            published_on="2023-11-15",
        ),
        retrieved_at="2026-08-02T10:30:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type="text/html",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://example.invalid/wac-51-50",
        jurisdiction="US-WA",
    )


class EvidenceReviewRegressionTests(unittest.TestCase):
    def test_development_lineage_rejects_parent_cycles(self) -> None:
        proposal = _development_record(
            key="G1-24:proposal",
            kind=DevelopmentRecordKind.PROPOSAL,
            sequence=1,
            parents=(),
        )
        committee = _development_record(
            key="G1-24:committee-action",
            kind=DevelopmentRecordKind.COMMITTEE_ACTION,
            sequence=2,
            parents=("G1-24:final-action",),
        )
        final = _development_record(
            key="G1-24:final-action",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            sequence=3,
            parents=("G1-24:committee-action",),
        )

        with self.assertRaisesRegex(ValueError, "cycle"):
            DevelopmentLineage(records=(proposal, committee, final))

    def test_development_lineage_requires_one_proposal_root_and_parented_actions(self) -> None:
        action = _development_record(
            key="G1-24:final-action",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            sequence=2,
            parents=(),
        )
        with self.assertRaisesRegex(ValueError, "proposal record"):
            DevelopmentLineage(records=(action,))

        proposal = _development_record(
            key="G1-24:proposal",
            kind=DevelopmentRecordKind.PROPOSAL,
            sequence=1,
            parents=(),
        )
        with self.assertRaisesRegex(ValueError, "parent"):
            DevelopmentLineage(records=(proposal, action))

    def test_normalized_add_resolves_against_existing_parent_locator(self) -> None:
        html = b"""
<html><body>
<section>
  <h3>WAC 51-50-0107</h3>
  <p>Section 107.2.9 is added.</p>
  <p>Synthetic new subsection text.</p>
</section>
</body></html>
"""
        adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            effective_from="2024-03-15",
            known_base_locators=frozenset({"107.2"}),
        )

        result = run_evidence_adapter(adapter, _source(html), html)

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].operation, AmendmentOperation.ADD)
        self.assertEqual(result.records[0].locator, "107.2.9")
        self.assertEqual(result.diagnostics, ())

    def test_official_wac_html_extracts_add_replace_and_reserved_sections(self) -> None:
        html = b"""
<html><body>
<h3><a>PDF</a> WAC 51-50-0107</h3>
<h3>Section 107—Construction documents.</h3>
<p>107.2.9 Synthetic new subsection.</p>
<p>1. Synthetic list item.</p>
<p>[Statutory Authority: synthetic history.]</p>
<hr>
<h3>PDF WAC 51-50-0403</h3>
<h3>Section 403—High-rise buildings.</h3>
<p>403.4.8.3 Synthetic replacement subsection.</p>
<p>[Statutory Authority: synthetic history.]</p>
<hr>
<h3>PDF WAC 51-50-0110</h3>
<h3>Reserved.</h3>
<p>[Statutory Authority: synthetic history.]</p>
</body></html>
"""
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"107.2", "403.4.8.3", "110"}),
            effective_dates_by_wac={
                "51-50-0107": "2024-03-15",
                "51-50-0403": "2024-03-16",
                "51-50-0110": "2024-03-15",
            },
            reserved_locators_by_wac={"51-50-0110": "110"},
        )

        result = run_evidence_adapter(adapter, _source(html), html)

        self.assertEqual(
            tuple(record.operation for record in result.records),
            (
                AmendmentOperation.ADD,
                AmendmentOperation.REPLACE,
                AmendmentOperation.RESERVE,
            ),
        )
        self.assertEqual(
            tuple(record.locator for record in result.records),
            ("107.2.9", "403.4.8.3", "110"),
        )
        self.assertEqual(
            tuple(record.effective_from for record in result.records),
            ("2024-03-15", "2024-03-16", "2024-03-15"),
        )
        self.assertEqual(result.records[0].source_anchor, "wac:51-50-0107:107.2.9")
        self.assertEqual(result.diagnostics, ())


if __name__ == "__main__":
    unittest.main()
