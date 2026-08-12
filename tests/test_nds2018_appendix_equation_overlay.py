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


def _block(page: int, y: float, text: str, number: int) -> PdfBlock:
    return PdfBlock(
        page_number=page,
        bbox=(45.0, y, 290.0, y + 18.0),
        text=text,
        block_number=number,
    )


def _evidence() -> NdsLayoutEvidence:
    pages = (
        PdfPage(
            85,
            612.0,
            783.0,
            (
                PdfBlock(
                    page_number=85,
                    bbox=(155.0, 120.0, 455.0, 138.0),
                    text="SYNTHETIC DOWEL FASTENERS",
                    block_number=1,
                ),
            ),
        ),
        PdfPage(
            86,
            612.0,
            783.0,
            (
                _block(86, 90.0, "12.1 Scope", 1),
                _block(86, 135.0, "x = y (D-1)", 2),
                _block(86, 180.0, "x = y (O-1)", 3),
            ),
        ),
    )
    return NdsLayoutEvidence(
        ast_source=AstSourceIdentity(
            artifact_id=NDS_2018_ARTIFACT_ID,
            edition_id=NDS_2018_EDITION_ID,
        ),
        file_name="synthetic-nds-appendix-equation.pdf",
        pages=analyze_nds2018_pages(pages),
    )


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


class Nds2018AppendixEquationOverlayTests(unittest.TestCase):
    def test_overlay_promotes_bounded_appendix_equation_locator(self) -> None:
        ast = parse_nds2018_document_structure(_evidence())
        equations = {
            node.locator: node
            for node in _walk(ast.root)
            if node.node_type is DocumentNodeType.EQUATION
        }

        self.assertIn("equation:D-1", equations)
        self.assertEqual(dict(equations["equation:D-1"].attributes)["equation_id"], "D-1")
        self.assertNotIn("equation:O-1", equations)


if __name__ == "__main__":
    unittest.main()
