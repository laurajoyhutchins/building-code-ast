from __future__ import annotations

import unittest

from building_code_ast.ingest.pdf_layout import project_bbox_to_writing_frame


class PdfWritingFrameGeometryTests(unittest.TestCase):
    def test_horizontal_writing_frame_preserves_native_bbox(self) -> None:
        bbox = (10.0, 20.0, 30.0, 40.0)

        self.assertEqual(
            project_bbox_to_writing_frame(bbox, (1.0, 0.0)),
            bbox,
        )

    def test_vertical_up_writing_frame_maps_page_y_to_inline_and_page_x_to_block_flow(self) -> None:
        bbox = (40.0, 400.0, 54.0, 744.0)

        self.assertEqual(
            project_bbox_to_writing_frame(bbox, (0.0, -1.0)),
            (-744.0, 40.0, -400.0, 54.0),
        )

    def test_direction_is_normalized_before_projection(self) -> None:
        bbox = (40.0, 400.0, 54.0, 744.0)

        self.assertEqual(
            project_bbox_to_writing_frame(bbox, (0.0, -2.0)),
            (-744.0, 40.0, -400.0, 54.0),
        )

    def test_zero_direction_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "writing direction"):
            project_bbox_to_writing_frame((10.0, 20.0, 30.0, 40.0), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
