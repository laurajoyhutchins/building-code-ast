from __future__ import annotations

import unittest

from building_code_ast.ingest.ashrae621_table_geometry import measure_ashrae621_table_geometry
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfPage


class Ashrae621TableGeometryConformanceTests(unittest.TestCase):
    def test_measurement_preserves_caption_identity_repetition_and_candidate_multiplicity(self) -> None:
        document = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=1,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(1, (72, 40, 300, 52), "Table 6.2.2.1 Synthetic table", 0),
                        PdfBlock(1, (72, 60, 200, 80), "cell evidence", 1, table_region_id=1),
                        PdfBlock(1, (220, 60, 400, 80), "other evidence", 2, table_region_id=2),
                    ),
                ),
                PdfPage(
                    page_number=2,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(2, (72, 40, 300, 52), "Table 6.2.2.1 continued", 0),
                        PdfBlock(2, (72, 60, 400, 80), "candidate evidence", 1, table_region_id=1),
                    ),
                ),
            ),
            outline=(),
        )

        result = measure_ashrae621_table_geometry(document)

        self.assertEqual(result.caption_occurrence_count, 2)
        self.assertEqual(result.native_identifier_count, 1)
        self.assertEqual(result.caption_page_count, 2)
        self.assertEqual(result.pages_with_region_evidence, 2)
        self.assertEqual(result.pages_without_region_evidence, ())
        self.assertEqual(result.retained_region_count, 3)
        self.assertEqual(
            [(item.native_locator, item.page_number, item.page_region_count) for item in result.occurrences],
            [("6.2.2.1", 1, 2), ("6.2.2.1", 2, 1)],
        )

    def test_missing_candidate_region_is_explicit_not_inferred(self) -> None:
        document = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=3,
                    width=612.0,
                    height=792.0,
                    blocks=(PdfBlock(3, (72, 40, 300, 52), "Table C-2 Synthetic table", 7),),
                ),
            ),
            outline=(),
        )

        result = measure_ashrae621_table_geometry(document)

        self.assertEqual(result.pages_with_region_evidence, 0)
        self.assertEqual(result.pages_without_region_evidence, (3,))
        self.assertEqual(result.retained_region_count, 0)
        self.assertEqual(result.occurrences[0].page_region_count, 0)

    def test_measurement_serialization_is_source_safe(self) -> None:
        document = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=4,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(4, (72, 40, 300, 52), "Table B2-1 Protected caption wording", 5),
                        PdfBlock(4, (72, 60, 400, 80), "Protected cell wording", 6, table_region_id=1),
                    ),
                ),
            ),
            outline=(),
        )

        payload = measure_ashrae621_table_geometry(document).to_dict()
        serialized = repr(payload)

        self.assertNotIn("Protected caption wording", serialized)
        self.assertNotIn("Protected cell wording", serialized)
        self.assertEqual(payload["occurrences"][0]["native_locator"], "B2-1")


if __name__ == "__main__":
    unittest.main()
