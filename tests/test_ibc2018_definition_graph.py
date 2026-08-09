from __future__ import annotations

import json
from pathlib import Path
import unittest

from building_code_ast.ibc2018_definition_graph import build_ibc2018_definition_graph


def _definition(suffix: str, term: str, *, section: str = "202") -> dict[str, object]:
    return {
        "id": f"ibc2018:definition:{suffix * 24}",
        "record_type": "definition",
        "review_state": "verified",
        "observed_term": term,
        "normalized_term": term.upper(),
        "source_section": section,
        "scope": "code_wide_unless_context_limits",
        "definition_text_sha256": suffix * 64,
        "source_anchor": {
            "pdf_page": 40,
            "printed_page": "13",
            "chapter": "2",
            "appendix": None,
            "bbox": [60.0, 100.0, 300.0, 140.0],
            "line_id": None,
            "observed_text_sha256": suffix * 64,
        },
    }


class Ibc2018DefinitionGraphTests(unittest.TestCase):
    def test_definition_projection_preserves_identity_scope_and_source_safe_evidence(self) -> None:
        record = _definition("a", "Height")
        graph = build_ibc2018_definition_graph([record])

        self.assertEqual(graph["schema_version"], "ibc-definition-graph/0.1.0")
        self.assertEqual(graph["publication_key"], "ibc-2018")
        self.assertEqual(len(graph["definitions"]), 1)
        node = graph["definitions"][0]
        self.assertEqual(node["id"], "ibc-2018:definition:" + "a" * 24)
        self.assertEqual(node["source_record_id"], record["id"])
        self.assertEqual(node["normalized_term"], "HEIGHT")
        self.assertEqual(node["scope"], "code_wide_unless_context_limits")
        self.assertEqual(node["definition_text_sha256"], "a" * 64)
        self.assertEqual(node["source_anchor"], record["source_anchor"])
        self.assertNotIn("definition_text", node)

    def test_definition_uses_preserve_resolved_unresolved_and_ambiguous_states(self) -> None:
        first = _definition("a", "Height")
        second = _definition("b", "Height", section="202.1")
        uses = [
            {
                "source_locator": "503.1",
                "term_key": "HEIGHT",
                "candidate_definition_ids": [first["id"]],
                "review_state": "verified",
            },
            {
                "source_locator": "504.1",
                "term_key": "HEIGHT",
                "candidate_definition_ids": [],
                "review_state": "provisional",
            },
            {
                "source_locator": "505.1",
                "term_key": "HEIGHT",
                "candidate_definition_ids": [first["id"], second["id"]],
                "review_state": "disputed",
            },
        ]

        graph = build_ibc2018_definition_graph([first, second], uses)

        self.assertEqual([use["resolution_state"] for use in graph["uses"]], ["resolved", "unresolved", "ambiguous"])
        self.assertEqual(graph["uses"][0]["target_definition_id"], "ibc-2018:definition:" + "a" * 24)
        self.assertIsNone(graph["uses"][1]["target_definition_id"])
        self.assertIsNone(graph["uses"][2]["target_definition_id"])
        self.assertEqual([item["state"] for item in graph["diagnostics"]], ["unresolved", "ambiguous"])

    def test_serialization_and_cycles_are_deterministic(self) -> None:
        first = _definition("a", "Alpha")
        second = _definition("b", "Beta")
        uses = [
            {
                "source_locator": "202",
                "source_definition_id": first["id"],
                "term_key": "BETA",
                "candidate_definition_ids": [second["id"]],
                "review_state": "verified",
            },
            {
                "source_locator": "202",
                "source_definition_id": second["id"],
                "term_key": "ALPHA",
                "candidate_definition_ids": [first["id"]],
                "review_state": "verified",
            },
        ]

        forward = build_ibc2018_definition_graph([first, second], uses)
        reverse = build_ibc2018_definition_graph([second, first], list(reversed(uses)))

        self.assertEqual(json.dumps(forward, sort_keys=True, separators=(",", ":")), json.dumps(reverse, sort_keys=True, separators=(",", ":")))
        self.assertEqual(forward["cycles"], [[first["id"], second["id"]]])

    def test_unknown_candidates_and_duplicate_definition_ids_fail_closed(self) -> None:
        first = _definition("a", "Height")
        with self.assertRaises(ValueError):
            build_ibc2018_definition_graph([first, dict(first)])

        with self.assertRaises(ValueError):
            build_ibc2018_definition_graph(
                [first],
                [
                    {
                        "source_locator": "503.1",
                        "term_key": "HEIGHT",
                        "candidate_definition_ids": ["ibc2018:definition:" + "f" * 24],
                        "review_state": "provisional",
                    }
                ],
            )

    def test_committed_source_safe_definition_inventory_projects_without_private_text(self) -> None:
        path = Path(__file__).resolve().parents[1] / "corpora" / "ibc-2018" / "ibc-2018-definition-inventory.json"
        records = json.loads(path.read_text(encoding="utf-8"))

        graph = build_ibc2018_definition_graph(records)

        self.assertEqual(len(graph["definitions"]), len(records))
        self.assertEqual(
            {node["source_record_id"] for node in graph["definitions"]},
            {record["id"] for record in records},
        )
        self.assertEqual(graph["uses"], [])
        self.assertEqual(graph["diagnostics"], [])


if __name__ == "__main__":
    unittest.main()
