from __future__ import annotations

import unittest

from building_code_ast.nec.change_history import (
    ChangeType,
    DevelopmentDisposition,
    DevelopmentRecord,
    DevelopmentRecordType,
    DevelopmentStage,
    ExpectationConfidence,
    ExpectedDisposition,
    ObservedChange,
    ReconciliationOutcome,
    SourceLocator,
    SourceManifestEntry,
    project_expected_changes,
    reconcile_changes,
    resolve_nec_reference,
)


_KNOWN = {
    "210",
    "210.8",
    "210.8(A)",
    "210.8(A)(1)",
    "210.8(A)(2)",
    "210.8(A)(3)",
    "210.8(A)(4)",
    "210.8(A)(5)",
    "210.8(B)",
    "210.8(F)",
}


def _source_locator(anchor: str) -> SourceLocator:
    return SourceLocator(source_id="nfpa70-test-records", page=12, anchor=anchor)


def _record(
    record_id: str,
    *,
    chain: str = "gfci-synthetic",
    stage: DevelopmentStage,
    disposition: DevelopmentDisposition,
    affected: tuple[str, ...] = ("210.8(A)(1) through (5)",),
    targets: tuple[str, ...] = ("210.8(A)",),
    changes: tuple[ChangeType, ...] = (ChangeType.MODIFY_TEXT,),
) -> DevelopmentRecord:
    record_type_by_stage = {
        DevelopmentStage.PUBLIC_INPUT: DevelopmentRecordType.PUBLIC_INPUT,
        DevelopmentStage.FIRST_REVISION: DevelopmentRecordType.FIRST_REVISION,
        DevelopmentStage.PUBLIC_COMMENT: DevelopmentRecordType.PUBLIC_COMMENT,
        DevelopmentStage.SECOND_REVISION: DevelopmentRecordType.SECOND_REVISION,
        DevelopmentStage.TECHNICAL_MEETING: DevelopmentRecordType.TECHNICAL_MEETING_MOTION,
        DevelopmentStage.STANDARDS_COUNCIL: DevelopmentRecordType.STANDARDS_COUNCIL_ACTION,
        DevelopmentStage.TIA: DevelopmentRecordType.TIA,
        DevelopmentStage.ERRATUM: DevelopmentRecordType.ERRATUM,
    }
    return DevelopmentRecord(
        record_id=record_id,
        change_chain_id=chain,
        record_type=record_type_by_stage[stage],
        stage=stage,
        disposition=disposition,
        panel="CMP-02",
        affected_references_raw=affected,
        target_references_raw=targets,
        change_types=changes,
        summary="Synthetic project-authored change summary.",
        source_locator=_source_locator(record_id),
    )


class SourceManifestTests(unittest.TestCase):
    def test_manifest_requires_lowercase_sha256_and_serializes_stably(self) -> None:
        entry = SourceManifestEntry(
            source_id="nfpa70-test-records",
            document_type="second_draft_report",
            title="Synthetic source record",
            cycle="2017-to-2020",
            source_url="https://example.test/source.pdf",
            retrieved_at="2026-08-02T13:30:00Z",
            sha256="a" * 64,
            media_type="application/pdf",
            access_scope="private-reference",
            panel="CMP-02",
            page_count=24,
        )

        self.assertEqual(
            entry.to_dict(),
            {
                "source_id": "nfpa70-test-records",
                "document_type": "second_draft_report",
                "title": "Synthetic source record",
                "cycle": "2017-to-2020",
                "source_url": "https://example.test/source.pdf",
                "retrieved_at": "2026-08-02T13:30:00Z",
                "sha256": "a" * 64,
                "media_type": "application/pdf",
                "access_scope": "private-reference",
                "panel": "CMP-02",
                "page_count": 24,
            },
        )

        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            SourceManifestEntry(
                source_id="bad",
                document_type="report",
                title="Bad",
                cycle="2017-to-2020",
                source_url="https://example.test/bad.pdf",
                retrieved_at="2026-08-02T13:30:00Z",
                sha256="A" * 64,
                media_type="application/pdf",
                access_scope="private-reference",
            )


