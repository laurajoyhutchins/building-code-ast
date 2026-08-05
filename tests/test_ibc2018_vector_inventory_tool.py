from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from building_code_ast.ibc2018_corpus import SOURCE_PAGE_COUNT, SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_ibc_2018_vector_inventory.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ibc_vector_inventory_tool", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load vector inventory tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VectorInventoryToolTests(unittest.TestCase):
    def test_write_artifacts_emits_source_safe_inventory_and_summary(self) -> None:
        module = load_tool()
        evidence = {
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 32_608_171,
            "source_page_count": SOURCE_PAGE_COUNT,
            "pages": [
                {
                    "pdf_page": page,
                    "regions": [
                        {
                            "pdf_page": page,
                            "bbox": [100.0, 100.0, 250.0, 240.0],
                            "drawing_count": 2,
                            "line_count": 2,
                            "curve_count": 6,
                            "rect_count": 0,
                            "fill_count": 1,
                            "stroke_count": 1,
                            "geometry_fingerprint": "d" * 64,
                        }
                    ] if page == 100 else [],
                }
                for page in range(1, SOURCE_PAGE_COUNT + 1)
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            records, summary = module.write_artifacts(output, evidence, figures=())
            self.assertEqual(len(records), 1)
            self.assertEqual(summary["record_count"], 1)
            payload = json.loads((output / "ibc-2018-vector-region-inventory.json").read_text())
            self.assertEqual(payload, records)
            self.assertNotIn('"observed_text":', (output / "ibc-2018-vector-region-inventory.json").read_text())
            self.assertTrue((output / "ibc-2018-vector-region-inventory.csv").is_file())
            self.assertTrue((output / "ibc-2018-vector-region-summary.json").is_file())

    def test_update_corpus_metadata_adds_counts_and_review_rows(self) -> None:
        module = load_tool()
        records = [
            {
                "id": "ibc2018:vector-region:" + "e" * 24,
                "record_type": "vector_graphic_region_detection",
                "review_state": "disputed",
                "disposition": "candidate_vector_region_unclassified",
                "chapter": "4",
                "appendix": None,
                "source_anchor": {"pdf_page": 100},
            }
        ]
        summary = {
            "record_count": 1,
            "page_count_with_regions": 1,
            "disposition_counts": {"candidate_vector_region_unclassified": 1},
            "review_state_counts": {"disputed": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "ibc-2018-corpus-manifest.json").write_text(json.dumps({
                "expected_artifact_counts": {},
                "known_limitations": ["vector-only drawing regions remain an explicit review backlog"],
                "inventory_files": [],
            }))
            (output / "ibc-2018-coverage-report.json").write_text(json.dumps({
                "counts": {},
                "counts_by_context": {},
                "known_limitations": ["vector-only drawing regions remain an explicit review backlog"],
            }))
            (output / "ibc-2018-review-queue.csv").write_text(
                "reason,record_id,record_type,review_state\nexisting,ibc2018:table:" + "f" * 24 + ",table,provisional\n"
            )
            module.update_corpus_metadata(output, records, summary)
            manifest = json.loads((output / "ibc-2018-corpus-manifest.json").read_text())
            coverage = json.loads((output / "ibc-2018-coverage-report.json").read_text())
            queue = (output / "ibc-2018-review-queue.csv").read_text().splitlines()
            self.assertEqual(manifest["expected_artifact_counts"]["vector_regions"]["value"], 1)
            self.assertEqual(coverage["counts"]["vector_regions"], 1)
            self.assertEqual(coverage["counts_by_context"]["vector_regions"], {"chapter:4": 1})
            self.assertEqual(len(queue), 3)
            self.assertTrue(any("completed vector-path scan" in item for item in coverage["known_limitations"]))



if __name__ == "__main__":
    unittest.main()
