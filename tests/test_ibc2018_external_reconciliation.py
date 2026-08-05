from __future__ import annotations

import copy
import unittest

from building_code_ast.ibc2018_external_reconciliation import (
    build_family_alias_index,
    reconcile_external_citations,
)


class ExternalReferenceReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.families = [
            {
                "id": "family-asce-7",
                "issuing_organization": "ASCE/SEI",
                "document_family": "7",
                "observed_designations": ["7—16"],
            },
            {
                "id": "family-icc-a117",
                "issuing_organization": "ICC",
                "document_family": "ICC A117.1",
                "observed_designations": ["ICC A117.1—09"],
            },
            {
                "id": "family-astm-d226",
                "issuing_organization": "ASTM",
                "document_family": "D226/D226M",
                "observed_designations": ["D226/D226M—09"],
            },
            {
                "id": "family-ansi-z971",
                "issuing_organization": "ANSI",
                "document_family": "Z 97.1",
                "observed_designations": ["Z 97.1—14"],
            },
            {
                "id": "family-asme-a171",
                "issuing_organization": "ASME",
                "document_family": "ASME/A17.1",
                "observed_designations": ["ASME/A17.1—2016/CSA B44—16"],
            },
            {
                "id": "family-cpa-a1356",
                "issuing_organization": "CPA",
                "document_family": "ANSI A135.6",
                "observed_designations": ["ANSI A135.6—2012"],
            },
        ]

    def citation(self, agency: str, designation: str, family_id: str | None = None) -> dict[str, object]:
        return {
            "id": f"citation-{agency}-{designation}",
            "issuing_organization": agency,
            "observed_designation": designation,
            "normalized_document_family_id": family_id,
            "normalization_confidence": 0.9 if family_id else 0.45,
            "review_state": "provisional" if family_id else "disputed",
        }

    def test_alias_index_keeps_ambiguous_aliases_ineligible(self) -> None:
        families = self.families + [
            {
                "id": "family-second-a117",
                "issuing_organization": "ICC",
                "document_family": "A117.1",
                "observed_designations": ["A117.1—10"],
            }
        ]
        index = build_family_alias_index(families)
        self.assertNotIn(("ICC", "A117.1"), index.unique_by_agency)
        self.assertIn(("ICC", "A117.1"), index.ambiguous_by_agency)

    def test_reconciles_only_unique_conservative_aliases(self) -> None:
        citations = [
            self.citation("ASCE", "7"),
            self.citation("ICC", "A117.1"),
            self.citation("ASTM", "D226"),
            self.citation("ASTM", "D226 T"),
            self.citation("ANSI", "Z97.1"),
            self.citation("ASME", "A17.1/CSA B44"),
            self.citation("ANSI", "A135.6"),
            self.citation("CPSC", "16 CFR P"),
        ]
        original = copy.deepcopy(citations)

        reconciled, summary = reconcile_external_citations(citations, self.families)

        self.assertEqual(citations, original)
        by_designation = {item["observed_designation"]: item for item in reconciled}
        self.assertEqual(by_designation["7"]["normalized_document_family_id"], "family-asce-7")
        self.assertEqual(by_designation["7"]["normalization_reason"], "agency_alias_unique")
        self.assertEqual(by_designation["A117.1"]["normalized_document_family_id"], "family-icc-a117")
        self.assertEqual(by_designation["D226"]["normalized_document_family_id"], "family-astm-d226")
        self.assertEqual(by_designation["D226 T"]["normalized_document_family_id"], "family-astm-d226")
        self.assertEqual(by_designation["D226 T"]["normalization_reason"], "trimmed_trailing_capture_artifact")
        self.assertEqual(by_designation["Z97.1"]["normalized_document_family_id"], "family-ansi-z971")
        self.assertEqual(by_designation["A17.1/CSA B44"]["normalized_document_family_id"], "family-asme-a171")
        self.assertEqual(by_designation["A135.6"]["normalized_document_family_id"], "family-cpa-a1356")
        self.assertEqual(by_designation["A135.6"]["normalization_reason"], "unique_designation_alias")
        self.assertIsNone(by_designation["16 CFR P"]["normalized_document_family_id"])
        self.assertEqual(by_designation["16 CFR P"]["normalization_reason"], "no_unique_family_alias")
        self.assertEqual(summary["newly_matched_count"], 7)
        self.assertEqual(summary["unmatched_count"], 1)

    def test_preserves_existing_match_and_records_reason(self) -> None:
        citation = self.citation("NFPA", "70", "family-nfpa-70")
        reconciled, summary = reconcile_external_citations([citation], self.families)
        self.assertEqual(reconciled[0]["normalized_document_family_id"], "family-nfpa-70")
        self.assertEqual(reconciled[0]["normalization_reason"], "preserved_existing_family_match")
        self.assertEqual(summary["preserved_match_count"], 1)

    def test_near_match_is_not_promoted(self) -> None:
        citations = [
            self.citation("ASTM", "D2260"),
            self.citation("CPSC", "16"),
        ]
        families = self.families + [
            {
                "id": "family-nfpa-16",
                "issuing_organization": "NFPA",
                "document_family": "16",
                "observed_designations": ["16—17"],
            }
        ]
        reconciled, summary = reconcile_external_citations(citations, families)
        self.assertTrue(all(item["normalized_document_family_id"] is None for item in reconciled))
        self.assertTrue(all(item["review_state"] == "disputed" for item in reconciled))
        self.assertEqual(summary["newly_matched_count"], 0)


if __name__ == "__main__":
    unittest.main()
