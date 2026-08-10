from __future__ import annotations

import unittest

from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfOutlineItem, PdfPage
from building_code_ast.nec2017_corpus import measure_nec2017_corpus


DIGEST = "603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7"


def _page(number: int, *texts: str) -> PdfPage:
    blocks = tuple(
        PdfBlock(
            page_number=number,
            bbox=(72.0, 100.0 + index * 30.0, 540.0, 120.0 + index * 30.0),
            text=text,
            block_number=index,
        )
        for index, text in enumerate(texts)
    )
    return PdfPage(page_number=number, width=612.0, height=792.0, blocks=blocks)


class Nec2017CorpusMeasurementTests(unittest.TestCase):
    def test_measurement_reuses_current_classifier_after_final_article_fix(self) -> None:
        layout = PdfLayoutDocument(
            file_name="nec-2017.pdf",
            pages=(
                _page(1, "ARTICLE 840 Premises", "840.1 Scope."),
                _page(2, "Chapter 9 Tables", "Table 1 Example"),
                _page(3, "Informative Annex A Example"),
            ),
            outline=(
                PdfOutlineItem(level=2, title="840 Premises", page_number=1),
                PdfOutlineItem(level=1, title="Chapter 9 Tables", page_number=2),
                PdfOutlineItem(level=1, title="Informative Annex A Example", page_number=3),
            ),
        )

        report = measure_nec2017_corpus(
            layout,
            source_sha256=DIGEST,
            source_size=7_422_245,
        )

        self.assertEqual(report["measurement_version"], "0.1.0")
        self.assertEqual(report["source"]["sha256"], DIGEST)
        self.assertEqual(report["source"]["page_count"], 3)
        self.assertEqual(report["outline_counts"], {"numeric_articles": 1, "chapters": 1, "informative_annexes": 1})
        self.assertEqual(report["article_counts"]["observed"], 1)
        self.assertEqual(report["article_counts"]["boundary_issues"], 0)
        self.assertEqual(report["boundary_issues"], [])

        self.assertEqual(report["classifier_counts"]["heading"], 1)
        self.assertEqual(report["classifier_counts"]["section"], 1)
        self.assertEqual(report["classifier_counts"]["unsupported"], 0)

    def test_same_page_chapter_transition_already_trimmed_by_selector_is_not_an_issue(self) -> None:
        layout = PdfLayoutDocument(
            file_name="nec-2017.pdf",
            pages=(
                _page(1, "ARTICLE 110 Requirements", "110.1 Scope."),
                _page(2, "Chapter 2 Wiring", "ARTICLE 200 Conductors", "200.1 Scope."),
            ),
            outline=(
                PdfOutlineItem(level=2, title="110 Requirements", page_number=1),
                PdfOutlineItem(level=1, title="Chapter 2 Wiring", page_number=2),
                PdfOutlineItem(level=2, title="200 Conductors", page_number=2),
            ),
        )

        report = measure_nec2017_corpus(layout, source_sha256=DIGEST, source_size=7_422_245)
        self.assertEqual(report["article_counts"]["observed"], 2)
        self.assertEqual(report["article_counts"]["boundary_issues"], 0)
        self.assertEqual(report["boundary_issues"], [])

    def test_measurement_is_order_stable_and_fails_closed_on_bad_identity(self) -> None:
        layout = PdfLayoutDocument(
            file_name="nec-2017.pdf",
            pages=(
                _page(1, "ARTICLE 100 Definitions", "100.1 Scope."),
                _page(2, "ARTICLE 110 Requirements", "110.1 Scope."),
            ),
            outline=(
                PdfOutlineItem(level=2, title="100 Definitions", page_number=1),
                PdfOutlineItem(level=2, title="110 Requirements", page_number=2),
            ),
        )
        first = measure_nec2017_corpus(layout, source_sha256=DIGEST, source_size=7_422_245)
        second = measure_nec2017_corpus(layout, source_sha256=DIGEST, source_size=7_422_245)
        self.assertEqual(first, second)

        with self.assertRaises(ValueError):
            measure_nec2017_corpus(layout, source_sha256="not-a-digest", source_size=7_422_245)
        with self.assertRaises(ValueError):
            measure_nec2017_corpus(layout, source_sha256=DIGEST, source_size=0)


if __name__ == "__main__":
    unittest.main()
