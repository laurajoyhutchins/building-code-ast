from __future__ import annotations

import unittest

from building_code_ast import DocumentNodeType
from building_code_ast.evidence import AstSourceIdentity
from building_code_ast.ingest.nds2018_layout import (
    NDS_2018_ARTIFACT_ID,
    NDS_2018_EDITION_ID,
    NdsLayoutEvidence,
    analyze_nds2018_pages,
)
from building_code_ast.ingest.nds2018_nonprose import parse_nds2018_document_structure
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfPage


def _block(
    page: int,
    y: float,
    text: str,
    number: int,
    *,
    x0: float = 45.0,
    x1: float = 560.0,
    height: float = 18.0,
) -> PdfBlock:
    return PdfBlock(
        page_number=page,
        bbox=(x0, y, x1, y + height),
        text=text,
        block_number=number,
    )


def _pages(*, reverse_blocks: bool = False) -> tuple[PdfPage, ...]:
    specs = {
        85: [
            _block(85, 120.0, "SYNTHETIC DOWEL FASTENERS", 1, x0=155.0, x1=455.0),
            _block(85, 220.0, "12.1 Scope 77   12.2 Values 78", 2, x0=100.0, x1=510.0),
        ],
        86: [
            _block(86, 90.0, "12.1 Scope", 1, x1=290.0),
            _block(86, 135.0, "Synthetic equation introduction.", 2, x1=290.0),
            _block(86, 180.0, "x \ue001 y", 3, x0=70.0, x1=180.0),
            _block(86, 181.0, "(12.1-1)", 4, x0=200.0, x1=290.0),
            _block(86, 230.0, "z = q (12.1-2)", 5, x0=80.0, x1=290.0),
        ],
        87: [
            _block(87, 90.0, "See Figure 12A for synthetic context.", 1, x1=290.0),
            _block(87, 220.0, "Figure 12A Synthetic Connection Geometry", 2, x0=45.0, x1=285.0),
            _block(87, 260.0, "Synthetic prose after the figure caption.", 3, x0=45.0, x1=285.0),
        ],
        88: [
            _block(88, 65.0, "Table 12A SYNTHETIC REFERENCE VALUES1,2", 1, x1=500.0, height=26.0),
            _block(88, 115.0, "Synthetic header A B C", 2, x1=560.0),
            _block(88, 155.0, "Synthetic row 1 2 3", 3, x1=560.0, height=200.0),
            _block(88, 690.0, "1. Synthetic table footnote one.", 4, x1=550.0),
        ],
        89: [
            _block(89, 65.0, "Table 12A SYNTHETIC REFERENCE VALUES1,2", 1, x1=500.0, height=26.0),
            _block(89, 78.0, "(Cont.)", 2, x0=45.0, x1=90.0),
            _block(89, 115.0, "Synthetic header D E F", 3, x1=560.0),
            _block(89, 155.0, "Synthetic row 4 5 6", 4, x1=560.0, height=200.0),
            _block(89, 690.0, "2. Synthetic table footnote two.", 5, x1=550.0),
        ],
        90: [
            _block(90, 90.0, "12.2 Values", 1, x1=290.0),
            _block(90, 130.0, "Synthetic prose after the continued table.", 2, x1=290.0),
        ],
    }
    pages: list[PdfPage] = []
    for page_number, blocks in specs.items():
        page_blocks = list(blocks)
        if reverse_blocks:
            page_blocks.reverse()
        pages.append(PdfPage(page_number, 612.0, 783.0, tuple(page_blocks)))
    return tuple(pages)


def _evidence(*, reverse_blocks: bool = False) -> NdsLayoutEvidence:
    return NdsLayoutEvidence(
        ast_source=AstSourceIdentity(
            artifact_id=NDS_2018_ARTIFACT_ID,
            edition_id=NDS_2018_EDITION_ID,
        ),
        file_name="synthetic-nds-nonprose.pdf",
        pages=analyze_nds2018_pages(_pages(reverse_blocks=reverse_blocks)),
    )


def _walk(node, parent=None):
    yield parent, node
    for child in node.children:
        yield from _walk(child, node)


class Nds2018NonproseTests(unittest.TestCase):
    def test_promotes_source_backed_nonprose_structure_without_semantics(self) -> None:
        ast = parse_nds2018_document_structure(_evidence())
        pairs = list(_walk(ast.root))
        nodes = [node for _, node in pairs]
        by_locator = {node.locator: node for node in nodes}

        separated = by_locator["equation:12.1-1"]
        inline = by_locator["equation:12.1-2"]
        self.assertEqual(separated.node_type, DocumentNodeType.EQUATION)
        self.assertEqual(inline.node_type, DocumentNodeType.EQUATION)
        self.assertIn("x \ue001 y", separated.span.text)
        self.assertIn("(12.1-1)", separated.span.text)
        self.assertEqual(dict(separated.attributes)["equation_id"], "12.1-1")
        self.assertEqual(dict(separated.attributes)["glyph_state"], "private_use_text_layer")
        self.assertNotIn("expression", dict(separated.attributes))

        figure = by_locator["figure:12A"]
        self.assertEqual(figure.node_type, DocumentNodeType.FIGURE)
        self.assertEqual(dict(figure.attributes)["graphic_state"], "unavailable_in_text_layout")
        self.assertEqual(
            sum(node.node_type is DocumentNodeType.FIGURE for node in nodes),
            1,
        )

        table = by_locator["table:12A"]
        self.assertEqual(table.node_type, DocumentNodeType.TABLE)
        self.assertEqual(dict(table.attributes)["table_id"], "12A")
        self.assertEqual(dict(table.attributes)["pdf_pages"], "88,89")
        self.assertEqual(dict(table.attributes)["continuation_state"], "continued")
        self.assertEqual(
            [child.node_type for child in table.children].count(DocumentNodeType.TABLE_HEADING),
            2,
        )
        self.assertEqual(
            [child.node_type for child in table.children].count(DocumentNodeType.FOOTNOTE),
            2,
        )
        self.assertTrue(
            any(
                child.node_type is DocumentNodeType.UNSUPPORTED
                and dict(child.attributes).get("source_role") == "table_body_unparsed"
                for child in table.children
            )
        )

        self.assertEqual(
            {diagnostic.code for diagnostic in ast.diagnostics},
            {"nds-figure-graphic-unavailable", "nds-table-body-structure-deferred"},
        )

        recognized = [
            node
            for node in nodes
            if node.node_type in {DocumentNodeType.EQUATION, DocumentNodeType.FIGURE, DocumentNodeType.TABLE}
        ]
        for region in recognized:
            for parent, node in pairs:
                if parent is region:
                    continue
                if node is region or node.node_type in {
                    DocumentNodeType.DOCUMENT,
                    DocumentNodeType.CHAPTER,
                    DocumentNodeType.APPENDIX,
                    DocumentNodeType.SECTION,
                    DocumentNodeType.SUBSECTION,
                }:
                    continue
                self.assertFalse(
                    region.span.start <= node.span.start
                    and node.span.end <= region.span.end,
                    msg=f"stale {node.node_type} ownership remains inside {region.locator}",
                )

    def test_output_is_independent_of_caller_block_order(self) -> None:
        first = parse_nds2018_document_structure(_evidence())
        repeated = parse_nds2018_document_structure(_evidence(reverse_blocks=True))
        self.assertEqual(first.to_dict(), repeated.to_dict())


if __name__ == "__main__":
    unittest.main()
