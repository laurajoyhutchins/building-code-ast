from __future__ import annotations

import unittest

from building_code_ast.ibc2018_reporting import render_coverage_markdown


class Ibc2018ReportingTests(unittest.TestCase):
    def test_render_coverage_markdown_uses_reconciled_counts(self) -> None:
        coverage = {
            "source_sha256": "abc",
            "counts": {"tables": 2, "vector_regions": 7},
            "incidental_layout_counts": {"broad": 3, "strict": 1},
            "internal_reference_resolution": {"resolved": 8, "unresolved": 1},
            "external_references": {
                "citation_occurrence_count": 10,
                "matched_family_count": 4,
                "unmatched_occurrence_count": 2,
                "newly_alias_matched_occurrence_count": 3,
            },
            "chapter35": {
                "row_count": 5,
                "individual_designation_count": 4,
                "normalized_family_count": 5,
                "families_not_detected_elsewhere_count": 1,
            },
            "vector_regions": {
                "record_count": 7,
                "page_count_with_regions": 6,
                "review_state_counts": {"disputed": 5, "rejected": 2},
                "disposition_counts": {"candidate": 5, "rejected": 2},
            },
            "review_queue": {"record_count": 9, "priority_counts": {"P0": 2, "P1": 3, "P3": 4}},
            "known_limitations": ["semantic review remains human-gated"],
        }
        rendered = render_coverage_markdown(coverage)
        self.assertIn("- tables: **2**", rendered)
        self.assertIn("- vector_regions: **7**", rendered)
        self.assertIn("- resolved: **8**", rendered)
        self.assertIn("- Unmatched citation occurrences: **2**", rendered)
        self.assertIn("- P0: **2**", rendered)
        self.assertIn("semantic review remains human-gated", rendered)


if __name__ == "__main__":
    unittest.main()
