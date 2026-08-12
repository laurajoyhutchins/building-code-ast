from __future__ import annotations

import unittest

from building_code_ast.ingest.nds2018_equation_locators import (
    match_nds2018_equation_label,
    normalize_nds2018_equation_locator,
)


class Nds2018EquationLocatorTests(unittest.TestCase):
    def test_accepts_measured_appendix_equation_families(self) -> None:
        for locator in ("A-1", "D-4", "E.2-1", "E.4-1", "F-2", "H-1", "J-4"):
            with self.subTest(locator=locator):
                self.assertEqual(normalize_nds2018_equation_locator(locator), locator)
                self.assertEqual(match_nds2018_equation_label(f"({locator})"), locator)

    def test_preserves_existing_numeric_equation_family(self) -> None:
        self.assertEqual(normalize_nds2018_equation_locator("12.1-1"), "12.1-1")
        self.assertEqual(match_nds2018_equation_label("(12.1-1)"), "12.1-1")

    def test_rejects_inferred_or_reference_like_shapes(self) -> None:
        for value in (
            "I",
            "I-",
            "Appendix D-1",
            "Equation D-1",
            "D.1",
            "O-1",
            "D-1a",
            "D 1",
            "(D-1) trailing prose",
        ):
            with self.subTest(value=value):
                self.assertIsNone(normalize_nds2018_equation_locator(value))


if __name__ == "__main__":
    unittest.main()
