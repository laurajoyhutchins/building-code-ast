from __future__ import annotations

import unittest

from building_code_ast.aisc360_page_coverage import (
    Aisc360PageObservation,
    build_aisc360_page_coverage_ast,
)
from building_code_ast.document_model import DocumentNodeType
from building_code_ast.document_validation import validate_document_ast


class Aisc360PageCoverageTests(unittest.TestCase):
    def test_every_page_survives_without_inventing_hierarchy_or_ocr_text(self) -> None:
        ast = build_aisc360_page_coverage_ast(
            (
                Aisc360PageObservation(1, "first page text"),
                Aisc360PageObservation(2, None),
                Aisc360PageObservation(3, None),
                Aisc360PageObservation(4, "fourth page text"),
            ),
            expected_page_count=4,
        )

        validate_document_ast(ast)
        self.assertEqual(ast.source_text, "first page textfourth page text")
        self.assertEqual(ast.source_artifact.edition_id, "aisc-scm-15")
        self.assertEqual(ast.source_artifact.publication_component_id, "ansi-aisc-360-16")
        self.assertEqual(len(ast.root.children), 4)
        self.assertTrue(all(node.node_type is DocumentNodeType.UNSUPPORTED for node in ast.root.children))
        self.assertEqual([node.locator for node in ast.root.children], ["page:1", "page:2", "page:3", "page:4"])

        first, second, third, fourth = ast.root.children
        self.assertEqual(first.span.text, "first page text")
        self.assertEqual(first.span.start, 0)
        self.assertEqual(first.span.end, len("first page text"))
        self.assertEqual(dict(first.attributes)["source_kind"], "embedded_text")

        self.assertEqual(second.span.text, "")
        self.assertEqual(second.span.start, len("first page text"))
        self.assertEqual(second.span.end, second.span.start)
        self.assertEqual(dict(second.attributes)["source_kind"], "image_only")
        self.assertEqual(third.span, second.span)

        self.assertEqual(fourth.span.text, "fourth page text")
        self.assertEqual(fourth.span.start, len("first page text"))
        self.assertEqual(fourth.span.end, len(ast.source_text))

    def test_page_observations_must_cover_exact_component_denominator_once(self) -> None:
        with self.assertRaisesRegex(ValueError, "each one-based component page exactly once"):
            build_aisc360_page_coverage_ast(
                (
                    Aisc360PageObservation(1, "one"),
                    Aisc360PageObservation(3, "three"),
                ),
                expected_page_count=3,
            )

    def test_empty_embedded_text_is_not_silently_reclassified_as_image_only(self) -> None:
        with self.assertRaisesRegex(ValueError, "embedded text must not be empty"):
            Aisc360PageObservation(1, "")

    def test_image_only_pages_receive_visible_diagnostics_without_source_expression(self) -> None:
        ast = build_aisc360_page_coverage_ast(
            (
                Aisc360PageObservation(1, "text"),
                Aisc360PageObservation(2, None),
            ),
            expected_page_count=2,
        )

        self.assertEqual(len(ast.diagnostics), 1)
        diagnostic = ast.diagnostics[0]
        self.assertEqual(diagnostic.code, "AISC360_IMAGE_ONLY_PAGE")
        self.assertEqual(diagnostic.span.text, "")
        self.assertNotIn("text", diagnostic.message.lower())
        self.assertIn("2", diagnostic.message)


if __name__ == "__main__":
    unittest.main()
