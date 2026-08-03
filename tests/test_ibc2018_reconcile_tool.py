from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "reconcile_ibc_2018_references.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ibc_reconcile_tool", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load reconciliation tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReconcileToolTests(unittest.TestCase):
    def test_reconcile_corpus_updates_inventory_summary_and_coverage(self) -> None:
        module = load_tool()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "ibc-2018-cross-reference-inventory.json": [
                    {"id": "r1", "target_kind": "section", "raw_target": "2702", "resolved_target": None, "resolution_state": "unresolved", "resolution_notes": None, "source_section": "403.4"}
                ],
                "ibc-2018-table-inventory.json": [{"section_context": "2702.1"}],
                "ibc-2018-figure-inventory.json": [],
                "ibc-2018-equation-inventory.json": [],
                "ibc-2018-exception-inventory.json": [],
                "ibc-2018-cross-reference-summary.json": {},
                "ibc-2018-coverage-report.json": {"internal_reference_resolution": {}},
            }
            for name, payload in payloads.items():
                (root / name).write_text(json.dumps(payload), encoding="utf-8")
            report = module.reconcile_corpus(root)
            records = json.loads((root / "ibc-2018-cross-reference-inventory.json").read_text())
            summary = json.loads((root / "ibc-2018-cross-reference-summary.json").read_text())
            coverage = json.loads((root / "ibc-2018-coverage-report.json").read_text())
            self.assertEqual(records[0]["resolution_state"], "resolved")
            self.assertEqual(summary["resolution_counts"], {"resolved": 1})
            self.assertEqual(coverage["internal_reference_resolution"], {"resolved": 1})
            self.assertEqual(report["changed_record_count"], 1)


if __name__ == "__main__":
    unittest.main()
