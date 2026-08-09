from __future__ import annotations

from copy import deepcopy
import unittest

from building_code_ast.nfpa13_reference_graph import project_nfpa13_relations


class NFPA13ReferenceGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.relations = [
            {
                "type": "references_clause",
                "source_locator": "4.1",
                "target_locator": "5.2",
                "target_artifact_id": "nfpa:13",
                "target_domain": "internal",
                "resolved": True,
                "evidence": {"start": 10, "end": 21, "text": "Section 5.2"},
            },
            {
                "type": "references_external_standard",
                "source_locator": "5.2",
                "target_locator": "external:astm:a53",
                "target_artifact_id": "standard:ASTM:A53",
                "target_domain": "external_standard",
                "resolved": True,
                "evidence": {"start": 30, "end": 38, "text": "ASTM A53"},
            },
            {
                "type": "references_clause",
                "source_locator": "5.2",
                "target_locator": "300.22",
                "target_artifact_id": None,
                "target_domain": "unspecified_document",
                "resolved": False,
                "evidence": {"start": 45, "end": 59, "text": "Section 300.22"},
            },
            {
                "type": "explains",
                "source_locator": "A.4.1",
                "target_locator": "4.1",
                "target_artifact_id": "nfpa:13",
                "target_domain": "internal",
                "resolved": True,
                "evidence": None,
            },
        ]

    def project(self, relations=None):
        return project_nfpa13_relations(self.relations if relations is None else relations)

    def test_projection_is_deterministic_and_order_independent(self) -> None:
        forward = self.project()
        reverse = self.project(list(reversed(self.relations)))
        self.assertEqual(forward, reverse)
        self.assertEqual("nfpa13-reference-graph/0.1.0", forward["schema"])
        self.assertEqual(
            {"artifact_id": "nfpa:13", "edition_id": "2019"},
            forward["publication"],
        )

    def test_preserves_resolution_domains_without_guessing(self) -> None:
        graph = self.project()
        unresolved = next(edge for edge in graph["edges"] if edge["target_locator"] == "300.22")
        self.assertEqual("unresolved", unresolved["resolution_state"])
        self.assertEqual("unspecified_document", unresolved["target_domain"])
        self.assertIsNone(unresolved["target_artifact_id"])

        external = next(
            edge for edge in graph["edges"] if edge["target_locator"] == "external:astm:a53"
        )
        self.assertEqual("resolved", external["resolution_state"])
        self.assertEqual("standard:ASTM:A53", external["target_artifact_id"])

    def test_public_projection_retains_coordinates_but_not_source_text(self) -> None:
        graph = self.project()
        edge = next(edge for edge in graph["edges"] if edge["source_locator"] == "4.1")
        self.assertEqual({"start": 10, "end": 21}, edge["evidence_span"])
        self.assertNotIn("Section 5.2", repr(graph))
        self.assertNotIn("ASTM A53", repr(graph))

    def test_only_explicit_input_explains_edges_are_projected(self) -> None:
        graph = self.project()
        explains = [edge for edge in graph["edges"] if edge["type"] == "explains"]
        self.assertEqual(1, len(explains))
        self.assertEqual("A.4.1", explains[0]["source_locator"])
        self.assertFalse(any(node["locator"] == "A.5.2" for node in graph["nodes"]))

    def test_cycles_are_representable(self) -> None:
        cycle = [
            {
                "type": "references_clause",
                "source_locator": "4.1",
                "target_locator": "5.2",
                "target_artifact_id": "nfpa:13",
                "target_domain": "internal",
                "resolved": True,
                "evidence": None,
            },
            {
                "type": "references_clause",
                "source_locator": "5.2",
                "target_locator": "4.1",
                "target_artifact_id": "nfpa:13",
                "target_domain": "internal",
                "resolved": True,
                "evidence": None,
            },
        ]
        graph = self.project(cycle)
        self.assertEqual(2, len(graph["edges"]))
        self.assertEqual([], graph["diagnostics"])

    def test_invalid_domain_state_combinations_fail_closed(self) -> None:
        invalid = deepcopy(self.relations)
        invalid[2]["target_artifact_id"] = "nfpa:13"
        with self.assertRaisesRegex(ValueError, "must not name a target artifact"):
            self.project(invalid)

        invalid = deepcopy(self.relations)
        invalid[0]["resolved"] = False
        with self.assertRaisesRegex(ValueError, "internal relation must be resolved"):
            self.project(invalid)


if __name__ == "__main__":
    unittest.main()
