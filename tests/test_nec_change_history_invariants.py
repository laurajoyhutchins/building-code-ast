from __future__ import annotations

import unittest

from building_code_ast.nec.change_history import resolve_nec_reference


class ChangeHistoryReferenceInvariantTests(unittest.TestCase):
    def test_resolves_alphabetic_sibling_range(self) -> None:
        known = {
            "210.8(A)",
            "210.8(B)",
            "210.8(C)",
            "210.8(D)",
            "210.8(E)",
            "210.8(F)",
        }

        result = resolve_nec_reference("210.8(A) through (F)", known)

        self.assertEqual(
            result.resolved_locators,
            tuple(f"210.8({letter})" for letter in "ABCDEF"),
        )
        self.assertEqual(result.method, "sibling-range")
        self.assertEqual(result.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
