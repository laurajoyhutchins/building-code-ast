from __future__ import annotations

import unittest

from building_code_ast.nec.style_manual import (
    DefinitionPlacement,
    MarkerRole,
    ParallelNumberingPolicy,
    ThirdLevelTitlePolicy,
    informational_note_identity,
    interpret_parenthetical_marker,
    style_profile_for_edition,
)


class NecStyleProfileTests(unittest.TestCase):
    def test_2017_uses_2015_manual_and_allows_article_local_definitions(self) -> None:
        profile = style_profile_for_edition("NFPA 70-2017")

        self.assertEqual(profile.code_edition, 2017)
        self.assertEqual(profile.style_manual_edition, 2015)
        self.assertEqual(
            profile.definition_placement,
            DefinitionPlacement.ARTICLE_100_OR_ARTICLE_LOCAL,
        )
        self.assertEqual(
            profile.parallel_numbering,
            ParallelNumberingPolicy.ENCOURAGED,
        )
        self.assertFalse(profile.article_100_is_subdivided)
        self.assertTrue(profile.informational_note_numbering_is_local)

    def test_2020_and_2023_centralize_definitions_in_article_100(self) -> None:
        profile_2020 = style_profile_for_edition(2020)
        profile_2023 = style_profile_for_edition("nec-2023")

        self.assertEqual(
            profile_2020.definition_placement,
            DefinitionPlacement.ARTICLE_100_ONLY,
        )
        self.assertEqual(
            profile_2023.definition_placement,
            DefinitionPlacement.ARTICLE_100_ONLY,
        )
        self.assertEqual(
            profile_2020.parallel_numbering,
            ParallelNumberingPolicy.ENCOURAGED,
        )
        self.assertEqual(
            profile_2023.parallel_numbering,
            ParallelNumberingPolicy.REQUIRED,
        )

    def test_2023_requires_consistency_when_third_level_titles_are_used(self) -> None:
        self.assertEqual(
            style_profile_for_edition(2017).third_level_title_policy,
            ThirdLevelTitlePolicy.OPTIONAL,
        )
        self.assertEqual(
            style_profile_for_edition(2023).third_level_title_policy,
            ThirdLevelTitlePolicy.OPTIONAL_BUT_SIBLING_CONSISTENT,
        )

    def test_unknown_edition_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported NEC edition"):
            style_profile_for_edition("test-edition")


class ParentheticalMarkerInterpretationTests(unittest.TestCase):
    def test_title_is_strong_structural_evidence(self) -> None:
        interpretation = interpret_parenthetical_marker(
            edition=2017,
            subdivision_level=2,
            has_title=True,
            introduced_as_list=False,
        )

        self.assertEqual(interpretation.role, MarkerRole.SUBDIVISION)
        self.assertEqual(interpretation.confidence, "high")
        self.assertEqual(interpretation.evidence, ("title",))

    def test_list_introduction_is_strong_list_item_evidence(self) -> None:
        interpretation = interpret_parenthetical_marker(
            edition=2023,
            subdivision_level=2,
            has_title=False,
            introduced_as_list=True,
        )

        self.assertEqual(interpretation.role, MarkerRole.LIST_ITEM)
        self.assertEqual(interpretation.confidence, "high")
        self.assertEqual(interpretation.evidence, ("list-introduction",))

    def test_bare_untitled_marker_remains_ambiguous(self) -> None:
        interpretation = interpret_parenthetical_marker(
            edition=2020,
            subdivision_level=3,
            has_title=False,
            introduced_as_list=False,
        )

        self.assertEqual(interpretation.role, MarkerRole.AMBIGUOUS)
        self.assertEqual(interpretation.confidence, "low")
        self.assertIn("numbering-alone-is-insufficient", interpretation.evidence)

    def test_conflicting_title_and_list_evidence_remains_ambiguous(self) -> None:
        interpretation = interpret_parenthetical_marker(
            edition=2017,
            subdivision_level=2,
            has_title=True,
            introduced_as_list=True,
        )

        self.assertEqual(interpretation.role, MarkerRole.AMBIGUOUS)
        self.assertEqual(interpretation.confidence, "low")
        self.assertEqual(
            interpretation.evidence,
            ("title", "list-introduction", "conflicting-evidence"),
        )

    def test_invalid_subdivision_level_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "subdivision_level"):
            interpret_parenthetical_marker(
                edition=2017,
                subdivision_level=0,
                has_title=True,
                introduced_as_list=False,
            )


class InformationalNoteIdentityTests(unittest.TestCase):
    def test_note_numbers_are_local_to_their_owner(self) -> None:
        first = informational_note_identity("110.26(A)", 1)
        second = informational_note_identity("110.26(B)", 1)

        self.assertEqual(first, "110.26(A)#informational-note:1")
        self.assertEqual(second, "110.26(B)#informational-note:1")
        self.assertNotEqual(first, second)

    def test_note_number_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "note_number"):
            informational_note_identity("110.26(A)", 0)


if __name__ == "__main__":
    unittest.main()
