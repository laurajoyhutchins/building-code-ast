from __future__ import annotations

import unittest

from building_code_ast.ingest.nec2017 import build_article_seed
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfOutlineItem,
    PdfPage,
)
from building_code_ast.nec.sections import build_section_review


def _normative_hierarchy_layout() -> PdfLayoutDocument:
    return PdfLayoutDocument(
        file_name="synthetic-nec-semantic-hierarchy.pdf",
        outline=(
            PdfOutlineItem(2, "110 Synthetic Installation Rules", 1),
            PdfOutlineItem(2, "200 Synthetic Next Article", 2),
        ),
        pages=(
            PdfPage(
                page_number=1,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(1, (54.0, 90.0, 560.0, 120.0), "ARTICLE 110\nSynthetic Installation Rules"),
                    PdfBlock(1, (54.0, 130.0, 560.0, 155.0), "Part I. General"),
                    PdfBlock(1, (54.0, 165.0, 560.0, 200.0), "110.1 Scope. The equipment shall be identified."),
                    PdfBlock(1, (64.0, 210.0, 560.0, 245.0), "(A) First Topic. The enclosure shall be secured."),
                    PdfBlock(1, (74.0, 255.0, 560.0, 290.0), "(1) First Item. The label shall be visible."),
                    PdfBlock(1, (54.0, 300.0, 560.0, 335.0), "110.2 Approval. The assembly shall be approved."),
                ),
            ),
            PdfPage(
                page_number=2,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(2, (54.0, 90.0, 560.0, 120.0), "ARTICLE 200\nSynthetic Next Article"),
                ),
            ),
        ),
    )


class NestedSemanticCompatibilityTests(unittest.TestCase):
    def test_section_review_reads_each_source_block_once(self) -> None:
        seed = build_article_seed(
            _normative_hierarchy_layout(),
            "110",
            source_sha256="d" * 64,
            source_size=9876,
        )

        review = build_section_review(seed.to_dict(), "110.1")

        self.assertEqual(len(review.clauses), 3)
        self.assertEqual(
            [clause.span.text for clause in review.clauses],
            [
                "The equipment shall be identified.",
                "The enclosure shall be secured.",
                "The label shall be visible.",
            ],
        )
        self.assertEqual(
            [node.span.text for node in review.source_nodes],
            [
                "110.1 Scope. The equipment shall be identified.",
                "(A) First Topic. The enclosure shall be secured.",
                "(1) First Item. The label shall be visible.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
