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
    flatten_nec_hierarchy,
)
from building_code_ast.model import SourceSpan


_ARTIFACT = DocumentSourceArtifact(
    artifact_id="test:nec-corpus-patterns",
    edition_id="test-edition",
)


def _nodes(
    specs: list[tuple[DocumentNodeType, str | None, str]],
) -> tuple[str, tuple[DocumentNode, ...]]:
    source = "\n\n".join(text for _, _, text in specs)
    result: list[DocumentNode] = []
    cursor = 0
    for index, (node_type, label, text) in enumerate(specs, start=1):
        start = source.index(text, cursor)
        end = start + len(text)
        cursor = end
        result.append(
            make_document_node(
                source_artifact=_ARTIFACT,
                node_type=node_type,
                locator=f"article:110/block:{index:04d}",
                span=SourceSpan(start, end, text),
                label=label,
                attributes={"layout_role": node_type.value, "pdf_page": "1"},
            )
        )
    return source, tuple(result)


def _locators(nodes: tuple[DocumentNode, ...]) -> list[str]:
    return [record.locator for record in flatten_nec_hierarchy(nodes)]


class NecCorpusPatternTests(unittest.TestCase):
    def test_ordinary_numbered_enumerations_are_not_promoted_to_clauses(self) -> None:
        source, nodes = _nodes(
            [
                (
                    DocumentNodeType.SECTION,
                    "110.3 Examination.",
                    "110.3 Examination. Synthetic examination text.",
                ),
                (
                    DocumentNodeType.SUBSECTION,
                    "(A)",
                    "(A) Examination. The following shall be evaluated:",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Suitability for installation and use in conformity with the provisions",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(2)",
                    "(2) Mechanical strength and durability, including enclosure adequacy",
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
        self.assertEqual(_locators(result.nodes), ["110.3", "110.3(A)"])
        subsection = result.nodes[0].children[0]
        self.assertEqual(
            [child.node_type for child in subsection.children],
            [DocumentNodeType.LIST_ITEM, DocumentNodeType.LIST_ITEM],
        )

    def test_inline_titled_markers_are_split_and_nested(self) -> None:
        source, nodes = _nodes(
            [
                (
                    DocumentNodeType.SECTION,
                    "110.26 Spaces.",
                    "110.26 Spaces. Synthetic section text.",
                ),
                (
                    DocumentNodeType.SUBSECTION,
                    "(A)",
                    "(A) Working Space. Synthetic subsection text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Depth of Working Space. Synthetic depth text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(a)",
                    "(a) Dead-Front Assemblies. Synthetic text. "
                    "(b) Low Voltage. Synthetic text. "
                    "(c) Existing Buildings. Synthetic text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(2)",
                    "(2) Width of Working Space. Synthetic width text.",
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
        self.assertEqual(
            _locators(result.nodes),
            [
                "110.26",
                "110.26(A)",
                "110.26(A)(1)",
                "110.26(A)(1)(a)",
                "110.26(A)(1)(b)",
                "110.26(A)(1)(c)",
                "110.26(A)(2)",
            ],
        )

    def test_numbered_enumerations_can_precede_an_inline_titled_clause(self) -> None:
        source, nodes = _nodes(
            [
                (
                    DocumentNodeType.SECTION,
                    "110.26 Spaces.",
                    "110.26 Spaces. Synthetic section text.",
                ),
                (
                    DocumentNodeType.SUBSECTION,
                    "(E)",
                    "(E) Dedicated Equipment Space. Synthetic subsection text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(2)",
                    "(2) Outdoor. Synthetic outdoor text. "
                    "(a) Installation Requirements. The following shall apply:",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Installed in identified enclosures "
                    "(2) Protected from accidental contact "
                    "(3) Protected from accidental spillage "
                    "(b) Work Space. Synthetic work-space text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(c)",
                    "(c) Dedicated Equipment Space. Synthetic dedicated-space text.",
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
        self.assertEqual(
            _locators(result.nodes),
            [
                "110.26",
                "110.26(E)",
                "110.26(E)(2)",
                "110.26(E)(2)(a)",
                "110.26(E)(2)(b)",
                "110.26(E)(2)(c)",
            ],
        )

    def test_parenthetical_domain_words_do_not_become_clause_markers(self) -> None:
        source, nodes = _nodes(
            [
                (
                    DocumentNodeType.DEFINITION_ENTRY,
                    "Associated Apparatus [as applied to Hazardous (Classified) Locations]",
                    "Associated Apparatus [as applied to Hazardous (Classified) Locations]. "
                    "Synthetic definition text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Electrical apparatus that has an alternative type of protection",
                ),
            ]
        )

        result = build_nec_hierarchy(
            article_number="100",
            source_text=source,
            source_artifact=_ARTIFACT,
            nodes=nodes,
        )

        self.assertEqual(result.diagnostics, ())
        self.assertEqual(flatten_nec_hierarchy(result.nodes), ())
        self.assertEqual(len(result.nodes), 2)

    def test_temperature_units_do_not_make_an_enumeration_look_titled(self) -> None:
        source, nodes = _nodes(
            [
                (
                    DocumentNodeType.SECTION,
                    "110.14 Connections.",
                    "110.14 Connections. Synthetic section text.",
                ),
                (
                    DocumentNodeType.SUBSECTION,
                    "(C)",
                    "(C) Temperature Limitations. Synthetic subsection text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Equipment Provisions. Synthetic equipment text.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(1)",
                    "(1) Conductors rated 60°C (140°F). "
                    "(2) Conductors with higher temperature ratings, provided the ampacity is limited.",
                ),
                (
                    DocumentNodeType.LIST_ITEM,
                    "(2)",
                    "(2) Separate Connector Provisions. Synthetic connector text.",
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
        self.assertEqual(
            _locators(result.nodes),
            ["110.14", "110.14(C)", "110.14(C)(1)", "110.14(C)(2)"],
        )


if __name__ == "__main__":
    unittest.main()
