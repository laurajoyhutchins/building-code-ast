from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.evidence.model import publication_state_id
from building_code_ast.ingest.ashrae621_2016 import (
    ASHRAE_62_1_2016_ARTIFACT,
    ASHRAE_62_1_2016_PUBLICATION,
    Ashrae621Observation,
    parse_ashrae621_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock


def _observation(
    text: str,
    *,
    page: int,
    printed_page: str | None,
    block_number: int,
    y: float,
    hint: str | None = None,
    locator: str | None = None,
) -> Ashrae621Observation:
    return Ashrae621Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(72.0, y, 540.0, y + 18.0),
            text=text,
            block_number=block_number,
        ),
        printed_page=printed_page,
        structure_hint=hint,
        native_locator=locator,
    )


class Ashrae621DocumentAstTests(unittest.TestCase):
    def test_exact_artifact_and_publication_state_preserve_incorporated_addenda(self) -> None:
        self.assertEqual(
            ASHRAE_62_1_2016_ARTIFACT.artifact_id,
            "sha256:a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759",
        )
        self.assertEqual(
            ASHRAE_62_1_2016_PUBLICATION.addenda_set,
            "ashrae-62.1-2013:addenda-a,c,d,e,f,g,h,i,j,k,p,q,r,s",
        )
        self.assertEqual(
            ASHRAE_62_1_2016_PUBLICATION.correction_set,
            "unresolved:no-incorporated-correction-layer-established",
        )
        self.assertEqual(
            ASHRAE_62_1_2016_ARTIFACT.edition_id,
            publication_state_id(ASHRAE_62_1_2016_PUBLICATION),
        )

    def test_structural_slice_preserves_procedure_hierarchy_coordinates_and_explicit_nonprose(self) -> None:
        observations = (
            _observation("6. PROCEDURES", page=20, printed_page="18", block_number=1, y=80),
            _observation("6.2 Ventilation Rate Procedure", page=20, printed_page="18", block_number=2, y=110),
            _observation("6.2.1 Synthetic Requirement", page=20, printed_page="18", block_number=3, y=140),
            _observation("Synthetic mandatory prose.", page=20, printed_page="18", block_number=4, y=170),
            _observation("Table 6.2.1 Synthetic Rates", page=20, printed_page="18", block_number=5, y=200),
            _observation(
                "Synthetic equation expression (6-1)",
                page=20,
                printed_page="18",
                block_number=6,
                y=230,
                hint="equation",
                locator="6-1",
            ),
            _observation(
                "Synthetic graphical region",
                page=20,
                printed_page="18",
                block_number=7,
                y=260,
                hint="graphical_region",
            ),
        )

        ast = parse_ashrae621_2016_observations(observations)
        section = ast.root.children[0]
        procedure = section.children[0]
        nested = procedure.children[0]
        table = next(child for child in nested.children if child.node_type is DocumentNodeType.TABLE)
        equation = next(child for child in nested.children if child.node_type is DocumentNodeType.EQUATION)
        graphical = next(
            child for child in nested.children if child.node_type is DocumentNodeType.GRAPHICAL_REGION
        )

        self.assertEqual(section.locator, "section:6")
        self.assertEqual(procedure.locator, "section:6.2")
        self.assertEqual(procedure.label, "Ventilation Rate Procedure")
        self.assertEqual(nested.locator, "section:6.2.1")
        self.assertEqual(dict(nested.attributes)["source_role"], "mandatory")
        self.assertEqual(table.locator, "table:6.2.1")
        self.assertEqual(equation.locator, "equation:6-1")
        self.assertEqual(dict(table.attributes)["coordinate_space"], "pdf_points")
        self.assertEqual(dict(table.attributes)["pdf_page"], "20")
        self.assertEqual(dict(table.attributes)["printed_page"], "18")
        self.assertEqual(dict(table.attributes)["bbox_pdf_points"], "72.000,200.000,540.000,218.000")
        self.assertEqual(graphical.node_type, DocumentNodeType.GRAPHICAL_REGION)
        self.assertEqual(dict(graphical.attributes)["semantic_status"], "unsupported")
        self.assertEqual(ast.diagnostics[0].code, "unsupported-ashrae621-graphical-semantics")

    def test_appendix_roles_are_exactly_source_classified(self) -> None:
        normative = parse_ashrae621_2016_observations(
            (
                _observation(
                    "NORMATIVE APPENDIX B SYNTHETIC MATERIAL",
                    page=44,
                    printed_page="42",
                    block_number=1,
                    y=80,
                ),
                _observation("Synthetic appendix prose.", page=44, printed_page="42", block_number=2, y=110),
            )
        )
        informative = parse_ashrae621_2016_observations(
            (
                _observation(
                    "INFORMATIVE APPENDIX E SYNTHETIC MATERIAL",
                    page=50,
                    printed_page="48",
                    block_number=1,
                    y=80,
                ),
                _observation("Synthetic calculation discussion.", page=50, printed_page="48", block_number=2, y=110),
            )
        )

        self.assertEqual(dict(normative.root.children[0].attributes)["source_role"], "mandatory")
        self.assertEqual(dict(informative.root.children[0].attributes)["source_role"], "informative")

    def test_appendix_heading_conflicting_with_retained_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "appendix A is mandatory in the retained publication"):
            parse_ashrae621_2016_observations(
                (
                    _observation(
                        "INFORMATIVE APPENDIX A SYNTHETIC MATERIAL",
                        page=40,
                        printed_page="38",
                        block_number=1,
                        y=80,
                    ),
                )
            )

    def test_unresolved_unhinted_math_stays_prose_instead_of_becoming_executable_semantics(self) -> None:
        ast = parse_ashrae621_2016_observations(
            (
                _observation("6. PROCEDURES", page=20, printed_page="18", block_number=1, y=80),
                _observation("Synthetic x = y / z expression", page=20, printed_page="18", block_number=2, y=110),
            )
        )
        self.assertEqual(ast.root.children[0].children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_discovery_order_does_not_change_output_or_ids(self) -> None:
        observations = (
            _observation("6. PROCEDURES", page=20, printed_page="18", block_number=1, y=80),
            _observation("6.3 Indoor Air Quality (IAQ) Procedure", page=20, printed_page="18", block_number=2, y=110),
            _observation("Synthetic mandatory prose.", page=20, printed_page="18", block_number=3, y=140),
        )
        self.assertEqual(
            parse_ashrae621_2016_observations(observations).to_dict(),
            parse_ashrae621_2016_observations(reversed(observations)).to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
