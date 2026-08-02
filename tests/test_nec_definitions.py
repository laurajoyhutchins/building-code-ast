from __future__ import annotations

import unittest

from building_code_ast.document_model import (
    DocumentAst,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from building_code_ast.model import SourceSpan
from building_code_ast.nec.definitions import build_definition_index
from building_code_ast.nec.model import (
    CodeReferenceKind,
    DefinitionFragmentKind,
    DefinitionQualifierKind,
)


ARTIFACT = DocumentSourceArtifact("synthetic:nec", "synthetic-edition")


def _article_seed(article_number: str = "100", *, include_false_candidate: bool = False) -> dict:
    blocks = [
        (DocumentNodeType.HEADING, "Article 100", "ARTICLE 100 Definitions", {}),
        (DocumentNodeType.HEADING, "Part", "Part I. General", {}),
        (
            DocumentNodeType.DEFINITION_ENTRY,
            "Accessible Device (AD) (as applied to controls)",
            "Accessible Device (AD) (as applied to controls). "
            "A synthetic device referenced by Section 120.1. (CMP-99)",
            {},
        ),
        (
            DocumentNodeType.LIST_ITEM,
            "(1)",
            "(1) A first project-authored characteristic",
            {"marker": "(1)"},
        ),
        (
            DocumentNodeType.NOTE,
            "Informational Note",
            "Informational Note: See Article 120 and Table 120.2.",
            {},
        ),
        (
            DocumentNodeType.DEFINITION_ENTRY,
            "Rated Assembly (600 Volts or Less)",
            "Rated Assembly (600 Volts or Less). A synthetic scoped assembly.",
            {},
        ),
        (
            DocumentNodeType.PARAGRAPH,
            None,
            "The definition continues in this project-authored paragraph.",
            {},
        ),
    ]
    if include_false_candidate:
        blocks.append(
            (
                DocumentNodeType.DEFINITION_ENTRY,
                "This explanatory sentence is not a definition",
                "This explanatory sentence is not a definition. (CMP-7)",
                {},
            )
        )
    blocks.append((DocumentNodeType.HEADING, "Part", "Part II. Higher Voltage", {}))

    chunks: list[str] = []
    nodes = []
    offset = 0
    for index, (node_type, label, text, attributes) in enumerate(blocks, start=1):
        if chunks:
            chunks.append("\n\n")
            offset += 2
        start = offset
        chunks.append(text)
        offset += len(text)
        span = SourceSpan(start, offset, text)
        nodes.append(
            make_document_node(
                source_artifact=ARTIFACT,
                node_type=node_type,
                locator=f"article:{article_number}/block:{index:04d}",
                span=span,
                label=label,
                attributes=attributes,
            )
        )

    source = "".join(chunks)
    full_span = SourceSpan(0, len(source), source)
    article_node = make_document_node(
        source_artifact=ARTIFACT,
        node_type=DocumentNodeType.SECTION,
        locator=f"article:{article_number}",
        span=full_span,
        label=f"Article {article_number} - Definitions",
        attributes={"article_number": article_number},
        children=nodes,
    )
    root = make_document_node(
        source_artifact=ARTIFACT,
        node_type=DocumentNodeType.DOCUMENT,
        locator=f"document:article:{article_number}",
        span=full_span,
        label="Synthetic NEC Article",
        children=(article_node,),
    )
    ast = DocumentAst(source, ARTIFACT, root)
    return {
        "seed_version": "0.1.0",
        "article": {"number": article_number, "title": "Definitions"},
        "document_ast": ast.to_dict(),
    }


class DefinitionExtractionTests(unittest.TestCase):
    def test_builds_structured_entries_with_attachments_and_references(self) -> None:
        index = build_definition_index(_article_seed())

        self.assertEqual(len(index.entries), 2)
        first, second = index.entries

        self.assertEqual(first.canonical_term, "Accessible Device")
        self.assertEqual([item.text for item in first.alternate_terms], ["AD"])
        self.assertEqual(
            [(item.kind, item.text) for item in first.qualifiers],
            [(DefinitionQualifierKind.APPLICABILITY, "controls")],
        )
        self.assertEqual(
            [item.kind for item in first.body_fragments],
            [DefinitionFragmentKind.BODY, DefinitionFragmentKind.LIST_ITEM],
        )
        self.assertEqual(len(first.notes), 1)
        self.assertEqual([item.text for item in first.code_making_panels], ["(CMP-99)"])
        self.assertEqual(
            {(item.kind, item.target) for item in first.references},
            {
                (CodeReferenceKind.SECTION, "120.1"),
                (CodeReferenceKind.ARTICLE, "120"),
                (CodeReferenceKind.TABLE, "120.2"),
            },
        )

        self.assertEqual(second.canonical_term, "Rated Assembly")
        self.assertEqual(second.alternate_terms, ())
        self.assertEqual(
            [(item.kind, item.text) for item in second.qualifiers],
            [(DefinitionQualifierKind.SCOPE, "600 Volts or Less")],
        )
        self.assertEqual(
            [item.kind for item in second.body_fragments],
            [DefinitionFragmentKind.BODY, DefinitionFragmentKind.CONTINUATION],
        )

    def test_false_definition_candidate_becomes_prior_entry_continuation(self) -> None:
        index = build_definition_index(_article_seed(include_false_candidate=True))

        self.assertEqual(len(index.entries), 2)
        self.assertEqual(index.diagnostics, ())
        self.assertEqual(
            [fragment.kind for fragment in index.entries[1].body_fragments],
            [DefinitionFragmentKind.BODY, DefinitionFragmentKind.CONTINUATION, DefinitionFragmentKind.CONTINUATION],
        )

    def test_output_is_deterministic(self) -> None:
        first = build_definition_index(_article_seed()).to_dict()
        second = build_definition_index(_article_seed()).to_dict()

        self.assertEqual(first, second)

    def test_wrong_article_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Article 100"):
            build_definition_index(_article_seed("110"))

    def test_mismatched_definition_heading_fails_closed(self) -> None:
        seed = _article_seed()
        first_definition = seed["document_ast"]["root"]["children"][0]["children"][2]
        first_definition["label"] = "Different Heading"

        with self.assertRaisesRegex(ValueError, "does not begin with its label"):
            build_definition_index(seed)


if __name__ == "__main__":
    unittest.main()
