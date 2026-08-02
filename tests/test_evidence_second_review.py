from __future__ import annotations

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
    publication_state_id,
    run_evidence_adapter,
)
from building_code_ast.evidence.amendments import (
    AmendmentOperation,
    AmendmentSet,
    JurisdictionalAmendmentPatch,
    NormalizedWashingtonWacHtmlAdapter,
    WashingtonWacHtmlAdapter,
)
from building_code_ast.evidence.development import (
    DevelopmentDisposition,
    DevelopmentLineage,
    DevelopmentRecord,
    DevelopmentRecordKind,
    IccDevelopmentTextAdapter,
)
from building_code_ast.evidence.errata import IccErrataPdfAdapter


ROOT = Path(__file__).resolve().parents[1]
BASE_STATE = PublicationIdentity(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    published_on="2020-10-23",
)


def _source(
    content: bytes,
    *,
    role: EvidenceRole,
    media_type: str,
    source_id: str,
    correction_set: str | None = None,
    effective_on: str | None = None,
    jurisdiction: str | None = None,
) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id=source_id,
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="Synthetic second-review source",
        issuing_body="Synthetic Issuing Body",
        evidence_role=role,
        publication=PublicationIdentity(
            publication_family="Synthetic evidence",
            edition="2021",
            correction_set=correction_set,
            published_on="2023-11-15",
            effective_on=effective_on,
        ),
        retrieved_at="2026-08-02T11:00:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type=media_type,
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://example.invalid/evidence",
        jurisdiction=jurisdiction,
    )


