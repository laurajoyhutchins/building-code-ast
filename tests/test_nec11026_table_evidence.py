from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNode, DocumentNodeType
from building_code_ast.ingest.nec2017 import build_article_seed
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfOutlineItem,
    PdfPage,
)


def _walk(node: DocumentNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _layout() -> PdfLayoutDocument:
    return PdfLayoutDocument(
        file_name="synthetic-nec.pdf",
        outline=(
            PdfOutlineItem(2, "110 Requirements for Synthetic Installations", 1),
            PdfOutlineItem(2, "200 Synthetic Next Article", 2),
        ),
        pages=(
            PdfPage(
                page_number=1,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(
                        1,
                        (54.0, 100.0, 303.0, 125.0),
                        "ARTICLE 110\nRequirements for Synthetic Installations",
                    ),
                    PdfBlock(
                        1,
                        (54.0, 150.0, 303.0, 180.0),
                        "110.26 Synthetic Working Space.",
                    ),
                    PdfBlock(
                        1,
                        (54.0, 190.0, 303.0, 220.0),
                        "(A) Synthetic Dimensions.",
                    ),
                    PdfBlock(
                        1,
                        (54.0, 230.0, 303.0, 270.0),
                        "(1) Synthetic Depth. The minimum depth shall be selected from Table 110.26(A)(1).",
                    ),
                    PdfBlock(
                        1,
                        (327.0, 300.0, 520.0, 315.0),
                        "Table 110.26(A)(1) Synthetic Thresholds",
                        table_region_id=1,
                    ),
                    PdfBlock(
                        1,
                        (327.0, 320.0, 575.0, 340.0),
                        "Synthetic Class Synthetic Limit",
                        table_region_id=1,
                    ),
                    PdfBlock(
                        1,
                        (327.0, 345.0, 575.0, 365.0),
                        "Class A 10 units Class B 20 units",
                        table_region_id=1,
                    ),
                    PdfBlock(
                        1,
                        (327.0, 390.0, 575.0, 420.0),
                        "Synthetic prose after the table.",
                    ),
                ),
            ),
            PdfPage(
                page_number=2,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(
                        2,
                        (54.0, 100.0, 303.0, 125.0),
                        "ARTICLE 200\nSynthetic Next Article",
                    ),
                ),
            ),
        ),
    )


class Nec11026TableEvidenceTests(unittest.TestCase):
    def test_announced_geometric_table_region_fails_closed(self) -> None:
        seed = build_article_seed(
            _layout(),
            "110",
            source_sha256="a" * 64,
            source_size=1234,
        )

        nodes = tuple(_walk(seed.document_ast.root))
        unsupported = tuple(
            node for node in nodes if node.node_type is DocumentNodeType.UNSUPPORTED
        )

        self.assertEqual(len(unsupported), 3)
        self.assertTrue(
            all(
                dict(node.attributes)["structure_hint"] == "table_like_layout"
                for node in unsupported
            )
        )
        self.assertTrue(
            all(
                dict(node.attributes)["table_evidence"] == "announced_geometric_region"
                for node in unsupported
            )
        )
        self.assertEqual(
            sum(item.code == "unsupported-table-layout" for item in seed.diagnostics),
            3,
        )
        self.assertIn(
            "Synthetic prose after the table.",
            {
                node.span.text
                for node in nodes
                if node.node_type is not DocumentNodeType.UNSUPPORTED
            },
        )


if __name__ == "__main__":
    unittest.main()
