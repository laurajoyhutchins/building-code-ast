from __future__ import annotations

import inspect
import unittest

from building_code_ast.ibc2018_caption_corrections import CAPTION_CORRECTIONS
from building_code_ast.ibc2018_corpus import SOURCE_SHA256, _caption_identifier


class Ibc2018CaptionCorrectionTests(unittest.TestCase):
    def test_named_anomalies_are_explicit_source_safe_records(self) -> None:
        self.assertEqual(len(CAPTION_CORRECTIONS), 3)
        self.assertEqual(
            {correction.correction_id for correction in CAPTION_CORRECTIONS},
            {
                "caption.table-1010-split-identifier",
                "caption.page-556-embedded-table-label",
                "caption.table-4-hyphenated-identifier",
            },
        )
        self.assertTrue(all(correction.source_sha256 == SOURCE_SHA256 for correction in CAPTION_CORRECTIONS))
        self.assertTrue(all(correction.rationale for correction in CAPTION_CORRECTIONS))
        self.assertTrue(all(correction.action for correction in CAPTION_CORRECTIONS))

    def test_current_caption_anomaly_behavior_is_preserved(self) -> None:
        self.assertEqual(
            _caption_identifier("TABLE 1 010", pdf_page=100),
            ("table", "1010", "010", ""),
        )
        self.assertIsNone(_caption_identifier("TABLE 100.1", pdf_page=556))
        self.assertEqual(
            _caption_identifier("TABLE 4-1", pdf_page=100),
            ("table", "4-1", "", ""),
        )

    def test_generic_caption_parser_no_longer_owns_literal_anomaly_branches(self) -> None:
        source = inspect.getsource(_caption_identifier)
        self.assertNotIn("TABLE 1 010", source)
        self.assertNotIn("pdf_page == 556", source)
        self.assertNotIn('identifier == "4"', source)


if __name__ == "__main__":
    unittest.main()
