from __future__ import annotations

import unittest

from building_code_ast import DocumentNodeType, DocumentSourceArtifact, validate_document_ast
from building_code_ast.ingest.pdf_layout import PdfBlock
from building_code_ast.ingest.tms402_16 import Tms402Observation, parse_tms402_16_observations


ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d",
    edition_id="2016-second-printing-errata-2018-10-22",
    publication_component_id="tms-402-16",
)


def _observation(
    text: str,
    *,
    y: float,
    role: str = "normative",
    hint: str | None = None,
    native_locator: str | None = None,
) -> Tms402Observation:
    return Tms402Observation(
        block=PdfBlock(
            page_number=67,
            bbox=(72.0 if role == "normative" else 330.0, y, 280.0 if role == "normative" else 540.0, y + 18.0),
            text=text,
            block_number=int(y),
        ),
        printed_page="C-1",
        source_role=role,
        text_origin="ocr",
        structure_hint=hint,
        native_locator=native_locator,
    )


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


class Tms402DocumentAstTests(unittest.TestCase):
    def test_builds_part_chapter_and_decimal_section_hierarchy(self) -> None:
        observations = [
            _observation("Synthetic subsection content.", y=190.0),
            _observation("1.1.1 Sample subsection", y=170.0),
            _observation("CHAPTER 1 SAMPLE CHAPTER", y=110.0),
            _observation("PART 1: SAMPLE PART", y=80.0),
            _observation("1.1 — Sample section", y=140.0),
        ]

        ast = parse_tms402_16_observations(observations, source_artifact=ARTIFACT)

        validate_document_ast(ast)
        part = ast.root.children[0]
        chapter = part.children[0]
        section = chapter.children[0]
        subsection = section.children[0]

        self.assertEqual(part.node_type, DocumentNodeType.HEADING)
        self.assertEqual(part.locator, "part:1")
        self.assertEqual(dict(part.attributes)["hierarchy_role"], "part")
        self.assertEqual(chapter.node_type, DocumentNodeType.CHAPTER)
        self.assertEqual(chapter.locator, "chapter:1")
        self.assertEqual(section.node_type, DocumentNodeType.SECTION)
        self.assertEqual(section.locator, "section:1.1")
        self.assertEqual(subsection.node_type, DocumentNodeType.SUBSECTION)
        self.assertEqual(subsection.locator, "section:1.1.1")
        self.assertEqual(subsection.children[0].node_type, DocumentNodeType.PARAGRAPH)

    def test_preserves_commentary_role_without_promoting_it_to_normative_hierarchy(self) -> None:
        observations = [
            _observation("PART 1: SAMPLE PART", y=80.0),
            _observation("CHAPTER 1 SAMPLE CHAPTER", y=110.0),
            _observation("1.1 — Sample section", y=140.0),
            _observation(
                "Commentary observation for the same native locator.",
                y=150.0,
                role="commentary",
                native_locator="1.1",
            ),
        ]

        ast = parse_tms402_16_observations(observations, source_artifact=ARTIFACT)
        nodes = list(_walk(ast.root))
        commentary = [
            node
            for node in nodes
            if dict(node.attributes).get("source_role") == "commentary"
        ]

        self.assertEqual(len(commentary), 1)
        self.assertEqual(commentary[0].node_type, DocumentNodeType.PARAGRAPH)
        self.assertEqual(dict(commentary[0].attributes)["native_locator"], "1.1")
        self.assertEqual(
            [node.locator for node in nodes].count("section:1.1"),
            1,
        )

    def test_records_pdf_coordinates_printed_page_and_ocr_provenance(self) -> None:
        ast = parse_tms402_16_observations(
            [
                _observation("PART 1: SAMPLE PART", y=80.0),
                _observation("CHAPTER 1 SAMPLE CHAPTER", y=110.0),
            ],
            source_artifact=ARTIFACT,
        )

        attrs = dict(ast.root.children[0].attributes)
        self.assertEqual(attrs["pdf_page"], "67")
        self.assertEqual(attrs["printed_page"], "C-1")
        self.assertEqual(attrs["coordinate_space"], "pdf_points")
        self.assertEqual(attrs["text_origin"], "ocr")
        self.assertEqual(attrs["source_role"], "normative")
        self.assertIn("bbox_pdf_points", attrs)

    def test_graphical_region_is_retained_with_visible_unsupported_diagnostic(self) -> None:
        observations = [
            _observation("PART 1: SAMPLE PART", y=80.0),
            _observation("CHAPTER 1 SAMPLE CHAPTER", y=110.0),
            _observation("1.1 — Sample section", y=140.0),
            _observation("[synthetic diagram region]", y=180.0, hint="graphical_region"),
        ]

        ast = parse_tms402_16_observations(observations, source_artifact=ARTIFACT)
        nodes = list(_walk(ast.root))
        graphical = [node for node in nodes if node.node_type is DocumentNodeType.GRAPHICAL_REGION]

        self.assertEqual(len(graphical), 1)
        self.assertEqual(dict(graphical[0].attributes)["semantic_status"], "unsupported")
        self.assertEqual(ast.diagnostics[0].code, "unsupported-tms402-graphical-semantics")

    def test_repeated_runs_ignore_caller_observation_order(self) -> None:
        observations = [
            _observation("PART 1: SAMPLE PART", y=80.0),
            _observation("CHAPTER 1 SAMPLE CHAPTER", y=110.0),
            _observation("1.1 — Sample section", y=140.0),
            _observation("Synthetic body text.", y=170.0),
        ]

        first = parse_tms402_16_observations(observations, source_artifact=ARTIFACT)
        second = parse_tms402_16_observations(reversed(observations), source_artifact=ARTIFACT)

        self.assertEqual(first.to_dict(), second.to_dict())

    def test_rejects_artifact_without_tms402_component_identity(self) -> None:
        combined_only = DocumentSourceArtifact(
            artifact_id=ARTIFACT.artifact_id,
            edition_id=ARTIFACT.edition_id,
        )
        tms602 = DocumentSourceArtifact(
            artifact_id=ARTIFACT.artifact_id,
            edition_id=ARTIFACT.edition_id,
            publication_component_id="tms-602-16",
        )
        observations = [_observation("PART 1: SAMPLE PART", y=80.0)]

        for artifact in (combined_only, tms602):
            with self.subTest(component=artifact.publication_component_id):
                with self.assertRaisesRegex(ValueError, "tms-402-16"):
                    parse_tms402_16_observations(observations, source_artifact=artifact)


if __name__ == "__main__":
    unittest.main()
