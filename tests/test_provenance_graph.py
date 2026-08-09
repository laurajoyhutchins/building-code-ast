from __future__ import annotations

import unittest

from building_code_ast.provenance_graph import (
    PROVENANCE_GRAPH_VERSION,
    build_provenance_graph,
    serialize_provenance_graph,
)


PUBLICATION = {"artifact_id": "synthetic:code", "edition_id": "2026"}


def node(key: str, locator: str, **extra: object) -> dict[str, object]:
    return {"key": key, "kind": "section", "locator": locator, **extra}


def edge(record_id: str, source: str, targets: list[str], state: str) -> dict[str, object]:
    return {
        "source_record_id": record_id,
        "type": "references",
        "source_key": source,
        "target_keys": targets,
        "resolution_state": state,
    }


class ProvenanceGraphTests(unittest.TestCase):
    def test_resolved_edge_preserves_source_safe_evidence(self) -> None:
        relationship = edge("r:1", "section:a", ["section:b"], "resolved")
        relationship["evidence"] = {"pdf_page": 7, "start": 12, "end": 18}
        graph = build_provenance_graph(
            publication=PUBLICATION,
            nodes=[node("section:a", "A"), node("section:b", "B")],
            relationships=[relationship],
        )
        self.assertEqual(graph["schema_version"], PROVENANCE_GRAPH_VERSION)
        self.assertEqual(graph["publication"], PUBLICATION)
        self.assertEqual(graph["edges"][0]["resolution_state"], "resolved")
        self.assertEqual(graph["edges"][0]["evidence"], {"end": 18, "pdf_page": 7, "start": 12})
        self.assertEqual(graph["diagnostics"], [])

    def test_preserves_missing_ambiguous_and_external_targets(self) -> None:
        external = node(
            "external:x",
            "external:X",
            kind="external_standard",
            artifact_id="synthetic:external",
            edition_id="2024",
        )
        graph = build_provenance_graph(
            publication=PUBLICATION,
            nodes=[node("section:a", "A"), node("section:b", "B"), node("section:c", "C"), external],
            relationships=[
                edge("r:missing", "section:a", [], "unresolved"),
                edge("r:ambiguous", "section:b", ["section:a", "section:c"], "ambiguous"),
                edge("r:external", "section:c", ["external:x"], "resolved"),
            ],
        )
        self.assertEqual(sorted(item["state"] for item in graph["diagnostics"]), ["ambiguous", "unresolved"])
        external_node = next(item for item in graph["nodes"] if item["key"] == "external:x")
        self.assertEqual(external_node["artifact_id"], "synthetic:external")
        self.assertEqual(external_node["edition_id"], "2024")

    def test_reports_resolved_internal_cycle_without_changing_edge_state(self) -> None:
        graph = build_provenance_graph(
            publication=PUBLICATION,
            nodes=[node("section:a", "A"), node("section:b", "B")],
            relationships=[
                edge("r:1", "section:a", ["section:b"], "resolved"),
                edge("r:2", "section:b", ["section:a"], "resolved"),
            ],
        )
        self.assertEqual([item["resolution_state"] for item in graph["edges"]], ["resolved", "resolved"])
        self.assertEqual(len(graph["cycles"]), 1)
        self.assertEqual(graph["cycles"][0]["state"], "cyclic")
        self.assertIn("cyclic", [item["state"] for item in graph["diagnostics"]])

    def test_identity_and_serialization_ignore_caller_order(self) -> None:
        nodes = [node("section:a", "A"), node("section:b", "B"), node("section:c", "C")]
        relationships = [
            edge("r:1", "section:a", ["section:b"], "resolved"),
            edge("r:2", "section:b", ["section:c"], "resolved"),
        ]
        first = build_provenance_graph(publication=PUBLICATION, nodes=nodes, relationships=relationships)
        second = build_provenance_graph(
            publication={"edition_id": "2026", "artifact_id": "synthetic:code"},
            nodes=reversed(nodes),
            relationships=reversed(relationships),
        )
        self.assertEqual(first, second)
        self.assertEqual(serialize_provenance_graph(first), serialize_provenance_graph(second))

    def test_fails_closed_on_unsafe_evidence_and_invalid_relationship_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "source-safe"):
            build_provenance_graph(
                publication=PUBLICATION,
                nodes=[node("section:a", "A", evidence={"text": "source expression"})],
                relationships=[],
            )
        with self.assertRaisesRegex(ValueError, "duplicate node key"):
            build_provenance_graph(
                publication=PUBLICATION,
                nodes=[node("section:a", "A"), node("section:a", "B")],
                relationships=[],
            )
        with self.assertRaisesRegex(ValueError, "resolution_state"):
            build_provenance_graph(
                publication=PUBLICATION,
                nodes=[node("section:a", "A")],
                relationships=[edge("r:bad", "section:a", [], "resolved")],
            )
        with self.assertRaisesRegex(ValueError, "unknown target node"):
            build_provenance_graph(
                publication=PUBLICATION,
                nodes=[node("section:a", "A")],
                relationships=[edge("r:missing", "section:a", ["section:b"], "resolved")],
            )


if __name__ == "__main__":
    unittest.main()
