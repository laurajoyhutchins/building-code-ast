from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.ibc2018_reference_graph import build_ibc2018_reference_graph


class Ibc2018ReferenceGraphTests(unittest.TestCase):
    def test_resolved_reference_links_section_nodes_and_preserves_evidence(self) -> None:
        anchor = {
            "pdf_page": 42,
            "printed_page": "27",
            "chapter": "4",
            "appendix": None,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "line_id": "line-1",
            "observed_text_sha256": "a" * 64,
        }
        graph = build_ibc2018_reference_graph(
            [
                {
                    "id": "ibc2018:internal-cross-reference:" + "1" * 24,
                    "record_type": "internal_cross_reference",
                    "review_state": "verified",
                    "source_section": "2702.1",
                    "target_kind": "section",
                    "raw_target": "403.4",
                    "resolved_target": "403.4",
                    "resolution_state": "resolved",
                    "resolution_reason": "exact_section_target",
                    "source_anchor": anchor,
                }
            ]
        )

        self.assertEqual(graph["schema_version"], "ibc-reference-graph/0.1.0")
        self.assertEqual(graph["publication_key"], "ibc-2018")
        self.assertEqual(
            [node["locator"] for node in graph["nodes"]],
            ["2702.1", "403.4"],
        )
        edge = graph["edges"][0]
        self.assertEqual(edge["source"], "ibc-2018:section:2702.1")
        self.assertEqual(edge["target"], "ibc-2018:section:403.4")
        self.assertEqual(edge["source_record_id"], "ibc2018:internal-cross-reference:" + "1" * 24)
        self.assertEqual(edge["source_anchor"], anchor)
        self.assertNotIn("text", edge)
        self.assertEqual(graph["diagnostics"], [])

    def test_unresolved_and_ambiguous_references_remain_visible(self) -> None:
        records = [
            {
                "id": "ibc2018:internal-cross-reference:" + "2" * 24,
                "record_type": "internal_cross_reference",
                "review_state": "provisional",
                "source_section": "101.2",
                "target_kind": "section",
                "raw_target": "9999.1",
                "resolved_target": None,
                "resolution_state": "unresolved",
                "resolution_reason": "section_target_not_indexed",
            },
            {
                "id": "ibc2018:internal-cross-reference:" + "3" * 24,
                "record_type": "internal_cross_reference",
                "review_state": "disputed",
                "source_section": "102.3",
                "target_kind": "section",
                "raw_target": "11.4",
                "resolved_target": None,
                "resolution_state": "ambiguous",
                "resolution_reason": "preserved_contextual_ambiguity",
            },
        ]

        graph = build_ibc2018_reference_graph(records)

        self.assertTrue(all(edge["target"] is None for edge in graph["edges"]))
        self.assertEqual(
            [diagnostic["state"] for diagnostic in graph["diagnostics"]],
            ["unresolved", "ambiguous"],
        )
        self.assertEqual(
            [diagnostic["raw_target"] for diagnostic in graph["diagnostics"]],
            ["9999.1", "11.4"],
        )

    def test_graph_serialization_is_deterministic_independent_of_record_order(self) -> None:
        records = [
            {
                "id": "ibc2018:internal-cross-reference:" + "4" * 24,
                "record_type": "internal_cross_reference",
                "review_state": "verified",
                "source_section": "1406.10",
                "target_kind": "section",
                "raw_target": "1406.11",
                "resolved_target": "1406.11",
                "resolution_state": "resolved",
                "resolution_reason": "preserved_resolved_target",
            },
            {
                "id": "ibc2018:internal-cross-reference:" + "5" * 24,
                "record_type": "internal_cross_reference",
                "review_state": "verified",
                "source_section": "1406.11",
                "target_kind": "section",
                "raw_target": "1406.10",
                "resolved_target": "1406.10",
                "resolution_state": "resolved",
                "resolution_reason": "preserved_resolved_target",
            },
        ]

        forward = build_ibc2018_reference_graph(records)
        reverse = build_ibc2018_reference_graph(list(reversed(records)))

        self.assertEqual(
            json.dumps(forward, sort_keys=True, separators=(",", ":")),
            json.dumps(reverse, sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual(forward["cycles"], [["1406.10", "1406.11"]])

    def test_non_section_targets_are_preserved_without_manufacturing_nodes(self) -> None:
        graph = build_ibc2018_reference_graph(
            [
                {
                    "id": "ibc2018:internal-cross-reference:" + "6" * 24,
                    "record_type": "internal_cross_reference",
                    "review_state": "verified",
                    "source_section": "2308.6.1",
                    "target_kind": "table",
                    "raw_target": "2308.6",
                    "resolved_target": None,
                    "resolution_state": "nonexistent",
                    "resolution_reason": "target_not_in_inventory",
                }
            ]
        )

        self.assertEqual([node["locator"] for node in graph["nodes"]], ["2308.6.1"])
        self.assertIsNone(graph["edges"][0]["target"])
        self.assertEqual(graph["edges"][0]["target_kind"], "table")
        self.assertEqual(graph["diagnostics"][0]["state"], "nonexistent")

    def test_source_safe_corpus_projects_without_private_source_material(self) -> None:
        corpus_dir = Path(__file__).resolve().parents[1] / "corpora" / "ibc-2018"
        records = json.loads(
            (corpus_dir / "ibc-2018-cross-reference-inventory.json").read_text(encoding="utf-8")
        )
        summary = json.loads(
            (corpus_dir / "ibc-2018-cross-reference-summary.json").read_text(encoding="utf-8")
        )

        graph = build_ibc2018_reference_graph(records)

        self.assertEqual(len(graph["edges"]), len(records))
        cyclic_components = [set(component) for component in graph["cycles"]]
        for source, target in summary["circular_section_reference_pairs"]:
            self.assertTrue(
                any({source, target}.issubset(component) for component in cyclic_components),
                msg=f"missing cyclic component for source-safe pair {source} <-> {target}",
            )


if __name__ == "__main__":
    unittest.main()