class ReferenceResolutionTests(unittest.TestCase):
    def test_resolves_exact_section_prefix(self) -> None:
        result = resolve_nec_reference("Section 210.8(F)", _KNOWN)

        self.assertEqual(result.resolved_locators, ("210.8(F)",))
        self.assertEqual(result.method, "exact")
        self.assertEqual(result.confidence, 1.0)

    def test_expands_numeric_sibling_range(self) -> None:
        result = resolve_nec_reference("210.8(A)(1) through (5)", _KNOWN)

        self.assertEqual(
            result.resolved_locators,
            tuple(f"210.8(A)({index})" for index in range(1, 6)),
        )
        self.assertEqual(result.method, "sibling-range")

    def test_range_fails_closed_when_one_member_is_missing(self) -> None:
        result = resolve_nec_reference(
            "210.8(A)(1) through (5)",
            _KNOWN - {"210.8(A)(4)"},
        )

        self.assertEqual(result.resolved_locators, ())
        self.assertEqual(result.method, "unresolved")
        self.assertIn("210.8(A)(4)", result.diagnostic or "")

    def test_unsupported_relative_reference_remains_unresolved(self) -> None:
        result = resolve_nec_reference("the exception following the second paragraph", _KNOWN)

        self.assertEqual(result.resolved_locators, ())
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.method, "unresolved")


class ExpectedProjectionTests(unittest.TestCase):
    def test_later_second_revision_overrides_first_revision(self) -> None:
        records = (
            _record(
                "FR-1",
                stage=DevelopmentStage.FIRST_REVISION,
                disposition=DevelopmentDisposition.ACCEPTED,
            ),
            _record(
                "SR-1",
                stage=DevelopmentStage.SECOND_REVISION,
                disposition=DevelopmentDisposition.RETURNED_TO_PRIOR_EDITION,
            ),
        )

        expectation = project_expected_changes(records, _KNOWN)[0]

        self.assertEqual(expectation.controlling_record_id, "SR-1")
        self.assertEqual(expectation.disposition, ExpectedDisposition.NO_CHANGE_EXPECTED)
        self.assertEqual(expectation.change_types, (ChangeType.NO_FINAL_CHANGE,))
        self.assertEqual(expectation.confidence, ExpectationConfidence.MEDIUM)
        self.assertEqual(expectation.supporting_record_ids, ("FR-1", "SR-1"))

    def test_council_issuance_creates_high_confidence_expectation(self) -> None:
        records = (
            _record(
                "SR-2",
                stage=DevelopmentStage.SECOND_REVISION,
                disposition=DevelopmentDisposition.ACCEPTED,
                affected=("210.8",),
                targets=("210.8(F)",),
                changes=(ChangeType.ADD_SUBDIVISION,),
            ),
            _record(
                "SC-2",
                stage=DevelopmentStage.STANDARDS_COUNCIL,
                disposition=DevelopmentDisposition.ISSUED,
                affected=("210.8",),
                targets=("210.8(F)",),
                changes=(ChangeType.ADD_SUBDIVISION,),
            ),
        )

        expectation = project_expected_changes(records, _KNOWN)[0]

        self.assertEqual(expectation.disposition, ExpectedDisposition.CHANGE_EXPECTED)
        self.assertEqual(expectation.confidence, ExpectationConfidence.HIGH)
        self.assertEqual(expectation.from_locators, ("210.8",))
        self.assertEqual(expectation.expected_target_references, ("210.8(F)",))

    def test_unresolved_controlling_reference_lowers_confidence(self) -> None:
        records = (
            _record(
                "SC-3",
                stage=DevelopmentStage.STANDARDS_COUNCIL,
                disposition=DevelopmentDisposition.ISSUED,
                affected=("Table 210.999",),
                targets=("Table 210.999",),
                changes=(ChangeType.CHANGE_TABLE,),
            ),
        )

        expectation = project_expected_changes(records, _KNOWN)[0]

        self.assertEqual(expectation.confidence, ExpectationConfidence.LOW)
        self.assertEqual(expectation.from_locators, ())
        self.assertEqual(expectation.unresolved_references, ("Table 210.999",))

    def test_conflicting_controlling_records_fail_closed(self) -> None:
        records = (
            _record(
                "SR-A",
                stage=DevelopmentStage.SECOND_REVISION,
                disposition=DevelopmentDisposition.ACCEPTED,
            ),
            _record(
                "SR-B",
                stage=DevelopmentStage.SECOND_REVISION,
                disposition=DevelopmentDisposition.REJECTED,
            ),
        )

        with self.assertRaisesRegex(ValueError, "conflicting controlling records"):
            project_expected_changes(records, _KNOWN)


