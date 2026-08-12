from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import CleanedPage, RuleSegment, SourceFragment, VisualLine
from building_code_ast.ingest.table_candidate_ownership import TableCaptionAnchor
from building_code_ast.nec2017_table_geometry_measurement import (
    NEC2017_SHA256,
    NEC2017_SIZE_BYTES,
    measure_nec2017_table_geometry,
)


def _fragment(page: int, block: int, bbox: tuple[float, float, float, float], text: str) -> SourceFragment:
    return SourceFragment(page, bbox, block, text, 10.0, "Synthetic")


def _table_page() -> CleanedPage:
    first = (
        _fragment(1, 1, (50, 102, 90, 112), "Protected A"),
        _fragment(1, 1, (150, 102, 190, 112), "10"),
    )
    second = (
        _fragment(1, 2, (50, 122, 90, 132), "Protected B"),
        _fragment(1, 2, (150, 122, 190, 132), "20"),
    )
    lines = (
        VisualLine(1, (50, 102, 190, 112), "Protected A 10", first),
        VisualLine(1, (50, 122, 190, 132), "Protected B 20", second),
    )
    rules = (
        RuleSegment(1, 50, 100, 250, 100),
        RuleSegment(1, 50, 120, 250, 120),
        RuleSegment(1, 50, 140, 250, 140),
        RuleSegment(1, 50, 100, 50, 140),
        RuleSegment(1, 150, 100, 150, 140),
        RuleSegment(1, 250, 100, 250, 140),
    )
    return CleanedPage(1, 612.0, 792.0, lines, (), rules)


def _pages() -> tuple[CleanedPage, ...]:
    return (_table_page(),) + tuple(
        CleanedPage(number, 612.0, 792.0, (), (), ()) for number in range(2, 882)
    )


class Nec2017TableGeometryMeasurementTests(unittest.TestCase):
    def test_exact_source_measurement_uses_shared_geometry_and_is_source_safe(self) -> None:
        caption = TableCaptionAnchor("caption:1", 1, (50, 80, 250, 90))
        first = measure_nec2017_table_geometry(
            _pages(), (caption,), source_sha256=NEC2017_SHA256, source_size=NEC2017_SIZE_BYTES
        )
        second = measure_nec2017_table_geometry(
            _pages(), (caption,), source_sha256=NEC2017_SHA256, source_size=NEC2017_SIZE_BYTES
        )

        self.assertEqual(first, second)
        self.assertEqual(first["source"]["page_count"], 881)
        self.assertEqual(first["candidate_family"]["grouped_geometry_candidates"], 1)
        self.assertEqual(first["candidate_family"]["vector_rule_candidates"], 1)
        self.assertEqual(first["candidate_family"]["candidate_envelopes_total"], 2)
        self.assertEqual(first["caption_ownership"]["recognized_caption_with_candidate"], 1)
        self.assertEqual(first["caption_ownership"]["ambiguous_caption_with_multiple_candidates"], 1)
        self.assertFalse(first["parser_promotion_performed"])
        self.assertNotIn("Protected A", repr(first))
        self.assertNotIn("Protected B", repr(first))

    def test_unmatched_candidate_and_nonhorizontal_caption_remain_explicit(self) -> None:
        caption = TableCaptionAnchor("caption:offset", 1, (20, 80, 220, 90))
        report = measure_nec2017_table_geometry(
            _pages(),
            (caption,),
            source_sha256=NEC2017_SHA256,
            source_size=NEC2017_SIZE_BYTES,
            unsupported_nonhorizontal_caption_starts=1,
        )
        self.assertEqual(report["denominators"]["table_caption_occurrences"], 2)
        self.assertEqual(report["table_start_family"]["unsupported_nonhorizontal_caption_starts"], 1)
        self.assertEqual(report["candidate_family"]["recognized_owned_candidates"], 0)
        self.assertEqual(report["candidate_family"]["unsupported_unresolved_candidates"], 2)
        self.assertEqual(report["caption_ownership"]["unsupported_caption_without_candidate"], 1)

    def test_exact_source_identity_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            measure_nec2017_table_geometry(
                _pages(), (), source_sha256="0" * 64, source_size=NEC2017_SIZE_BYTES
            )
        with self.assertRaises(ValueError):
            measure_nec2017_table_geometry(
                _pages()[:-1], (), source_sha256=NEC2017_SHA256, source_size=NEC2017_SIZE_BYTES
            )


if __name__ == "__main__":
    unittest.main()
