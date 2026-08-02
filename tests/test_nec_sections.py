from __future__ import annotations

import unittest

from building_code_ast.document_model import (
    DocumentAst,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from building_code_ast.model import SourceSpan
from building_code_ast.nec.model import (
    DefinitionEntry,
    DefinitionFragment,
    DefinitionFragmentKind,
    DefinitionIndex,
    ReviewedModality,
    definition_entry_id,
)
from building_code_ast.nec.sections import build_section_review, derive_language_profile


ARTIFACT = DocumentSourceArtifact("synthetic:nec", "synthetic-edition")


def _seed(article_number: str, blocks: list[tuple]) -> dict:
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
        nodes.append(
            make_document_node(
                source_artifact=ARTIFACT,
                node_type=node_type,
                locator=f"article:{article_number}/block:{index:04d}",
                span=SourceSpan(start, offset, text),
                label=label,
                attributes=attributes,
            )
        )
    source = "".join(chunks)
    full = SourceSpan(0, len(source), source)
    article = make_document_node(
        source_artifact=ARTIFACT,
        node_type=DocumentNodeType.SECTION,
        locator=f"article:{article_number}",
        span=full,
        label=f"Article {article_number} - Synthetic",
        attributes={"article_number": article_number},
        children=nodes,
    )
    root = make_document_node(
        source_artifact=ARTIFACT,
        node_type=DocumentNodeType.DOCUMENT,
        locator=f"document:article:{article_number}",
        span=full,
        label="Synthetic Article",
        children=(article,),
    )
    return {
        "seed_version": "0.1.0",
        "article": {"number": article_number, "title": "Synthetic"},
        "document_ast": DocumentAst(source, ARTIFACT, root).to_dict(),
    }


def _definitions() -> DefinitionIndex:
    source = "Approved. Synthetic approval body.\n\nListed. Synthetic listing body."
    approved_span = SourceSpan(0, 34, source[:34])
    listed_start = source.index("Listed")
    approved = DefinitionEntry(
        definition_id=definition_entry_id(ARTIFACT, "article:100/block:0001"),
        source_locator="article:100/block:0001",
        display_term="Approved",
        canonical_term="Approved",
        term_span=SourceSpan(0, 8, "Approved"),
        alternate_terms=(),
        qualifiers=(),
        body_fragments=(
            DefinitionFragment(
                DefinitionFragmentKind.BODY,
                "article:100/block:0001",
                "definition_entry",
                SourceSpan(10, 34, source[10:34]),
            ),
        ),
        notes=(),
        code_making_panels=(),
        references=(),
        source_span=approved_span,
    )
    listed = DefinitionEntry(
        definition_id=definition_entry_id(ARTIFACT, "article:100/block:0002"),
        source_locator="article:100/block:0002",
        display_term="Listed",
        canonical_term="Listed",
        term_span=SourceSpan(listed_start, listed_start + 6, "Listed"),
        alternate_terms=(),
        qualifiers=(),
        body_fragments=(
            DefinitionFragment(
                DefinitionFragmentKind.BODY,
                "article:100/block:0002",
                "definition_entry",
                SourceSpan(listed_start + 8, len(source), source[listed_start + 8 :]),
            ),
        ),
        notes=(),
        code_making_panels=(),
        references=(),
        source_span=SourceSpan(listed_start, len(source), source[listed_start:]),
    )
    return DefinitionIndex(source, ARTIFACT, "article:100", (approved, listed))


def _article_90() -> dict:
    return _seed(
        "90",
        [
            (
                DocumentNodeType.SECTION,
                "90.5 Mandatory, Permissive, and Explanatory Rules.",
                "90.5 Mandatory, Permissive, and Explanatory Rules.",
                {},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(A)",
                "(A) Mandatory Rules. Synthetic mandatory rules use the terms shall or shall not.",
                {"marker": "(A)"},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(B)",
                "(B) Permissive Rules. Synthetic permissive rules use shall be permitted or shall not be required.",
                {"marker": "(B)"},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(C)",
                "(C) Explanatory Material. Explanatory material is placed in informational notes.",
                {"marker": "(C)"},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(D)",
                "(D) Annexes. Nonmandatory information is separated from enforceable requirements.",
                {"marker": "(D)"},
            ),
            (DocumentNodeType.SECTION, "90.6 Next Section.", "90.6 Next Section. Stop here.", {}),
        ],
    )


def _article_110() -> dict:
    return _seed(
        "110",
        [
            (
                DocumentNodeType.SECTION,
                "110.2 Approval.",
                "110.2 Approval. Synthetic equipment shall be acceptable only if approved.",
                {},
            ),
            (
                DocumentNodeType.NOTE,
                "Informational Note",
                "Informational Note: See 90.7 for a synthetic cross-reference.",
                {},
            ),
            (
                DocumentNodeType.SECTION,
                "110.3 Examination and Installation.",
                "110.3 Examination and Installation.",
                {},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(A)",
                "(A) Examination. In judging synthetic equipment, the following shall be evaluated:",
                {"marker": "(A)"},
            ),
            (
                DocumentNodeType.LIST_ITEM,
                "(1)",
                "(1) Suitability for the synthetic installation",
                {"marker": "(1)"},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(B)",
                "(B) Installation. Listed equipment shall be installed according to supplied instructions.",
                {"marker": "(B)"},
            ),
            (
                DocumentNodeType.SECTION,
                "110.14 Synthetic Connections.",
                "110.14 Synthetic Connections. Synthetic terminals shall be connected by an identified method.",
                {},
            ),
            (
                DocumentNodeType.SECTION,
                "110.16 Warning Labels.",
                "110.16 Warning Labels.",
                {},
            ),
            (
                DocumentNodeType.SUBSECTION,
                "(A)",
                "(A) General. When synthetic service equipment is installed, a warning label shall be marked.",
                {"marker": "(A)"},
            ),
            (
                DocumentNodeType.NOTE,
                "Exception",
                "Exception: A label shall not be required where an equivalent synthetic warning is present.",
                {"kind": "exception"},
            ),
            (
                DocumentNodeType.NOTE,
                "Informational Note",
                "Informational Note: This note may describe a project-authored practice.",
                {},
            ),
            (DocumentNodeType.SECTION, "110.18 Next Section.", "110.18 Next Section. Stop here.", {}),
            (
                DocumentNodeType.SECTION,
                "110.26 Synthetic Working Space.",
                "110.26 Synthetic Working Space. Working space shall be provided about synthetic equipment.",
                {},
            ),
            (DocumentNodeType.SECTION, "110.27 Next Section.", "110.27 Next Section. Stop here.", {}),
        ],
    )


class SectionReviewTests(unittest.TestCase):
    def test_section_boundary_notes_and_definition_links(self) -> None:
        review = build_section_review(_article_110(), "110.2", definitions=_definitions())

        self.assertEqual(review.section_locator, "110.2")
        self.assertNotIn("110.3", review.source_text)
        self.assertEqual(len(review.clauses), 1)
        self.assertEqual(review.clauses[0].modality, ReviewedModality.REQUIREMENT)
        self.assertIn("authority_approval", review.clauses[0].semantic_tags)
        self.assertEqual(
            review.clauses[0].definition_ids,
            (_definitions().entries[0].definition_id,),
        )
        self.assertEqual(len(review.notes), 1)
        self.assertEqual(review.exceptions, ())
        self.assertIn("90.7", {reference.target for reference in review.references})

    def test_modal_precedence_condition_and_exception_separation(self) -> None:
        review = build_section_review(_article_110(), "110.16", definitions=_definitions())

        self.assertEqual(len(review.clauses), 1)
        clause = review.clauses[0]
        self.assertEqual(clause.modality, ReviewedModality.REQUIREMENT)
        self.assertEqual(clause.condition_span.text, "When synthetic service equipment is installed")
        self.assertIn("warning", clause.semantic_tags)
        self.assertEqual(len(review.exceptions), 1)
        self.assertEqual(review.exceptions[0].modality, ReviewedModality.NONREQUIREMENT)
        self.assertEqual(len(review.notes), 1)
        self.assertNotIn("may", [clause.modality.value for clause in review.clauses])

    def test_examination_and_listing_tags_are_preserved(self) -> None:
        review = build_section_review(_article_110(), "110.3", definitions=_definitions())

        self.assertEqual([clause.modality for clause in review.clauses], [
            ReviewedModality.REQUIREMENT,
            ReviewedModality.REQUIREMENT,
        ])
        tags = set().union(*(set(clause.semantic_tags) for clause in review.clauses))
        self.assertIn("examination", tags)
        self.assertIn("installation", tags)
        self.assertIn("listing", tags)
        self.assertIn(_definitions().entries[1].definition_id, review.clauses[1].definition_ids)

    def test_section_90_5_derives_complete_language_profile(self) -> None:
        review = build_section_review(_article_90(), "90.5")
        profile = derive_language_profile(review)

        self.assertEqual(profile.source_locator, "90.5")
        self.assertEqual(profile.mandatory_phrases, ("shall", "shall not"))
        self.assertEqual(
            profile.permissive_phrases,
            ("shall be permitted", "shall not be required"),
        )
        self.assertEqual(
            {item.category.value for item in profile.evidence},
            {"mandatory", "permissive", "explanatory", "nonmandatory"},
        )

    def test_missing_section_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "110.99"):
            build_section_review(_article_110(), "110.99")


if __name__ == "__main__":
    unittest.main()
