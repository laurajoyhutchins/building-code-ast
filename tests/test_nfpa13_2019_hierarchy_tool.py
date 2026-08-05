from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_nfpa13_2019_hierarchy.py"
SPEC = importlib.util.spec_from_file_location("extract_nfpa13_2019_hierarchy", MODULE_PATH)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)

BOLD = "NewBaskervilleStd-Bold"
BOLD_ITALIC = "NewBaskervilleStd-BoldIt"
ROMAN = "NewBaskervilleStd-Roman"


def line(text: str, bbox: tuple[float, float, float, float], spans: list[tuple[str, str]]) -> object:
    return subject.Line(
        text,
        bbox,
        [{"font": font, "text": value} for font, value in spans],
        0 if bbox[0] < 306 else 1,
    )


class SyntaxTests(unittest.TestCase):
    def test_recognizes_normative_and_annex_locators(self) -> None:
        cases = [
            ("20.15 Column Protection", "20.15", False),
            ("8.6.5.2.1.3 Text", "8.6.5.2.1.3", False),
            ("A.10.2.4.2.1* Explanation", "A.10.2.4.2.1", True),
        ]
        for value, locator, starred in cases:
            with self.subTest(value=value):
                match = subject.CLAUSE_RE.match(value)
                self.assertIsNotNone(match)
                assert match
                self.assertEqual(locator, match.group("locator"))
                self.assertEqual(starred, bool(match.group("star")))

    def test_node_identity_is_deterministic(self) -> None:
        first = subject._node_id("20.15", "section")
        self.assertEqual(first, subject._node_id("20.15", "section"))
        self.assertNotEqual(first, subject._node_id("20.16", "section"))
        self.assertEqual(72, len(first))


class HeadingTests(unittest.TestCase):
    def test_joins_wrapped_heading_without_clause_body(self) -> None:
        lines = [
            line(
                "B.2.1.4 Ability to Predict Expected Performance from Calcula‐",
                (54, 132, 303, 143),
                [(BOLD, "B.2.1.4 Ability to Predict Expected Performance from Calcula‐")],
            ),
            line(
                "ted Performance.   Ability to accurately predict performance",
                (54, 142, 303, 153),
                [(BOLD, "ted Performance."), (ROMAN, "   Ability to accurately predict performance")],
            ),
        ]
        self.assertEqual(
            "Ability to Predict Expected Performance from Calculated Performance",
            subject._heading(lines, 0),
        )

    def test_joins_horizontal_fragments_after_abbreviation(self) -> None:
        lines = [
            line("F.2.7 U.S.", (36, 268, 78, 279), [(BOLD, "F.2.7 U.S. ")]),
            line("Government", (88, 268, 140, 279), [(BOLD, "Government ")]),
            line(
                "Publications.   U.S.",
                (150, 268, 226, 279),
                [(BOLD, "Publications."), (ROMAN, "   U.S.")],
            ),
        ]
        self.assertEqual("U.S. Government Publications", subject._heading(lines, 0))

    def test_ignores_revision_marker(self) -> None:
        lines = [
            line(
                "4.3.6* Extra Hazard (Group 2) (EH2).",
                (36, 70, 285, 81),
                [(BOLD, "4.3.6* Extra Hazard (Group 2) (EH2).")],
            ),
            line("N", (300, 71, 306, 82), [(BOLD_ITALIC, "N")]),
        ]
        self.assertEqual("Extra Hazard (Group 2) (EH2)", subject._heading(lines, 0))


class ValidationTests(unittest.TestCase):
    def test_accepts_valid_annex_correspondence(self) -> None:
        root = {
            "node_id": subject._node_id("document", "document"),
            "type": "document",
            "locator": "document",
            "parent_locator": None,
            "attributes": {},
            "children": [],
        }
        chapter = subject._node("1", "Administration", {"container_kind": "chapter"})
        section = subject._node("1.1", "Scope", {"explicit": "true"})
        annex = subject._node("A", "Explanatory Material", {"container_kind": "annex"})
        annex_section = subject._node(
            "A.1",
            None,
            {"explicit": "true", "annex": "A", "corresponds_to": "1"},
        )
        root["children"] = [chapter, annex]
        chapter["children"] = [section]
        annex["children"] = [annex_section]
        self.assertTrue(subject.validate({"root": root})["passed"])


if __name__ == "__main__":
    unittest.main()
