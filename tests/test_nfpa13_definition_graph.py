from __future__ import annotations

from copy import deepcopy
import unittest

from building_code_ast.nfpa13_definition_graph import project_nfpa13_definitions


class NFPA13DefinitionGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definitions = [
            {
                "locator": "3.3.1#definition",
                "scope_locator": "3.3.1",
                "term_key": "term:alpha",
                "evidence": {"start": 10, "end": 25, "text": "Synthetic alpha"},
            },
            {
                "locator": "3.3.2#definition",
                "scope_locator": "3.3.2",
                "term_key": "term:beta",
                "evidence": {"start": 30, "end": 44, "text": "Synthetic beta"},
            },
        ]
        self.uses = [
            {
                "source_locator": "5.1#p1",
                "term_key": "term:alpha",
                "candidate_definition_locators": ["3.3.1#definition"],
                "evidence": {"start": 100, "end": 105, "text": "alpha"},
            },
            {
                "source_locator": "5.2#p1",
                "term_key": "term:beta",
                "candidate_definition_locators": [],
                "evidence": {"start": 110, "end": 114, "text": "beta"},
            },
            {
                "source_locator": "5.3#p1",
                "term_key": "term:alpha",
                "candidate_definition_locators": [
                    "3.3.1#definition",
                    "3.3.2#definition",
                ],
                "evidence": {"start": 120, "end": 125, "text": "alpha"},
            },
        ]

    def project(self, definitions=None, uses=None):
        return project_nfpa13_definitions(
            self.definitions if definitions is None else definitions,
            self.uses if uses is None else uses,
        )

    def test_projection_is_deterministic_and_order_independent(self) -> None:
        forward = self.project()
        reverse = self.project(list(reversed(self.definitions)), list(reversed(self.uses)))
        self.assertEqual(forward, reverse)
        self.assertEqual("nfpa13-definition-graph/0.1.0", forward["schema"])
        self.assertEqual(
            {"artifact_id": "nfpa:13", "edition_id": "2019"},
            forward["publication"],
        )

    def test_resolution_states_are_explicit(self) -> None:
        graph = self.project()
        states = {edge["source_locator"]: edge["resolution_state"] for edge in graph["uses"]}
        self.assertEqual("resolved", states["5.1#p1"])
        self.assertEqual("unresolved", states["5.2#p1"])
        self.assertEqual("ambiguous", states["5.3#p1"])

    def test_definition_scope_and_candidates_are_preserved(self) -> None:
        graph = self.project()
        definition = next(item for item in graph["definitions"] if item["locator"] == "3.3.1#definition")
        self.assertEqual("3.3.1", definition["scope_locator"])
        ambiguous = next(item for item in graph["uses"] if item["source_locator"] == "5.3#p1")
        self.assertEqual(
            ["3.3.1#definition", "3.3.2#definition"],
            ambiguous["candidate_definition_locators"],
        )

    def test_public_projection_keeps_coordinates_but_not_source_text(self) -> None:
        graph = self.project()
        self.assertNotIn("Synthetic alpha", repr(graph))
        self.assertNotIn("Synthetic beta", repr(graph))
        definition = next(item for item in graph["definitions"] if item["locator"] == "3.3.1#definition")
        self.assertEqual({"start": 10, "end": 25}, definition["evidence_span"])

    def test_duplicate_definition_locator_fails_closed(self) -> None:
        duplicate = deepcopy(self.definitions)
        duplicate.append(deepcopy(self.definitions[0]))
        with self.assertRaisesRegex(ValueError, "duplicate definition locator"):
            self.project(definitions=duplicate)

    def test_unknown_candidate_definition_fails_closed(self) -> None:
        uses = deepcopy(self.uses)
        uses[0]["candidate_definition_locators"] = ["3.3.999#definition"]
        with self.assertRaisesRegex(ValueError, "unknown definition locator"):
            self.project(uses=uses)

    def test_definition_use_cycles_are_representable(self) -> None:
        uses = [
            {
                "source_locator": "3.3.1#definition",
                "term_key": "term:beta",
                "candidate_definition_locators": ["3.3.2#definition"],
                "evidence": None,
            },
            {
                "source_locator": "3.3.2#definition",
                "term_key": "term:alpha",
                "candidate_definition_locators": ["3.3.1#definition"],
                "evidence": None,
            },
        ]
        graph = self.project(uses=uses)
        self.assertEqual(2, len(graph["uses"]))
        self.assertEqual([], graph["diagnostics"])


if __name__ == "__main__":
    unittest.main()
