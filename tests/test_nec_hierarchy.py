from __future__ import annotations

import unittest

from building_code_ast.document_model import (
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from building_code_ast.ingest.nec_hierarchy import (
    build_nec_hierarchy,
    canonical_nec_locator,
    compare_hierarchy,
    flatten_nec_hierarchy,
    load_clause_oracle,
    nec_locator_depth,
    nec_parent_locator,
)
from building_code_ast.model import SourceSpan


_ARTIFACT = DocumentSourceArtifact(
    artifact_id="test:electrical-code",
    edition_id="test-edition",
)


def _flat_nodes(specs: list[tuple[DocumentNodeType, str | None, str]]) -> tuple[str, tuple[DocumentNode, ...]]:
    source = "\n\n".join(text for _, _, text in specs)
    nodes: list[DocumentNode] = []
    cursor = 0
    for index, (node_type, label, text) in enumerate(specs, start=1):
        start = source.index(text, cursor)
        end = start + len(text)
        cursor = end
        nodes.append(
            make_document_node(
                source_artifact=_ARTIFACT,
                node_type=node_type,
                locator=f"article:110/block:{index:04d}",
                span=SourceSpan(start, end, text),
                label=label,
                attributes={"pdf_page": "1", "layout_role": node_type.value},
            )
        )
    return source, tuple(nodes)


def _attributes(node: DocumentNode) -> dict[str, str]:
    return dict(node.attributes)


class LocatorTests(unittest.TestCase):
    def test_canonical_locator_and_parent_support_repeated_deep_markers(self) -> None:
        locator = canonical_nec_locator(" 110.26 (A) (1) (a) (1) ")

        self.assertEqual(locator, "110.26(A)(1)(a)(1)")
        self.assertEqual(nec_parent_locator(locator), "110.26(A)(1)(a)")
        self.assertEqual(nec_locator_depth(locator), 5)

    def test_article_and_section_parents_are_explicit(self) -> None:
        self.assertIsNone(nec_parent_locator("110"))
        self.assertEqual(nec_parent_locator("110.26"), "110")
        self.assertEqual(nec_locator_depth("110"), 0)
        self.assertEqual(nec_locator_depth("110.26"), 1)

    def test_invalid_locator_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid NEC locator"):
            canonical_nec_locator("110.26(A) trailing")


class HierarchyBuilderTests(unittest.TestCase):
    def test_builds_part_section_and_deep_clause_tree(self) -> None:
        source, nodes = _flat_nodes(
            [
                (DocumentNodeType.HEADING, "Part I. General", "Part I. General"),
                (
                    DocumentNodeType.SECTION,
                    "110.1 Scope.",
                    "110.1 Scope. Synthetic scope sentence.",
                ),
                (
                    DocumentNodeType.SUBSECTION,
                    "(A)",
                    "(A) First Topic. Synthetic subsection text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) First Item. Synthetic item text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(a)",
                    "(a) Detail. Synthetic nested text.",
                ),
                (
                    DocumentNodeType.NOTE,
                    "Informational Note",
                    "Informational Note: Synthetic explanation.",
                ),
            ]
        )

        result = build_nec_hierarchy(
            article_number="110",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )

        self.assertEqual(result.diagnostics, ())
        part = result.nodes[0]
        section = part.children[0]
        subsection = section.children[0]
        item = subsection.children[0]
        detail = item.children[0]
        note = detail.children[0]

        self.assertEqual(_attributes(part)["nec_part"], "I")
        self.assertEqual(section.locator, "nec:110.1")
        self.assertEqual(subsection.locator, "nec:110.1(A)")
        self.assertEqual(item.locator, "nec:110.1(A)(1)")
        self.assertEqual(detail.locator, "nec:110.1(A)(1)(a)")
        self.assertEqual(note.node_type, DocumentNodeType.NOTE)
        self.assertEqual(section.span.end, note.span.end)
        self.assertEqual(part.span.end, note.span.end)

    def test_uppercase_marker_resets_deeper_stack_to_section(self) -> None:
        source, nodes = _flat_nodes(
            [
                (DocumentNodeType.SECTION, "110.1 Scope.", "110.1 Scope. Synthetic."),
                (DocumentNodeType.SUBSECTION, "(A)", "(A) Alpha. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(1)", "(1) One. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(a)", "(a) Detail. Synthetic."),
                (DocumentNodeType.SUBSECTION, "(B)", "(B) Beta. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(1)", "(1) One. Synthetic."),
            ]
        )

        result = build_nec_hierarchy(
            article_number="110",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )

        section = result.nodes[0]
        self.assertEqual(
            [child.locator for child in section.children],
            ["nec:110.1(A)", "nec:110.1(B)"],
        )
        self.assertEqual(section.children[1].children[0].locator, "nec:110.1(B)(1)")

    def test_repeated_numeric_marker_can_nest_below_lowercase_marker(self) -> None:
        source, nodes = _flat_nodes(
            [
                (DocumentNodeType.SECTION, "110.1 Scope.", "110.1 Scope. Synthetic."),
                (DocumentNodeType.SUBSECTION, "(A)", "(A) Alpha. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(1)", "(1) One. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(a)", "(a) Detail. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(1)", "(1) Deep Item. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(2)", "(2) Deep Sibling. Synthetic."),
            ]
        )

        result = build_nec_hierarchy(
            article_number="110",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )

        lowercase = result.nodes[0].children[0].children[0].children[0]
        self.assertEqual(
            [child.locator for child in lowercase.children],
            ["nec:110.1(A)(1)(a)(1)", "nec:110.1(A)(1)(a)(2)"],
        )

    def test_marker_without_open_section_is_preserved_with_diagnostic(self) -> None:
        source, nodes = _flat_nodes(
            [(DocumentNodeType.SUBSECTION, "(A)", "(A) Orphan. Synthetic text.")]
        )

        result = build_nec_hierarchy(
            article_number="110",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )

        self.assertEqual(result.nodes[0].locator, "article:110/block:0001")
        self.assertEqual([item.code for item in result.diagnostics], ["orphan-nec-marker"])


class HierarchyOracleTests(unittest.TestCase):
    def test_exact_tree_matches_clause_csv(self) -> None:
        source, nodes = _flat_nodes(
            [
                (DocumentNodeType.SECTION, "110.1 Scope.", "110.1 Scope. Synthetic."),
                (DocumentNodeType.SUBSECTION, "(A)", "(A) Alpha. Synthetic."),
                (DocumentNodeType.LIST_ITEM, "(1)", "(1) One. Synthetic."),
            ]
        )
        result = build_nec_hierarchy(
            article_number="110",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )
        expected = load_clause_oracle(
            "clause_id,clause_title,parent\n"
            "110.1,Scope,110\n"
            "110.1(A),Alpha,110.1\n"
            "110.1(A)(1),One,110.1(A)\n"
        )

        report = compare_hierarchy(expected, flatten_nec_hierarchy(result.nodes))

        self.assertTrue(report.conforms)
        self.assertEqual(report.matches, 3)
        self.assertEqual(report.mismatches, ())

    def test_reports_mismatch_classes_independently(self) -> None:
        expected = load_clause_oracle(
            "clause_id,clause_title,parent\n"
            "110.1,Expected Scope,110\n"
            "110.1(A),Alpha,110.1\n"
            "110.1(A)(1),One,110.1(A)\n"
            "110.1(B),Missing,110.1\n"
        )
        actual = load_clause_oracle(
            "clause_id,clause_title,parent\n"
            "110.1,Actual Scope,110\n"
            "110.1(A),Alpha,110\n"
            "110.1(A)(1),One,110.1(A)\n"
            "110.1(C),Unexpected,110.1\n"
        )

        report = compare_hierarchy(expected, actual)
        codes = {item.code for item in report.mismatches}

        self.assertIn("title-mismatch", codes)
        self.assertIn("parent-mismatch", codes)
        self.assertIn("depth-mismatch", codes)
        self.assertIn("missing-locator", codes)
        self.assertIn("unexpected-locator", codes)
        self.assertIn("order-mismatch", codes)
        self.assertFalse(report.conforms)

    def test_duplicate_clause_ids_are_reported_not_collapsed(self) -> None:
        records = load_clause_oracle(
            "clause_id,clause_title,parent\n"
            "110.1,Scope,110\n"
            "110.1,Scope Again,110\n"
        )

        report = compare_hierarchy(records, records)

        self.assertIn("duplicate-expected-locator", {item.code for item in report.mismatches})
        self.assertIn("duplicate-actual-locator", {item.code for item in report.mismatches})


if __name__ == "__main__":
    unittest.main()
