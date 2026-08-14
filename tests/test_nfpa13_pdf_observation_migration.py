from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from building_code_ast.pdf_observation import (
    ObservedPdfBlock,
    ObservedPdfLine,
    ObservedPdfPage,
    ObservedPdfSpan,
)


MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_nfpa13_2019_ast.py"
SPEC = importlib.util.spec_from_file_location("extract_nfpa13_2019_ast_observation_test", MODULE_PATH)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


class _Page:
    def get_text(self, kind: str, *, sort: bool = False) -> object:
        if kind == "text":
            return "NFPA 13 2019 Edition\n13-42\n"
        raise AssertionError(f"NFPA adapter must not walk PyMuPDF {kind!r} text directly")


class _Document:
    def __getitem__(self, index: int) -> _Page:
        if index != 4:
            raise AssertionError(f"unexpected document index {index}")
        return _Page()


class Nfpa13PdfObservationMigrationTests(unittest.TestCase):
    def test_raw_lines_project_shared_observation_and_keep_nfpa_page_policy_local(self) -> None:
        observed = ObservedPdfPage(
            page_number=5,
            width=612.0,
            height=792.0,
            blocks=(
                ObservedPdfBlock(
                    page_number=5,
                    block_number=7,
                    block_id="p5:b7",
                    bbox=(327.0, 100.0, 500.0, 112.0),
                    lines=(
                        ObservedPdfLine(
                            line_id="p5:b7:l0",
                            bbox=(327.0, 100.0, 500.0, 112.0),
                            spans=(
                                ObservedPdfSpan(
                                    span_id="p5:b7:l0:s0",
                                    bbox=(327.0, 100.0, 390.0, 112.0),
                                    text="10.2.1 ",
                                    font_name="NewBaskervilleStd-Bold",
                                    font_size=9.0,
                                    flags=16,
                                ),
                                ObservedPdfSpan(
                                    span_id="p5:b7:l0:s1",
                                    bbox=(390.0, 100.0, 500.0, 112.0),
                                    text="Synthetic Heading",
                                    font_name="NewBaskervilleStd-Roman",
                                    font_size=9.0,
                                    flags=0,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            rules=(),
        )

        with patch.object(subject, "observe_pymupdf_page", return_value=observed, create=True) as shared:
            lines = subject.raw_lines_from_document(_Document(), 5, 5)

        shared.assert_called_once()
        self.assertEqual(shared.call_args.kwargs, {"page_number": 5})
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line.text, "10.2.1 Synthetic Heading")
        self.assertEqual(line.pdf_page, 5)
        self.assertEqual(line.printed_page, "13-42")
        self.assertEqual(line.column, 1)
        self.assertEqual(line.bbox, (327.0, 100.0, 500.0, 112.0))
        self.assertEqual(
            line.fonts,
            ("NewBaskervilleStd-Bold", "NewBaskervilleStd-Roman"),
        )
        self.assertEqual(line.sizes, (9.0, 9.0))


if __name__ == "__main__":
    unittest.main()