class ReconciliationTests(unittest.TestCase):
    def test_confirms_positive_and_negative_expectations(self) -> None:
        positive = project_expected_changes(
            (
                _record(
                    "SC-positive",
                    chain="positive",
                    stage=DevelopmentStage.STANDARDS_COUNCIL,
                    disposition=DevelopmentDisposition.ISSUED,
                    affected=("210.8",),
                    targets=("210.8(F)",),
                    changes=(ChangeType.ADD_SUBDIVISION,),
                ),
                _record(
                    "SC-negative",
                    chain="negative",
                    stage=DevelopmentStage.STANDARDS_COUNCIL,
                    disposition=DevelopmentDisposition.RETURNED_TO_PRIOR_EDITION,
                    affected=("210.8(B)",),
                    targets=("210.8(B)",),
                ),
            ),
            _KNOWN,
        )
        observed = (
            ObservedChange(
                observed_change_id="obs-1",
                from_locators=("210.8",),
                to_locators=("210.8(F)",),
                change_types=(ChangeType.ADD_SUBDIVISION,),
                summary="Synthetic observed change.",
                alignment_confidence=0.98,
            ),
        )

        reconciliations = reconcile_changes(positive, observed)
        by_expectation = {
            item.expectation_id: item for item in reconciliations if item.expectation_id is not None
        }

        self.assertEqual(
            by_expectation["exp:positive"].outcome,
            ReconciliationOutcome.CONFIRMED,
        )
        self.assertEqual(
            by_expectation["exp:negative"].outcome,
            ReconciliationOutcome.CONFIRMED,
        )

    def test_reports_missing_contradictory_and_unexpected_observations(self) -> None:
        expectations = project_expected_changes(
            (
                _record(
                    "SC-missing",
                    chain="missing",
                    stage=DevelopmentStage.STANDARDS_COUNCIL,
                    disposition=DevelopmentDisposition.ISSUED,
                    affected=("210.8(A)",),
                    targets=("210.8(A)",),
                    changes=(ChangeType.MODIFY_TEXT,),
                ),
                _record(
                    "SC-no-change",
                    chain="no-change",
                    stage=DevelopmentStage.STANDARDS_COUNCIL,
                    disposition=DevelopmentDisposition.REJECTED,
                    affected=("210.8(B)",),
                    targets=("210.8(B)",),
                ),
            ),
            _KNOWN,
        )
        observed = (
            ObservedChange(
                observed_change_id="obs-contradiction",
                from_locators=("210.8(B)",),
                to_locators=("210.8(B)",),
                change_types=(ChangeType.MODIFY_TEXT,),
                summary="Synthetic contradiction.",
                alignment_confidence=0.9,
            ),
            ObservedChange(
                observed_change_id="obs-unexpected",
                from_locators=("210.8(F)",),
                to_locators=("210.8(F)",),
                change_types=(ChangeType.MODIFY_TEXT,),
                summary="Synthetic unexpected change.",
                alignment_confidence=0.8,
            ),
        )

        reconciliations = reconcile_changes(expectations, observed)
        outcomes = {item.outcome for item in reconciliations}

        self.assertIn(ReconciliationOutcome.EXPECTED_NOT_OBSERVED, outcomes)
        self.assertIn(ReconciliationOutcome.CONTRADICTED, outcomes)
        self.assertIn(ReconciliationOutcome.UNEXPECTED_OBSERVED, outcomes)


if __name__ == "__main__":
    unittest.main()
