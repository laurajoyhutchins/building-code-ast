from __future__ import annotations

import unittest

from building_code_ast import DocumentNodeType
from building_code_ast.evidence import AstSourceIdentity
from building_code_ast.ingest.nds2018_hierarchy import parse_nds2018_hierarchy
from building_code_ast.ingest.nds2018_layout import (
    NDS_2018_ARTIFACT_ID,
    NDS_2018_EDITION_ID,
    NdsLayoutEvidence,
    analyze_nds2018_pages,
)
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfPage


def _block(page: int, y: float, text: str, number: int) -> PdfBlock:
    return PdfBlock(
        page_number=page,
        bbox=(60.0, y, 550.0, y + 18.0),
        text=text,
        block_number=number,
    )


def _evidence() -> NdsLayoutEvidence:
    pages = (
        PdfPage(
            page_number=6,
            width=612.0,
            height=783.0,
            blocks=(
                _block(6, 120.0, "I Yield Limit Equations for Connections 173", 1),
            ),
        ),
        PdfPage(
            page_number=185,
            width=612.0,
            height=783.0,
            blocks=(
                _block(
                    185,
                    100.0,
                    "Appendix (Non-mandatory) Yield Limit Equations for Connections",
                    1,
                ),
                _block(185, 145.0, ".1 Yield Modes", 2),
            ),
        ),
    )
    return NdsLayoutEvidence(
        ast_source=AstSourceIdentity(
            artifact_id=NDS_2018_ARTIFACT_ID,
            edition_id=NDS_2018_EDITION_ID,
        ),
        file_name="synthetic-nds-layout.pdf",
        pages=analyze_nds2018_pages(pages),
    )


def _flatten(node):
    yield node
    for child in node.children:
        yield from _flatten(child)


class Nds2018AppendixHeadingRecoveryTests(unittest.TestCase):
    def test_recovers_missing_appendix_letter_from_unique_toc_title_and_page(self) -> None:
        ast = parse_nds2018_hierarchy(_evidence())
        nodes = list(_flatten(ast.root))
        appendices = [node for node in nodes if node.node_type is DocumentNodeType.APPENDIX]

        self.assertEqual([node.locator for node in appendices], ["appendix:I"])
        appendix = appendices[0]
        self.assertEqual(appendix.label, "Yield Limit Equations for Connections")
        self.assertEqual(dict(appendix.attributes)["source_role"], "non_mandatory")
        self.assertEqual(
            dict(appendix.attributes)["native_locator_evidence"],
            "front_matter_toc_title_page",
        )
        self.assertNotIn(
            "nds-appendix-locator-unresolved",
            {diagnostic.code for diagnostic in ast.diagnostics},
        )


if __name__ == "__main__":
    unittest.main()
