from __future__ import annotations

import unittest

from building_code_ast.ingest.layout_analysis import (
    CleanedPage,
    PageLines,
    ReadingOrderMode,
    SourceFragment,
    VisualLine,
    clean_recurring_margins,
    detect_recurring_margins,
    estimate_body_font,
    infer_page_order,
    order_page_lines,
    structural_margin_key,
    visual_line_id,
)


def make_line(
    page: int,
    x0: float,
    y0: float,
    x1: float,
    text: str,
    *,
    font_size: float = 10.0,
    page_height: float = 300.0,
) -> VisualLine:
    fragment = SourceFragment(
        page_number=page,
        bbox=(x0, y0, x1, y0 + font_size),
        block_number=int(y0 * 10 + x0),
        raw_text=text,
        font_size=font_size,
        font_name="SyntheticBody",
    )
    return VisualLine(
        line_id=visual_line_id(page, (fragment,)),
        page_number=page,
        bbox=fragment.bbox,
        text=text,
        fragments=(fragment,),
        font_size=font_size,
        font_name="SyntheticBody",
    )


class LayoutAnalysisTests(unittest.TestCase):
    def test_structural_key_normalizes_numeric_runs(self) -> None:
        self.assertEqual(
            structural_margin_key("2018 IBC 31"),
            structural_margin_key("2018 IBC 32"),
        )

    def test_recurring_header_is_removed_only_in_top_band(self) -> None:
        pages = tuple(
            PageLines(
                page_number=page,
                width=200.0,
                height=300.0,
                lines=(
                    make_line(page, 10.0, 5.0, 190.0, f"2018 IBC {page}"),
                    make_line(page, 10.0, 145.0, 190.0, f"2018 IBC {page}"),
                    make_line(page, 10.0, 175.0, 190.0, f"Body paragraph {page}."),
                ),
            )
            for page in (1, 2, 3)
        )

        margins = detect_recurring_margins(pages)
        cleaned = clean_recurring_margins(pages, margins)

        self.assertEqual(
            [item.line.text for item in cleaned[0].removed],
            ["2018 IBC 1"],
        )
        self.assertIn("2018 IBC 1", [item.text for item in cleaned[0].retained])
        self.assertEqual(cleaned[0].removed[0].reason, "recurring_header")

    def test_fixed_safety_bands_remove_symbol_only_footer(self) -> None:
        page = PageLines(
            page_number=1,
            width=200.0,
            height=300.0,
            lines=(
                make_line(1, 10.0, 10.0, 190.0, "RUNNING HEADER"),
                make_line(1, 10.0, 150.0, 190.0, "Body text."),
                make_line(1, 95.0, 286.0, 105.0, "®"),
            ),
        )
        cleaned = clean_recurring_margins((page,), detect_recurring_margins((page,)))
        self.assertEqual([line.text for line in cleaned[0].retained], ["Body text."])
        self.assertEqual(
            [item.reason for item in cleaned[0].removed],
            ["fixed_header", "fixed_footer"],
        )

    def test_margin_key_collapses_split_numeric_runs(self) -> None:
        self.assertEqual(
            structural_margin_key("2 201 8 INTERNATIONAL BUILDING CODE"),
            structural_margin_key("12 2018 INTERNATIONAL BUILDING CODE"),
        )

    def test_body_font_estimate_resists_short_oversized_headings(self) -> None:
        page = CleanedPage(
            page_number=1,
            width=200.0,
            height=300.0,
            retained=(
                make_line(1, 10.0, 20.0, 190.0, "LARGE TITLE", font_size=22.0),
                make_line(
                    1,
                    10.0,
                    60.0,
                    190.0,
                    "This is a long synthetic body paragraph used for weighting.",
                    font_size=10.0,
                ),
                make_line(
                    1,
                    10.0,
                    85.0,
                    190.0,
                    "Another long synthetic body paragraph used for weighting.",
                    font_size=10.0,
                ),
            ),
            removed=(),
        )

        profile = estimate_body_font((page,))

        self.assertEqual(profile.body_font_size, 10.0)
        self.assertEqual(profile.heading_threshold, 11.5)
        self.assertIn("body_font:10.0", profile.evidence)

    def test_infers_asymmetric_two_column_split(self) -> None:
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(
                make_line(1, 50.0, 60.0, 190.0, "left top"),
                make_line(1, 50.0, 100.0, 190.0, "left bottom"),
                make_line(1, 360.0, 60.0, 540.0, "right top"),
                make_line(1, 360.0, 100.0, 540.0, "right bottom"),
            ),
            removed=(),
        )

        profile = infer_page_order(page)
        ordered = order_page_lines(page, profile)

        self.assertIs(profile.mode, ReadingOrderMode.TWO_COLUMN)
        self.assertIsNotNone(profile.split_x)
        assert profile.split_x is not None
        self.assertGreater(profile.split_x, 190.0)
        self.assertLess(profile.split_x, 360.0)
        self.assertEqual(
            [item.text for item in ordered],
            ["left top", "left bottom", "right top", "right bottom"],
        )

    def test_detects_columns_despite_many_indented_starts(self) -> None:
        retained = []
        for index, x0 in enumerate((50.0, 65.0, 80.0, 145.0, 175.0, 50.0)):
            retained.append(make_line(1, x0, 40.0 + index * 20.0, 285.0, f"left {index}"))
        for index, x0 in enumerate((326.0, 338.0, 350.0, 410.0, 326.0, 360.0)):
            retained.append(make_line(1, x0, 44.0 + index * 20.0, 570.0, f"right {index}"))
        page = CleanedPage(1, 612.0, 792.0, tuple(retained), ())

        profile = infer_page_order(page)
        ordered = order_page_lines(page, profile)

        self.assertIs(profile.mode, ReadingOrderMode.TWO_COLUMN)
        self.assertGreater(profile.split_x or 0.0, 285.0)
        self.assertLess(profile.split_x or 612.0, 326.0)
        self.assertTrue(all(line.text.startswith("left") for line in ordered[:6]))
        self.assertTrue(all(line.text.startswith("right") for line in ordered[6:]))

    def test_detects_list_heavy_two_column_page(self) -> None:
        retained = []
        for index in range(24):
            width = 55.0 if index < 18 else 180.0
            retained.append(
                make_line(1, 50.0, 30.0 + index * 9.0, 50.0 + width, f"left item {index}")
            )
        for index in range(12):
            retained.append(
                make_line(1, 320.0, 34.0 + index * 16.0, 560.0, f"right paragraph {index}")
            )
        page = CleanedPage(1, 612.0, 792.0, tuple(retained), ())

        profile = infer_page_order(page)

        self.assertIs(profile.mode, ReadingOrderMode.TWO_COLUMN)
        self.assertGreater(profile.split_x or 0.0, 230.0)
        self.assertLess(profile.split_x or 612.0, 340.0)

    def test_rejects_false_split_without_vertical_overlap(self) -> None:
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(
                make_line(1, 50.0, 20.0, 190.0, "top left"),
                make_line(1, 360.0, 240.0, 540.0, "bottom right"),
            ),
            removed=(),
        )

        self.assertIs(infer_page_order(page).mode, ReadingOrderMode.TOP_TO_BOTTOM)

    def test_full_width_opening_line_precedes_two_column_body(self) -> None:
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(
                make_line(1, 30.0, 10.0, 570.0, "CHAPTER TITLE"),
                make_line(1, 50.0, 80.0, 190.0, "left"),
                make_line(1, 360.0, 80.0, 540.0, "right"),
                make_line(1, 50.0, 110.0, 190.0, "left two"),
                make_line(1, 360.0, 110.0, 540.0, "right two"),
            ),
            removed=(),
        )

        profile = infer_page_order(page)
        self.assertIs(profile.mode, ReadingOrderMode.TWO_COLUMN)
        self.assertEqual(order_page_lines(page, profile)[0].text, "CHAPTER TITLE")

    def test_full_width_separator_splits_two_column_bands(self) -> None:
        page = CleanedPage(
            page_number=1,
            width=600.0,
            height=300.0,
            retained=(
                make_line(1, 50.0, 40.0, 190.0, "left above"),
                make_line(1, 360.0, 40.0, 540.0, "right above"),
                make_line(1, 30.0, 100.0, 570.0, "FULL WIDTH HEADING"),
                make_line(1, 50.0, 150.0, 190.0, "left below"),
                make_line(1, 360.0, 150.0, 540.0, "right below"),
            ),
            removed=(),
        )

        profile = infer_page_order(page)
        ordered = order_page_lines(page, profile)

        self.assertIs(profile.mode, ReadingOrderMode.TWO_COLUMN)
        self.assertEqual(
            [line.text for line in ordered],
            [
                "left above",
                "right above",
                "FULL WIDTH HEADING",
                "left below",
                "right below",
            ],
        )


if __name__ == "__main__":
    unittest.main()
