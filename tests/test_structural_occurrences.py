from __future__ import annotations

import unittest

from building_code_ast.ingest.structural_occurrences import (
    LocatorOccurrence,
    LocatorOccurrencePattern,
    group_locator_occurrences,
)


class StructuralOccurrenceTests(unittest.TestCase):
    def test_adjacent_repeated_pages_form_one_source_ordered_group(self) -> None:
        occurrences = (
            LocatorOccurrence("6.2.2.1", pdf_page=17, source_order=30),
            LocatorOccurrence("6.2.2.1", pdf_page=15, source_order=10),
            LocatorOccurrence("6.2.2.1", pdf_page=16, source_order=20),
        )

        groups = group_locator_occurrences(occurrences)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].native_locator, "6.2.2.1")
        self.assertEqual(groups[0].pages, (15, 16, 17))
        self.assertEqual(groups[0].pattern, LocatorOccurrencePattern.ADJACENT_PAGES)
        self.assertEqual(
            tuple(item.source_order for item in groups[0].occurrences),
            (10, 20, 30),
        )

    def test_same_page_duplicates_are_preserved_as_ambiguity_not_collapsed(self) -> None:
        group = group_locator_occurrences(
            (
                LocatorOccurrence("C-3", pdf_page=40, source_order=1),
                LocatorOccurrence("C-3", pdf_page=40, source_order=2),
                LocatorOccurrence("C-3", pdf_page=41, source_order=3),
            )
        )[0]

        self.assertEqual(group.pages, (40, 40, 41))
        self.assertEqual(group.pattern, LocatorOccurrencePattern.SAME_PAGE_DUPLICATE)
        self.assertEqual(len(group.occurrences), 3)

    def test_nonadjacent_repetition_is_distinct_from_adjacent_continuation_shape(self) -> None:
        group = group_locator_occurrences(
            (
                LocatorOccurrence("K-1", pdf_page=54, source_order=1),
                LocatorOccurrence("K-1", pdf_page=56, source_order=2),
            )
        )[0]

        self.assertEqual(group.pattern, LocatorOccurrencePattern.DISCONTIGUOUS_PAGES)

    def test_groups_are_deterministic_across_caller_order(self) -> None:
        occurrences = (
            LocatorOccurrence("B", pdf_page=4, source_order=30),
            LocatorOccurrence("A", pdf_page=2, source_order=10),
            LocatorOccurrence("A", pdf_page=3, source_order=20),
        )
        self.assertEqual(
            group_locator_occurrences(occurrences),
            group_locator_occurrences(reversed(occurrences)),
        )

    def test_invalid_identity_and_source_order_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "native_locator"):
            LocatorOccurrence(" ", pdf_page=1, source_order=0)
        with self.assertRaisesRegex(ValueError, "pdf_page"):
            LocatorOccurrence("A", pdf_page=0, source_order=0)
        with self.assertRaisesRegex(ValueError, "source_order"):
            LocatorOccurrence("A", pdf_page=1, source_order=-1)
        with self.assertRaisesRegex(ValueError, "source_order values must be unique"):
            group_locator_occurrences(
                (
                    LocatorOccurrence("A", pdf_page=1, source_order=0),
                    LocatorOccurrence("B", pdf_page=2, source_order=0),
                )
            )


if __name__ == "__main__":
    unittest.main()
