from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.document_validation import validate_document_ast
from building_code_ast.ingest.ashrae901_2016 import (
    ASHRAE_90_1_2016_ARTIFACT_ID,
    ASHRAE_90_1_2016_EDITION_ID,
    Ashrae901Appendix,
    Ashrae901Region,
    Ashrae901Section,
    Ashrae901Structure,
    build_ashrae901_document_ast,
)


class Ashrae901DocumentAstTests(unittest.TestCase):
    def test_publication_identity_is_exact_source_scoped(self) -> None:
        self.assertEqual(
            ASHRAE_90_1_2016_ARTIFACT_ID,
            "sha256:275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162",
        )
        self.assertTrue(ASHRAE_90_1_2016_EDITION_ID.startswith("publication:"))

    def test_structural_slice_preserves_hierarchy_role_coordinates_and_table(self) -> None:
        source = (
            "6 Systems\n"
            "6.1 General\n"
            "Synthetic mandatory prose.\n"
            "Table 6.1-A Synthetic Limits\n"
            "A Normative Appendix\n"
            "Synthetic appendix prose.\n"
        )
        table_start = source.index("Table 6.1-A")
        appendix_start = source.index("A Normative Appendix")
        structure = Ashrae901Structure(
            source_text=source,
            sections=(
                Ashrae901Section("6", 0, appendix_start, 12, 8, (72, 90, 540, 700)),
                Ashrae901Section("6.1", source.index("6.1"), appendix_start, 12, 8, (72, 110, 540, 700)),
            ),
            tables=(
                Ashrae901Region("Table 6.1-A", table_start, appendix_start, 12, 8, (72, 220, 540, 360)),
            ),
            appendices=(
                Ashrae901Appendix("A", appendix_start, len(source), 300, 296, (72, 90, 540, 700)),
            ),
            unsupported=(
                Ashrae901Region("figure:synthetic", source.index("Synthetic mandatory prose."), table_start, 12, 8, (72, 180, 540, 210)),
            ),
        )

        ast = build_ashrae901_document_ast(structure)
        validate_document_ast(ast)

        section = ast.root.children[0]
        subsection = section.children[0]
        table = subsection.children[0]
        unsupported = subsection.children[1]
        appendix = ast.root.children[1]

        self.assertEqual(section.node_type, DocumentNodeType.SECTION)
        self.assertEqual(subsection.node_type, DocumentNodeType.SUBSECTION)
        self.assertEqual(table.node_type, DocumentNodeType.TABLE)
        self.assertEqual(unsupported.node_type, DocumentNodeType.UNSUPPORTED)
        self.assertEqual(dict(subsection.attributes)["source_role"], "mandatory")
        self.assertEqual(dict(appendix.attributes)["source_role"], "mandatory")
        self.assertEqual(dict(table.attributes)["coordinate_space"], "pdf_points")
        self.assertEqual(dict(table.attributes)["pdf_page"], "12")
        self.assertEqual(dict(table.attributes)["printed_page"], "8")
        self.assertEqual(dict(table.attributes)["bbox"], "72,220,540,360")
        self.assertTrue(ast.diagnostics)

    def test_informative_appendix_role_is_source_backed(self) -> None:
        source = "B Informative Appendix\nSynthetic explanatory material.\n"
        ast = build_ashrae901_document_ast(
            Ashrae901Structure(
                source_text=source,
                appendices=(
                    Ashrae901Appendix("B", 0, len(source), 301, 297, (72, 90, 540, 700)),
                ),
            )
        )

        appendix = ast.root.children[0]
        self.assertEqual(dict(appendix.attributes)["source_role"], "informative")

    def test_deterministic_rerun_is_byte_stable(self) -> None:
        source = "6 Systems\n6.1 General\nSynthetic mandatory prose.\n"
        structure = Ashrae901Structure(
            source_text=source,
            sections=(
                Ashrae901Section("6", 0, len(source), 12, 8, (72, 90, 540, 700)),
                Ashrae901Section("6.1", source.index("6.1"), len(source), 12, 8, (72, 110, 540, 700)),
            ),
        )
        self.assertEqual(
            build_ashrae901_document_ast(structure).to_dict(),
            build_ashrae901_document_ast(structure).to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
