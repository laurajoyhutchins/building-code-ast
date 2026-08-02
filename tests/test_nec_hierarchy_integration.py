from __future__ import annotations

import unittest

from building_code_ast.ingest.nec2017 import build_article_seed
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfOutlineItem,
    PdfPage,
)
from building_code_ast.nec.seed import article_seed_view


def _hierarchical_layout() -> PdfLayoutDocument:
    return PdfLayoutDocument(
        file_name="synthetic-nec-hierarchy.pdf",
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
                    PdfBlock(1, (54.0, 165.0, 560.0, 200.0), "110.1 Scope. Synthetic scope text."),
                    PdfBlock(1, (64.0, 210.0, 560.0, 245.0), "(A) First Topic. Synthetic subsection text."),
                    PdfBlock(1, (74.0, 255.0, 560.0, 290.0), "(1) First Item. Synthetic item text."),
                    PdfBlock(1, (84.0, 300.0, 560.0, 335.0), "Informational Note: Synthetic explanation."),
                    PdfBlock(1, (64.0, 345.0, 560.0, 380.0), "(B) Second Topic. Synthetic sibling text."),
                    PdfBlock(1, (54.0, 390.0, 560.0, 425.0), "110.2 Approval. Synthetic approval text."),
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


class ArticleSeedHierarchyIntegrationTests(unittest.TestCase):
    def test_article_seed_contains_nested_canonical_nec_locators(self) -> None:
        seed = build_article_seed(
            _hierarchical_layout(),
            "110",
            source_sha256="b" * 64,
            source_size=4321,
        )

        article_children = seed.document_ast.root.children[0].children
        part = next(node for node in article_children if dict(node.attributes).get("nec_part") == "I")
        first_section, second_section = part.children
        subsection_a, subsection_b = first_section.children
        item = subsection_a.children[0]
        note = item.children[0]

        self.assertEqual(first_section.locator, "nec:110.1")
        self.assertEqual(subsection_a.locator, "nec:110.1(A)")
        self.assertEqual(item.locator, "nec:110.1(A)(1)")
        self.assertEqual(note.label, "Informational Note")
        self.assertEqual(subsection_b.locator, "nec:110.1(B)")
        self.assertEqual(second_section.locator, "nec:110.2")
        self.assertEqual(first_section.span.end, subsection_b.span.end)
        self.assertEqual(part.span.end, second_section.span.end)

    def test_semantic_seed_view_flattens_nested_nodes_in_source_preorder(self) -> None:
        seed = build_article_seed(
            _hierarchical_layout(),
            "110",
            source_sha256="c" * 64,
            source_size=4321,
        )

        view = article_seed_view(seed.to_dict())
        structural = [
            node.locator
            for node in view.nodes
            if node.locator.startswith("nec:")
        ]

        self.assertEqual(
            structural,
            [
                "nec:110.1",
                "nec:110.1(A)",
                "nec:110.1(A)(1)",
                "nec:110.1(B)",
                "nec:110.2",
            ],
        )


if __name__ == "__main__":
    unittest.main()
