from __future__ import annotations

import unittest

from building_code_ast.ingest.writing_frame import downstream_page_clip


class PdfWritingFrameClipTests(unittest.TestCase):
    def test_vertical_up_text_clips_to_later_block_flow(self) -> None:
        self.assertEqual(
            downstream_page_clip((192.0, 499.0, 200.0, 744.0), (0.0, -1.0), 612.0, 783.0),
            (192.0, 0.0, 612.0, 783.0),
        )

    def test_horizontal_text_clips_below_announcement(self) -> None:
        self.assertEqual(
            downstream_page_clip((40.0, 100.0, 300.0, 120.0), (1.0, 0.0), 612.0, 783.0),
            (0.0, 100.0, 612.0, 783.0),
        )

    def test_non_cardinal_direction_is_not_silently_approximated(self) -> None:
        with self.assertRaisesRegex(ValueError, "cardinal"):
            downstream_page_clip((10.0, 20.0, 30.0, 40.0), (1.0, 1.0), 100.0, 100.0)


if __name__ == "__main__":
    unittest.main()
