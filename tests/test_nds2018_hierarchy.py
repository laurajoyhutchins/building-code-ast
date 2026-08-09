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


def _block(page: int, y: float, text: str, number: int, *, x0: float = 60.0, x1: float = 550.0) -> PdfBlock:
    return PdfBlock(
        page_number=page,
        bbox=(x0, y, x1, y + 18.0),
        text=text,
        block_number=number,
    )


def _pages(*, reverse_blocks: bool = False) -> tuple[PdfPage, ...]:
    specs = {
        13: [
            _block(13, 120.0, "SYNTHETIC DESIGN REQUIREMENTS", 1, x0=150.0, x1=462.0),
            _block(13, 220.0, "1.1 Scope 2   1.2 Materials 3", 2, x0=100.0, x1=510.0),
        ],
        14: [
            _block(14, 90.0, "1.1 Scope", 1),
            _block(14, 125.0, "Synthetic scope prose.", 2),
            _block(14, 165.0, "1.1.1 Definitions", 3),
            _block(
                14,
                205.0,
                "1.1.1.1 Alpha is a synthetic term. 1.1.1.2 Beta is another synthetic term.",
                4,
            ),
            _block(14, 260.0, "1.2 Materials", 5),
            _block(14, 295.0, "(a) First synthetic item", 6),
            _block(14, 330.0, "\ue000 + x = y", 7),
        ],
        170: [
            _block(170, 100.0, "Appendix A (Non-mandatory) SYNTHETIC PRACTICES", 1),
            _block(170, 145.0, "A.1 Purpose", 2),
            _block(170, 180.0, "Synthetic appendix prose.", 3),
        ],
        185: [
            _block(185, 100.0, "Appendix (Non-mandatory) SYNTHETIC LIMIT EQUATIONS", 1),
            _block(185, 145.0, ".1 Synthetic damaged locator", 2),
        ],
        198: [
            _block(198, 100.0, "Appendix N (Mandatory) SYNTHETIC LRFD", 1),
            _block(198, 145.0, "N.1 Scope", 2),
        ],
        203: [
            _block(203, 100.0, "REFERENCES", 1),
            _block(203, 145.0, "Synthetic reference entry.", 2),
        ],
    }
    pages: list[PdfPage] = []
    for page_number, blocks in specs.items():
        page_blocks = list(blocks)
        if reverse_blocks:
            page_blocks.reverse()
        pages.append(
            PdfPage(
                page_number=page_number,
                width=612.0,
                height=783.0,
                blocks=tuple(page_blocks),
            )
        )
    return tuple(pages)


def _evidence(*, reverse_blocks: bool = False) -> NdsLayoutEvidence:
    return NdsLayoutEvidence(
        ast_source=AstSourceIdentity(
            artifact_id=NDS_2018_ARTIFACT_ID,
            edition_id=NDS_2018_EDITION_ID,
        ),
        file_name="synthetic-nds-layout.pdf",
        pages=analyze_nds2018_pages(_pages(reverse_blocks=reverse_blocks)),
    )


def _flatten(node):
    yield node
    for child in node.children:
        yield from _flatten(child)


class Nds2018HierarchyTests(unittest.TestCase):
    def test_builds_conservative_hierarchy_with_native_locators_and_roles(self) -> None:
        ast = parse_nds2018_hierarchy(_evidence())
        nodes = list(_flatten(ast.root))
        by_locator = {node.locator: node for node in nodes}

        self.assertEqual(ast.source_artifact.artifact_id, NDS_2018_ARTIFACT_ID)
        self.assertEqual(ast.source_artifact.edition_id, NDS_2018_EDITION_ID)

        chapter = by_locator["chapter:1"]
        self.assertEqual(chapter.node_type, DocumentNodeType.CHAPTER)
        self.assertEqual(chapter.label, "SYNTHETIC DESIGN REQUIREMENTS")
        self.assertEqual(dict(chapter.attributes)["source_role"], "mandatory")

        self.assertEqual(by_locator["section:1.1"].node_type, DocumentNodeType.SECTION)
        self.assertEqual(by_locator["section:1.1.1"].node_type, DocumentNodeType.SUBSECTION)
        self.assertEqual(by_locator["definition:1.1.1.1"].node_type, DocumentNodeType.DEFINITION_ENTRY)
        self.assertEqual(by_locator["definition:1.1.1.2"].node_type, DocumentNodeType.DEFINITION_ENTRY)

        list_items = [node for node in nodes if node.node_type is DocumentNodeType.LIST_ITEM]
        self.assertEqual(len(list_items), 1)
        self.assertIn("First synthetic item", list_items[0].span.text)

        appendix_a = by_locator["appendix:A"]
        appendix_n = by_locator["appendix:N"]
        self.assertEqual(appendix_a.node_type, DocumentNodeType.APPENDIX)
        self.assertEqual(dict(appendix_a.attributes)["source_role"], "non_mandatory")
        self.assertEqual(dict(appendix_n.attributes)["source_role"], "mandatory")
        self.assertEqual(by_locator["section:A.1"].node_type, DocumentNodeType.SECTION)
        self.assertEqual(by_locator["section:N.1"].node_type, DocumentNodeType.SECTION)

        unsupported = [node for node in nodes if node.node_type is DocumentNodeType.UNSUPPORTED]
        self.assertTrue(any("Appendix (Non-mandatory)" in node.span.text for node in unsupported))
        self.assertTrue(any("\ue000" in node.span.text for node in unsupported))
        self.assertNotIn("appendix:I", by_locator)

        self.assertTrue(any(node.node_type is DocumentNodeType.HEADING and node.label == "REFERENCES" for node in ast.root.children))
        self.assertEqual(
            {diagnostic.code for diagnostic in ast.diagnostics},
            {"nds-appendix-locator-unresolved", "nds-nonprose-structure-deferred"},
        )

        forbidden = {DocumentNodeType.EQUATION, DocumentNodeType.TABLE, DocumentNodeType.FIGURE}
        self.assertFalse(any(node.node_type in forbidden for node in nodes))

    def test_chapter_contents_locators_are_not_promoted_to_body_sections(self) -> None:
        ast = parse_nds2018_hierarchy(_evidence())
        chapter = next(node for node in ast.root.children if node.locator == "chapter:1")
        direct_locators = [node.locator for node in chapter.children]

        self.assertEqual(direct_locators.count("section:1.1"), 1)
        self.assertEqual(direct_locators.count("section:1.2"), 1)
        chapter_contents = [
            node for node in chapter.children if dict(node.attributes).get("source_role") == "chapter_contents"
        ]
        self.assertEqual(len(chapter_contents), 1)
        self.assertIn("1.1 Scope 2", chapter_contents[0].span.text)

    def test_output_is_independent_of_caller_block_order(self) -> None:
        first = parse_nds2018_hierarchy(_evidence())
        repeated = parse_nds2018_hierarchy(_evidence(reverse_blocks=True))
        self.assertEqual(first.to_dict(), repeated.to_dict())


if __name__ == "__main__":
    unittest.main()
