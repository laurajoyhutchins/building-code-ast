from __future__ import annotations

import unittest

from building_code_ast.ingest.table_continuation import (
    TableCaptionOccurrence,
    classify_table_continuations,
)


class TableExplicitContinuationTests(unittest.TestCase):
    def test_explicit_continuation_links_to_immediately_prior_same_locator(self) -> None:
        occurrences = (
            TableCaptionOccurrence("a", "6.2.2.1", 15, False),
            TableCaptionOccurrence("b", "6.2.2.1", 16, True),
            TableCaptionOccurrence("c", "6.2.2.1", 17, True),
        )

        result = classify_table_continuations(occurrences)

        self.assertEqual(
            result.resolved_links,
            (("a", "b"), ("b", "c")),
        )
        self.assertEqual(result.unresolved_repeated_occurrence_ids, ())

    def test_repeated_locator_without_explicit_marker_remains_unresolved(self) -> None:
        occurrences = (
            TableCaptionOccurrence("first", "K-1", 54, False),
            TableCaptionOccurrence("second", "K-1", 55, False),
            TableCaptionOccurrence("third", "K-1", 56, False),
        )

        result = classify_table_continuations(occurrences)

        self.assertEqual(result.resolved_links, ())
        self.assertEqual(
            result.unresolved_repeated_occurrence_ids,
            ("second", "third"),
        )

    def test_different_native_locators_do_not_link(self) -> None:
        occurrences = (
            TableCaptionOccurrence("left", "6.2.2.2", 19, False),
            TableCaptionOccurrence("right", "6.2.5.2", 19, True),
        )

        result = classify_table_continuations(occurrences)

        self.assertEqual(result.resolved_links, ())
        self.assertEqual(result.unresolved_repeated_occurrence_ids, ())
        self.assertEqual(result.orphan_explicit_continuation_ids, ("right",))

    def test_first_occurrence_marked_continued_is_orphan_evidence(self) -> None:
        occurrences = (
            TableCaptionOccurrence("orphan", "8.2", 25, True),
        )

        result = classify_table_continuations(occurrences)

        self.assertEqual(result.resolved_links, ())
        self.assertEqual(result.orphan_explicit_continuation_ids, ("orphan",))

    def test_input_order_does_not_change_classification(self) -> None:
        ordered = (
            TableCaptionOccurrence("start", "C-2", 37, False),
            TableCaptionOccurrence("middle", "C-2", 38, True),
            TableCaptionOccurrence("end", "C-2", 39, True),
        )
        reversed_input = tuple(reversed(ordered))

        self.assertEqual(
            classify_table_continuations(ordered),
            classify_table_continuations(reversed_input),
        )


if __name__ == "__main__":
    unittest.main()