def _patch(
    *,
    source_id: str = "wa:synthetic",
    locator: str = "107.2.9",
    operation: AmendmentOperation = AmendmentOperation.ADD,
    replacement_text: str | None = "Synthetic text.",
    scope: str | None = None,
    sequence: int = 1,
    source_anchor: str = "synthetic:1",
) -> JurisdictionalAmendmentPatch:
    return JurisdictionalAmendmentPatch(
        source_id=source_id,
        jurisdiction="US-WA",
        authority="Synthetic Authority",
        base_publication_state_id=publication_state_id(BASE_STATE),
        wac_citation="51-50-0107",
        locator=locator,
        operation=operation,
        effective_from="2024-03-15",
        effective_to=None,
        replacement_text=replacement_text,
        scope=scope,
        sequence=sequence,
        source_anchor=source_anchor,
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


class EvidenceSecondReviewTests(unittest.TestCase):
    def test_scope_payload_is_exclusive_to_scope_operations(self) -> None:
        with self.assertRaisesRegex(ValueError, "scope must be null"):
            _patch(scope="Unexpected scope metadata.")
        with self.assertRaisesRegex(ValueError, "scope must be null"):
            _patch(
                operation=AmendmentOperation.DELETE,
                replacement_text=None,
                scope="Unexpected scope metadata.",
            )

    def test_amendment_order_is_independent_of_input_tuple_order(self) -> None:
        replacement = _patch(
            source_id="wa:replacement",
            locator="403.5.4",
            operation=AmendmentOperation.REPLACE,
            replacement_text="Replacement text.",
            sequence=1,
            source_anchor="replacement:1",
        )
        scope = _patch(
            source_id="wa:scope",
            locator="403.5.4",
            operation=AmendmentOperation.SCOPE,
            replacement_text=None,
            scope="Synthetic scope.",
            sequence=1,
            source_anchor="scope:1",
        )

        forward = tuple(item.patch_id for item in AmendmentSet((replacement, scope)).ordered())
        reversed_order = tuple(item.patch_id for item in AmendmentSet((scope, replacement)).ordered())

        self.assertEqual(forward, reversed_order)

    def test_amendment_set_rejects_duplicate_source_sequence(self) -> None:
        first = _patch(locator="107.2.9", sequence=1, source_anchor="source:1")
        second = _patch(locator="108.1", sequence=1, source_anchor="source:duplicate")

        with self.assertRaisesRegex(ValueError, "source-local sequence"):
            AmendmentSet((first, second))

    def test_top_level_add_resolves_through_its_chapter(self) -> None:
        html = b"""
<html><body><section>
<h3>WAC 51-50-1207</h3>
<p>Section 1207 is added.</p>
<p>Synthetic added top-level section.</p>
</section></body></html>
"""
        adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            effective_from="2024-03-15",
            known_base_locators=frozenset({"12"}),
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                source_id="wa:top-level-add",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].locator, "1207")
        self.assertEqual(result.records[0].operation, AmendmentOperation.ADD)
        self.assertEqual(result.diagnostics, ())

    def test_normalized_adapter_preserves_source_candidate_sequence(self) -> None:
        html = b"""
<html><body>
<section><h3>WAC 51-50-0107</h3><p>Section 107.2 is clarified.</p></section>
<section><h3>WAC 51-50-0108</h3><p>Section 108.1 is added.</p><p>Added text.</p></section>
</body></html>
"""
        adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            effective_from="2024-03-15",
            known_base_locators=frozenset({"108"}),
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                source_id="wa:normalized-sequence",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].sequence, 2)

    def test_official_adapter_preserves_section_candidate_sequence(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0107</h3><p>107.2.9 Added text.</p>
<h3>PDF WAC 51-50-0403</h3><p>403.5.4 Replacement text.</p>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"107.2", "403.5.4"}),
            effective_dates_by_wac={"51-50-0403": "2024-03-16"},
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                source_id="wa:official-sequence",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].sequence, 2)

    def test_official_adapter_accepts_locator_specific_effective_dates(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0403</h3>
<p>403.4.8.3 First replacement.</p>
<p>403.5.4 Second replacement.</p>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"403.4.8.3", "403.5.4"}),
            effective_dates_by_wac={"51-50-0403": "2024-03-15"},
            effective_dates_by_locator={"403.5.4": "2024-03-16"},
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                source_id="wa:locator-dates",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(
            tuple(item.effective_from for item in result.records),
            ("2024-03-15", "2024-03-16"),
        )

    def test_official_adapter_preserves_space_for_self_closing_breaks(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0107</h3>
<p>107.2.9 First phrase<br/>second phrase.</p>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"107.2"}),
            effective_dates_by_wac={"51-50-0107": "2024-03-15"},
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                source_id="wa:self-closing-break",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertIn("First phrase second phrase", result.records[0].replacement_text)

    def test_lineage_rejects_backward_same_proposal_parent_sequence(self) -> None:
        proposal = _development_record(
            key="G1-24:proposal",
            kind=DevelopmentRecordKind.PROPOSAL,
            sequence=1,
            parents=(),
        )
        committee = _development_record(
            key="G1-24:committee",
            kind=DevelopmentRecordKind.COMMITTEE_ACTION,
            sequence=3,
            parents=(proposal.record_key,),
        )
        final = _development_record(
            key="G1-24:final",
            kind=DevelopmentRecordKind.FINAL_ACTION,
            sequence=2,
            parents=(committee.record_key,),
        )

        with self.assertRaisesRegex(ValueError, "parent sequence"):
            DevelopmentLineage((proposal, committee, final))

    def test_development_adapter_does_not_bridge_unsupported_actions(self) -> None:
        pdf_bytes = b"synthetic development bytes"
        pages = (
            """G1-24
Proponent: Synthetic Proponent
Affected: 107.2
Proposal: Synthetic proposal.
Committee Action: Reconsidered with conditions
Final Action: Approved
""",
        )
        adapter = IccDevelopmentTextAdapter(page_text_extractor=lambda _: pages)
        result = run_evidence_adapter(
            adapter,
            _source(
                pdf_bytes,
                role=EvidenceRole.DEVELOPMENT_HISTORY,
                media_type="application/pdf",
                source_id="icc:unsupported-chain",
            ),
            pdf_bytes,
        )

        self.assertEqual(
            tuple(item.kind for item in result.records),
            (DevelopmentRecordKind.PROPOSAL,),
        )
        self.assertIn("unsupported-development-action", {item.code for item in result.diagnostics})

    def test_errata_preserves_source_candidate_sequence(self) -> None:
        pdf_bytes = b"synthetic errata bytes"
        pages = (
            """Page 1-1, Section 101.1 wording adjusted for consistency.
Page 1-2, Section 101.2 now reads . . .
Synthetic replacement.
""",
        )
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            applies_to_printings=("first-printing",),
            page_text_extractor=lambda _: pages,
        )
        result = run_evidence_adapter(
            adapter,
            _source(
                pdf_bytes,
                role=EvidenceRole.OFFICIAL_CORRECTION,
                media_type="application/pdf",
                source_id="icc:errata-sequence",
                correction_set="synthetic-corrections",
            ),
            pdf_bytes,
        )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].sequence, 2)
        self.assertEqual(result.records[0].source_anchor, "errata:2")

    def test_amendment_schema_prohibits_scope_on_non_scope_operations(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/jurisdictional-amendment-patch.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(
            any(
                rule.get("if", {}).get("properties", {}).get("operation", {}).get("const")
                == "scope"
                and rule.get("else", {}).get("properties", {}).get("scope", {}).get("type")
                == "null"
                for rule in schema["allOf"]
            )
        )


if __name__ == "__main__":
    unittest.main()
