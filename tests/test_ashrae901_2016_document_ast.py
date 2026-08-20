from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType
from building_code_ast.ingest.ashrae901_2016 import (
    ASHRAE_90_1_2016_ARTIFACT,
    ASHRAE_90_1_2016_PUBLICATION,
    Ashrae901Observation,
    parse_ashrae901_2016_observations,
)
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLine, PdfSpan


def _observation(
    text: str,
    *,
    page: int,
    printed_page: str,
    block_number: int,
    y: float,
    hint: str | None = None,
    locator: str | None = None,
    font: str | None = None,
    size: float | None = None,
) -> Ashrae901Observation:
    lines = ()
    if font is not None and size is not None:
        span = PdfSpan(
            bbox=(72.0, y, 540.0, y + size),
            text=text,
            font=font,
            size=size,
            flags=0,
        )
        lines = (PdfLine(bbox=span.bbox, spans=(span,)),)
    return Ashrae901Observation(
        block=PdfBlock(
            page_number=page,
            bbox=(72.0, y, 540.0, y + 18.0),
            text=text,
            block_number=block_number,
            lines=lines,
        ),
        printed_page=printed_page,
        structure_hint=hint,
        native_locator=locator,
    )


class Ashrae901DocumentAstTests(unittest.TestCase):
    def test_exact_artifact_and_publication_state_include_addenda_and_correction_state(self) -> None:
        self.assertEqual(
            ASHRAE_90_1_2016_ARTIFACT.artifact_id,
            "sha256:275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162",
        )
        self.assertEqual(
            ASHRAE_90_1_2016_PUBLICATION.addenda_set,
            "ashrae-90.1-2013:addenda-enumerated-in-90.1-2016-appendix-h",
        )
        self.assertEqual(
            ASHRAE_90_1_2016_PUBLICATION.correction_set,
            "unresolved:no-incorporated-post-publication-correction-established",
        )
        self.assertEqual(
            ASHRAE_90_1_2016_ARTIFACT.edition_id,
            ASHRAE_90_1_2016_PUBLICATION.publication_id,
        )

    def test_structural_slice_preserves_hierarchy_role_coordinates_table_and_unsupported(self) -> None:
        observations = (
            _observation(
                "6 SYNTHETIC SYSTEMS",
                page=12,
                printed_page="8",
                block_number=1,
                y=80,
                font="Helvetica-Bold",
                size=11.0,
            ),
            _observation(
                "6.1 Synthetic Scope",
                page=12,
                printed_page="8",
                block_number=2,
                y=110,
                font="Helvetica-Bold",
                size=10.0,
            ),
            _observation(
                "6.1.1 Synthetic Subsection",
                page=12,
                printed_page="8",
                block_number=3,
                y=140,
                font="Helvetica-Bold",
                size=10.0,
            ),
            _observation("Synthetic mandatory prose.", page=12, printed_page="8", block_number=4, y=170),
            _observation("Table 6.1.1-1 Synthetic Limits", page=12, printed_page="8", block_number=5, y=200),
            _observation(
                "Synthetic graphical region",
                page=12,
                printed_page="8",
                block_number=6,
                y=230,
                hint="graphical_region",
            ),
        )

        ast = parse_ashrae901_2016_observations(observations)
        section = ast.root.children[0]
        subsection = section.children[0]
        nested = subsection.children[0]
        table = next(child for child in nested.children if child.node_type is DocumentNodeType.TABLE)
        graphical = next(
            child for child in nested.children if child.node_type is DocumentNodeType.GRAPHICAL_REGION
        )

        self.assertEqual(section.locator, "section:6")
        self.assertEqual(subsection.locator, "section:6.1")
        self.assertEqual(nested.locator, "section:6.1.1")
        self.assertEqual(dict(nested.attributes)["source_role"], "mandatory")
        self.assertEqual(table.locator, "table:6.1.1-1")
        self.assertEqual(dict(table.attributes)["coordinate_space"], "pdf_points")
        self.assertEqual(dict(table.attributes)["pdf_page"], "12")
        self.assertEqual(dict(table.attributes)["printed_page"], "8")
        self.assertEqual(dict(table.attributes)["bbox_pdf_points"], "72.000,200.000,540.000,218.000")
        self.assertEqual(graphical.node_type, DocumentNodeType.GRAPHICAL_REGION)
        self.assertEqual(ast.diagnostics[0].code, "unsupported-ashrae901-graphical-semantics")

    def test_appendix_role_comes_from_retained_publication_classification(self) -> None:
        mandatory = parse_ashrae901_2016_observations(
            (
                _observation(
                    "NORMATIVE APPENDIX A SYNTHETIC MATERIAL",
                    page=300,
                    printed_page="296",
                    block_number=1,
                    y=80,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation("Synthetic appendix prose.", page=300, printed_page="296", block_number=2, y=110),
            )
        )
        informative = parse_ashrae901_2016_observations(
            (
                _observation(
                    "INFORMATIVE APPENDIX E SYNTHETIC MATERIAL",
                    page=302,
                    printed_page="298",
                    block_number=1,
                    y=80,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation("Synthetic explanatory prose.", page=302, printed_page="298", block_number=2, y=110),
            )
        )

        self.assertEqual(dict(mandatory.root.children[0].attributes)["source_role"], "mandatory")
        self.assertEqual(dict(informative.root.children[0].attributes)["source_role"], "informative")

    def test_appendix_native_headings_use_source_typography_and_nest_under_appendix(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "NORMATIVE APPENDIX A SYNTHETIC MATERIAL",
                    page=300,
                    printed_page="296",
                    block_number=1,
                    y=80,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation(
                    "A1 Synthetic Appendix Section",
                    page=300,
                    printed_page="296",
                    block_number=2,
                    y=110,
                    font="Helvetica-Bold",
                    size=10.0,
                ),
                _observation(
                    "A1.1 Synthetic Appendix Subsection",
                    page=300,
                    printed_page="296",
                    block_number=3,
                    y=140,
                    font="Helvetica-Bold",
                    size=10.0,
                ),
                _observation(
                    "Synthetic appendix prose.",
                    page=300,
                    printed_page="296",
                    block_number=4,
                    y=170,
                ),
            )
        )

        appendix = ast.root.children[0]
        section = appendix.children[0]
        subsection = section.children[0]
        prose = subsection.children[0]
        self.assertEqual(appendix.locator, "appendix:A")
        self.assertEqual(section.locator, "section:A1")
        self.assertEqual(section.node_type, DocumentNodeType.SUBSECTION)
        self.assertEqual(subsection.locator, "section:A1.1")
        self.assertEqual(dict(section.attributes)["source_role"], "mandatory")
        self.assertEqual(dict(subsection.attributes)["source_role"], "mandatory")
        self.assertEqual(prose.node_type, DocumentNodeType.PARAGRAPH)

    def test_appendix_locator_with_wrong_typography_remains_prose(self) -> None:
        ast = parse_ashrae901_2016_observations(
            (
                _observation(
                    "INFORMATIVE APPENDIX E SYNTHETIC MATERIAL",
                    page=302,
                    printed_page="298",
                    block_number=1,
                    y=80,
                    font="Helvetica-Bold",
                    size=11.0,
                ),
                _observation(
                    "E1 Synthetic False Positive",
                    page=302,
                    printed_page="298",
                    block_number=2,
                    y=110,
                    font="Helvetica",
                    size=10.0,
                ),
            )
        )
        self.assertEqual(ast.root.children[0].children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_appendix_heading_that_conflicts_with_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "appendix A is mandatory in the retained publication"):
            parse_ashrae901_2016_observations(
                (
                    _observation(
                        "INFORMATIVE APPENDIX A SYNTHETIC MATERIAL",
                        page=300,
                        printed_page="296",
                        block_number=1,
                        y=80,
                        font="Helvetica-Bold",
                        size=11.0,
                    ),
                )
            )

    def test_discovery_order_does_not_change_output_or_ids(self) -> None:
        observations = (
            _observation(
                "6 SYNTHETIC SYSTEMS",
                page=12,
                printed_page="8",
                block_number=1,
                y=80,
                font="Helvetica-Bold",
                size=11.0,
            ),
            _observation(
                "6.1 Synthetic Scope",
                page=12,
                printed_page="8",
                block_number=2,
                y=110,
                font="Helvetica-Bold",
                size=10.0,
            ),
            _observation("Synthetic mandatory prose.", page=12, printed_page="8", block_number=3, y=140),
        )
        self.assertEqual(
            parse_ashrae901_2016_observations(observations).to_dict(),
            parse_ashrae901_2016_observations(reversed(observations)).to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
