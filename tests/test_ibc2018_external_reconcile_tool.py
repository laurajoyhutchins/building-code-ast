from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "reconcile_ibc_2018_external_references.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ibc_external_reconcile_tool", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load external reconciliation tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExternalReconcileToolTests(unittest.TestCase):
    def test_reconcile_corpus_updates_inventory_crosschecks_and_coverage(self) -> None:
        module = load_tool()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            families = [
                {
                    "id": "family-7",
                    "issuing_organization": "ASCE/SEI",
                    "document_family": "7",
                    "observed_designations": ["7—16"],
                },
                {
                    "id": "family-24",
                    "issuing_organization": "ASCE/SEI",
                    "document_family": "24",
                    "observed_designations": ["24—14"],
                },
            ]
            citations = [
                {
                    "id": "citation-7",
                    "issuing_organization": "ASCE",
                    "observed_designation": "7",
                    "normalized_document_family_id": None,
                    "normalization_confidence": 0.45,
                    "review_state": "disputed",
                },
                {
                    "id": "citation-unknown",
                    "issuing_organization": "ASCE",
                    "observed_designation": "99",
                    "normalized_document_family_id": None,
                    "normalization_confidence": 0.45,
                    "review_state": "disputed",
                },
            ]
            payloads = {
                "ibc-2018-external-reference-inventory.json": families,
                "ibc-2018-external-citation-inventory.json": citations,
                "ibc-2018-reference-crosschecks.json": {
                    "chapter35_families_not_detected_elsewhere": ["family-7", "family-24"],
                    "citation_occurrences_without_chapter35_match": ["citation-7", "citation-unknown"],
                    "designation_or_edition_mismatches": [],
                    "duplicate_or_alias_families": [],
                    "unresolved_organizations_or_titles": [],
                },
                "ibc-2018-coverage-report.json": {
                    "chapter35": {"families_not_detected_elsewhere_count": 2},
                    "external_references": {
                        "citation_occurrence_count": 2,
                        "matched_family_count": 0,
                        "unmatched_occurrence_count": 2,
                    },
                },
            }
            for name, payload in payloads.items():
                (root / name).write_text(json.dumps(payload), encoding="utf-8")

            report = module.reconcile_corpus(root)

            records = json.loads((root / "ibc-2018-external-citation-inventory.json").read_text())
            crosschecks = json.loads((root / "ibc-2018-reference-crosschecks.json").read_text())
            coverage = json.loads((root / "ibc-2018-coverage-report.json").read_text())
            with (root / "ibc-2018-external-citation-inventory.csv").open(newline="", encoding="utf-8") as handle:
                csv_rows = list(csv.DictReader(handle))

            self.assertEqual(records[0]["normalized_document_family_id"], "family-7")
            self.assertEqual(crosschecks["chapter35_families_not_detected_elsewhere"], ["family-24"])
            self.assertEqual(crosschecks["citation_occurrences_without_chapter35_match"], ["citation-unknown"])
            self.assertEqual(coverage["chapter35"]["families_not_detected_elsewhere_count"], 1)
            self.assertEqual(coverage["external_references"]["matched_family_count"], 1)
            self.assertEqual(coverage["external_references"]["unmatched_occurrence_count"], 1)
            self.assertEqual(coverage["external_references"]["newly_alias_matched_occurrence_count"], 1)
            self.assertEqual(len(csv_rows), 2)
            self.assertEqual(report["newly_matched_count"], 1)


if __name__ == "__main__":
    unittest.main()
