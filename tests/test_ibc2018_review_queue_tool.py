from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "prioritize_ibc_2018_review_queue.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ibc_review_queue_tool", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load review queue tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewQueueToolTests(unittest.TestCase):
    def test_prioritize_corpus_writes_queue_summary_and_semantic_packet(self) -> None:
        module = load_tool()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "ibc-2018-review-queue.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["reason", "record_id", "record_type", "review_state"])
                writer.writeheader()
                writer.writerow({"reason": "generic", "record_id": "semantic", "record_type": "semantic_pilot_record", "review_state": "provisional"})
                writer.writerow({"reason": "generic", "record_id": "citation", "record_type": "external_citation_occurrence", "review_state": "disputed"})
            (root / "ibc-2018-semantic-pilot.json").write_text(
                json.dumps([
                    {
                        "id": "semantic",
                        "record_type": "semantic_pilot_record",
                        "review_state": "provisional",
                        "chapter": "7",
                        "source_record_id": "table-7",
                        "source_record_type": "table",
                        "structural_verification": {
                            "features": ["dimensional_units", "nearby_exception_relationship"],
                            "qualifications": ["semantic meaning unreviewed"],
                            "semantic_interpretation_verified": False,
                        },
                    }
                ]),
                encoding="utf-8",
            )
            (root / "ibc-2018-external-citation-inventory.json").write_text(
                json.dumps([
                    {
                        "id": "citation",
                        "record_type": "external_citation_occurrence",
                        "review_state": "disputed",
                        "normalized_document_family_id": None,
                        "normalization_reason": "no_unique_family_alias",
                    }
                ]),
                encoding="utf-8",
            )
            (root / "ibc-2018-coverage-report.json").write_text(json.dumps({}), encoding="utf-8")
            (root / "ibc-2018-corpus-manifest.json").write_text(json.dumps({"inventory_files": []}), encoding="utf-8")

            report = module.prioritize_corpus(root)

            with (root / "ibc-2018-review-queue.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            summary = json.loads((root / "ibc-2018-review-summary.json").read_text())
            coverage = json.loads((root / "ibc-2018-coverage-report.json").read_text())
            manifest = json.loads((root / "ibc-2018-corpus-manifest.json").read_text())
            with (root / "ibc-2018-semantic-review-packet.csv").open(newline="", encoding="utf-8") as handle:
                packet = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["record_id"], "semantic")
            self.assertEqual(rows[0]["priority_band"], "P0")
            self.assertEqual(rows[1]["priority_band"], "P1")
            self.assertEqual(summary["priority_counts"], {"P0": 1, "P1": 1})
            self.assertEqual(coverage["review_queue"]["record_count"], 2)
            self.assertIn("ibc-2018-review-summary.json", manifest["inventory_files"])
            self.assertEqual(packet[0]["chapter"], "7")
            self.assertIn("dimensional_units", packet[0]["features"])
            self.assertEqual(report["semantic_pilot_record_count"], 1)


if __name__ == "__main__":
    unittest.main()
