from __future__ import annotations

import unittest

from building_code_ast.nec.change_history import (
    ChangeType,
    DevelopmentDisposition,
    DevelopmentRecord,
    DevelopmentRecordType,
    DevelopmentStage,
    SourceLocator,
    resolve_nec_reference,
)


class ChangeHistoryInvariantTests(unittest.TestCase):
    def test_development_record_type_must_match_stage(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match stage"):
            DevelopmentRecord(
                record_id="bad-stage-type",
                change_chain_id="synthetic-chain",
                record_type=DevelopmentRecordType.PUBLIC_INPUT,
                stage=DevelopmentStage.STANDARDS_COUNCIL,
                disposition=DevelopmentDisposition.ISSUED,
                panel="CMP-02",
                affected_references_raw=("210.8",),
                target_references_raw=("210.8(F)",),
                change_types=(ChangeType.ADD_SUBDIVISION,),
                summary="Synthetic invalid record.",
                source_locator=SourceLocator(
                    source_id="synthetic-source",
                    page=1,
                    anchor="bad-stage-type",
                ),
            )

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
