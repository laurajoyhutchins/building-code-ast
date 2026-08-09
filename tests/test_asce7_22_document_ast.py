from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentNodeType, DocumentSourceArtifact
from building_code_ast.ingest.asce7_22 import Asce7Observation, parse_asce7_22_observations
from building_code_ast.ingest.pdf_layout import PdfBlock


ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0",
    edition_id="asce-7-22",
)


def _observation(
    text: str,
    *,
    block_number: int,
    y: float,
    x0: float = 72.0,
    x1: float = 280.0,
    hint: str | None = None,
    locator: str | None = None,
) -> Asce7Observation:
    return Asce7Observation(
        block=PdfBlock(
            page_number=133,
            bbox=(x0, y, x1, y + 16.0),
            text=text,
            block_number=block_number,
        ),
        printed_page="71",
        structure_hint=hint,
        native_locator=locator,
    )


def _identities(ast):
    result = {}

    def walk(node):
        result[node.locator] = node.node_id
        for child in node.children:
            walk(child)

    walk(ast.root)
    return result


class Asce722DocumentAstTests(unittest.TestCase):
    def _slice(self) -> tuple[Asce7Observation, ...]:
        return (
            _observation("CHAPTER 8 SYNTHETIC LOADS", block_number=1, y=80.0, x0=274.0, x1=350.0),
            _observation("8.1 SYNTHETIC DEFINITIONS", block_number=2, y=110.0),
            _observation("8.1.1 Scope", block_number=3, y=140.0),
            _observation("Synthetic prose for structural testing.", block_number=4, y=170.0),
            _observation("x = y + z (8.2-1)", block_number=5, y=200.0),
            _observation("Table 8.2-1. Synthetic tabular region", block_number=6, y=230.0),
            _observation("Figure 8.2-1. Synthetic figure region", block_number=7, y=260.0),
            _observation("Synthetic hazard map region", block_number=8, y=290.0, hint="graphical_region"),
        )

    def test_builds_hierarchy_with_non_prose_structures_and_coordinates(self) -> None:
        ast = parse_asce7_22_observations(self._slice(), source_artifact=ARTIFACT)

        chapter = ast.root.children[0]
        section = chapter.children[0]
        subsection = section.children[0]
        leaf_types = {child.node_type for child in subsection.children}

        self.assertEqual(chapter.node_type, DocumentNodeType.CHAPTER)
        self.assertEqual(section.locator, "section:8.1")
        self.assertEqual(subsection.locator, "section:8.1.1")
        self.assertEqual(
            leaf_types,
            {
                DocumentNodeType.PARAGRAPH,
                DocumentNodeType.EQUATION,
                DocumentNodeType.TABLE,
                DocumentNodeType.FIGURE,
                DocumentNodeType.GRAPHICAL_REGION,
            },
        )
        equation = next(child for child in subsection.children if child.node_type is DocumentNodeType.EQUATION)
        attrs = dict(equation.attributes)
        self.assertEqual(equation.locator, "equation:8.2-1")
        self.assertEqual(attrs["coordinate_space"], "pdf_points")
        self.assertEqual(attrs["pdf_page"], "133")
        self.assertEqual(attrs["printed_page"], "71")
        self.assertEqual(attrs["bbox_pdf_points"], "72.000,200.000,280.000,216.000")
        self.assertEqual(ast.diagnostics[0].code, "unsupported-asce-graphical-semantics")

    def test_discovery_order_does_not_change_durable_ids_or_output(self) -> None:
        ordered = self._slice()
        first = parse_asce7_22_observations(ordered, source_artifact=ARTIFACT)
        repeated = parse_asce7_22_observations(reversed(ordered), source_artifact=ARTIFACT)

        self.assertEqual(_identities(first), _identities(repeated))
        self.assertEqual(first.to_dict(), repeated.to_dict())

    def test_extraction_block_number_is_not_part_of_unnumbered_identity(self) -> None:
        first = (
            _observation("CHAPTER 8 SYNTHETIC LOADS", block_number=1, y=80.0, x0=274.0, x1=350.0),
            _observation("8.1 Scope", block_number=2, y=110.0),
            _observation("Synthetic prose.", block_number=3, y=140.0),
        )
        changed_block_numbers = (
            _observation("CHAPTER 8 SYNTHETIC LOADS", block_number=101, y=80.0, x0=274.0, x1=350.0),
            _observation("8.1 Scope", block_number=102, y=110.0),
            _observation("Synthetic prose.", block_number=103, y=140.0),
        )

        parsed_first = parse_asce7_22_observations(first, source_artifact=ARTIFACT)
        parsed_changed = parse_asce7_22_observations(changed_block_numbers, source_artifact=ARTIFACT)

        self.assertEqual(_identities(parsed_first), _identities(parsed_changed))
        paragraph = parsed_first.root.children[0].children[0].children[0]
        self.assertNotIn("block-3", paragraph.locator)
        self.assertIn("bbox-", paragraph.locator)

    def test_two_column_order_keeps_left_column_before_right_column(self) -> None:
        observations = (
            _observation("CHAPTER 8 SYNTHETIC LOADS", block_number=1, y=80.0, x0=274.0, x1=350.0),
            _observation("8.1 Left Section", block_number=2, y=220.0, x0=57.0, x1=280.0),
            _observation("Left column later text.", block_number=3, y=700.0, x0=57.0, x1=280.0),
            _observation("8.2 Right Section", block_number=4, y=210.0, x0=323.0, x1=567.0),
            _observation("Right column text.", block_number=5, y=240.0, x0=323.0, x1=567.0),
        )

        ast = parse_asce7_22_observations(observations, source_artifact=ARTIFACT)
        chapter = ast.root.children[0]

        self.assertEqual([child.locator for child in chapter.children], ["section:8.1", "section:8.2"])
        self.assertIn("Left column later text.", chapter.children[0].span.text)
        self.assertIn("Right column text.", chapter.children[1].span.text)

    def test_page_footer_is_not_promoted_to_document_structure(self) -> None:
        observations = self._slice() + (
            _observation(
                "Synthetic publication footer 71",
                block_number=99,
                y=755.0,
                x0=57.0,
                x1=567.0,
            ),
        )

        ast = parse_asce7_22_observations(observations, source_artifact=ARTIFACT)

        self.assertNotIn("Synthetic publication footer 71", ast.source_text)

    def test_explicit_non_prose_hint_requires_publication_locator_when_text_has_none(self) -> None:
        observation = _observation("x = y", block_number=9, y=320.0, hint="equation")
        with self.assertRaisesRegex(ValueError, "equation observations require a publication-native locator"):
            parse_asce7_22_observations((observation,), source_artifact=ARTIFACT)


if __name__ == "__main__":
    unittest.main()
