import unittest

from building_code_ast.document_model import DocumentNodeType, DocumentSourceArtifact
from building_code_ast.document_validation import validate_document_ast
from building_code_ast.ingest.aci318 import parse_aci318_page
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfPage


ARTIFACT = DocumentSourceArtifact(
    artifact_id="aci-318-19:7b6b572e9e65",
    edition_id="aci-318-19:first-printing:2019-06",
)


def _page(*blocks: PdfBlock) -> PdfPage:
    return PdfPage(page_number=11, width=595.22, height=842.0, blocks=blocks)


def _block(x0: float, x1: float, y0: float, text: str, number: int) -> PdfBlock:
    return PdfBlock(
        page_number=11,
        bbox=(x0, y0, x1, y0 + 20.0),
        text=text,
        block_number=number,
    )


def _flatten(node):
    yield node
    for child in node.children:
        yield from _flatten(child)


class Aci318DocumentAstTests(unittest.TestCase):
    def test_preserves_normative_and_commentary_as_distinct_source_roles(self) -> None:
        page = _page(
            _block(165, 485, 60, "CHAPTER 1—SYNTHETIC GENERAL", 0),
            _block(60, 270, 90, "1.1 Synthetic scope", 1),
            _block(60, 270, 120, "1.1.1 Synthetic normative provision", 2),
            _block(325, 565, 90, "R1.1 Synthetic explanation", 3),
            _block(325, 565, 120, "R1.1.1 Synthetic commentary", 4),
        )

        first = parse_aci318_page(page, source_artifact=ARTIFACT, printed_page=9)
        second = parse_aci318_page(page, source_artifact=ARTIFACT, printed_page=9)
        nodes = list(_flatten(first.root))
        chapter = next(
            node
            for node in nodes
            if node.locator == "aci-318-19:publication-structure:chapter:1"
        )
        normative_section = next(
            node for node in nodes if node.locator == "aci-318-19:normative:1.1"
        )
        normative = next(
            node for node in nodes if node.locator == "aci-318-19:normative:1.1.1"
        )
        commentary_section = next(
            node for node in nodes if node.locator == "aci-318-19:commentary:R1.1"
        )
        commentary = next(
            node for node in nodes if node.locator == "aci-318-19:commentary:R1.1.1"
        )

        self.assertEqual(dict(chapter.attributes)["source_role"], "publication_structure")
        self.assertIn(normative_section, chapter.children)
        self.assertIn(commentary_section, chapter.children)
        self.assertIn(normative, normative_section.children)
        self.assertIn(commentary, commentary_section.children)
        self.assertEqual(dict(normative.attributes)["source_role"], "normative")
        self.assertEqual(dict(commentary.attributes)["source_role"], "commentary")
        self.assertNotEqual(normative.node_id, commentary.node_id)
        self.assertEqual(dict(commentary.attributes)["corresponds_to"], normative.locator)
        self.assertEqual(dict(normative.attributes)["pdf_page"], "11")
        self.assertEqual(dict(normative.attributes)["printed_page"], "9")
        self.assertEqual(
            dict(normative.attributes)["bbox"],
            "60.000,120.000,270.000,140.000",
        )
        self.assertEqual(first.to_dict(), second.to_dict())
        validate_document_ast(first)

    def test_table_keeps_source_role_without_reconstructing_cells(self) -> None:
        page = _page(
            _block(60, 275, 90, "5.3 Synthetic loads", 1),
            _block(60, 285, 130, "Table 5.3.1—Synthetic matrix", 2),
            _block(325, 565, 90, "R5.3 Synthetic explanation", 3),
            _block(325, 565, 130, "Table R5.3.1—Synthetic commentary matrix", 4),
        )

        ast = parse_aci318_page(page, source_artifact=ARTIFACT, printed_page=51)
        tables = [node for node in _flatten(ast.root) if node.node_type is DocumentNodeType.TABLE]

        normative = next(
            node for node in tables if node.locator == "aci-318-19:normative:table:5.3.1"
        )
        commentary = next(
            node
            for node in tables
            if node.locator == "aci-318-19:commentary:table:R5.3.1"
        )
        self.assertEqual(dict(normative.attributes)["source_role"], "normative")
        self.assertEqual(dict(commentary.attributes)["source_role"], "commentary")
        self.assertEqual(normative.children, ())
        self.assertEqual(commentary.children, ())
        validate_document_ast(ast)

    def test_midline_source_role_marker_is_not_promoted(self) -> None:
        page = _page(
            _block(60, 270, 130, "1.1 Synthetic scope", 1),
            _block(165, 485, 105, "CODE COMMENTARY", 2),
        )

        ast = parse_aci318_page(page, source_artifact=ARTIFACT, printed_page=9)
        unsupported = next(
            node
            for node in _flatten(ast.root)
            if node.node_type is DocumentNodeType.UNSUPPORTED
        )

        self.assertEqual(dict(unsupported.attributes)["source_role"], "unresolved")
        self.assertTrue(
            any(
                diagnostic.code == "aci318_ambiguous_source_role"
                for diagnostic in ast.diagnostics
            )
        )
        validate_document_ast(ast)

    def test_duplicate_locator_only_glyph_fragment_is_not_a_second_structure(self) -> None:
        page = _page(
            _block(325, 565, 235, "R4.2—Synthetic materials", 1),
            _block(348, 369, 386, "R4.2", 2),
        )

        ast = parse_aci318_page(page, source_artifact=ARTIFACT, printed_page=51)
        matches = [
            node
            for node in _flatten(ast.root)
            if node.locator == "aci-318-19:commentary:R4.2"
        ]

        self.assertEqual(len(matches), 1)
        self.assertTrue(
            any(
                diagnostic.code == "aci318_duplicate_locator_fragment"
                for diagnostic in ast.diagnostics
            )
        )
        validate_document_ast(ast)


if __name__ == "__main__":
    unittest.main()
