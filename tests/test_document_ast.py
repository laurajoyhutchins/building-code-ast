from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from building_code_ast import (
    DOCUMENT_AST_VERSION,
    DocumentNodeType,
    DocumentSourceArtifact,
    document_ast_from_dict,
    document_node_id,
    make_document_node,
    validate_document_ast,
)
from building_code_ast.model import SourceSpan


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_NAMES = (
    "document-nested-list",
    "document-definitions",
    "document-table",
)


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((ROOT / f"fixtures/expected/{name}.json").read_text(encoding="utf-8"))


def _walk(node: dict[str, object]):
    yield node
    for child in node["children"]:
        yield from _walk(child)


class DocumentAstTests(unittest.TestCase):
    def test_reviewed_document_fixtures_round_trip_with_exact_provenance(self) -> None:
        node_types: set[str] = set()

        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                expected = _load_fixture(name)
                source = (ROOT / f"fixtures/sources/{name}.txt").read_text(encoding="utf-8")
                ast = document_ast_from_dict(expected)

                self.assertEqual(ast.to_dict(), expected)
                self.assertEqual(ast.source_text, source)
                self.assertEqual(ast.ast_version, DOCUMENT_AST_VERSION)
                validate_document_ast(ast)

                for node in _walk(expected["root"]):
                    span = node["span"]
                    self.assertEqual(
                        source[span["start"] : span["end"]],
                        span["text"],
                    )
                    node_types.add(node["type"])

        self.assertTrue(
            {
                "document",
                "chapter",
                "section",
                "subsection",
                "paragraph",
                "list_item",
                "definition_entry",
                "table",
                "table_heading",
                "table_column",
                "table_row",
                "table_cell",
                "heading",
                "note",
                "footnote",
            }.issubset(node_types)
        )

    def test_node_factory_canonicalizes_attributes_and_identity(self) -> None:
        artifact = DocumentSourceArtifact(
            artifact_id="synthetic:factory",
            edition_id="v1",
        )
        node = make_document_node(
            source_artifact=artifact,
            node_type=DocumentNodeType.PARAGRAPH,
            locator="paragraph:1",
            span=SourceSpan(start=0, end=4, text="Text"),
            attributes={"z": "last", "a": "first"},
        )

        self.assertEqual(
            node.node_id,
            document_node_id(
                artifact_id=artifact.artifact_id,
                edition_id=artifact.edition_id,
                node_type=DocumentNodeType.PARAGRAPH,
                locator="paragraph:1",
            ),
        )
        self.assertEqual(node.to_dict()["attributes"], {"a": "first", "z": "last"})

    def test_node_identity_is_stable_and_edition_scoped(self) -> None:
        first = document_node_id(
            artifact_id="synthetic:sample",
            edition_id="2024",
            node_type=DocumentNodeType.SECTION,
            locator="section:1.1",
        )
        repeated = document_node_id(
            artifact_id="synthetic:sample",
            edition_id="2024",
            node_type=DocumentNodeType.SECTION,
            locator="section:1.1",
        )
        later_edition = document_node_id(
            artifact_id="synthetic:sample",
            edition_id="2027",
            node_type=DocumentNodeType.SECTION,
            locator="section:1.1",
        )

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, later_edition)
        self.assertRegex(first, r"^docnode:[0-9a-f]{64}$")

    def test_node_identity_is_publication_component_scoped(self) -> None:
        tms_402 = document_node_id(
            artifact_id="sha256:combined-tms-artifact",
            edition_id="2016",
            publication_component_id="tms-402-16",
            node_type=DocumentNodeType.SECTION,
            locator="section:1.1",
        )
        tms_602 = document_node_id(
            artifact_id="sha256:combined-tms-artifact",
            edition_id="2016",
            publication_component_id="tms-602-16",
            node_type=DocumentNodeType.SECTION,
            locator="section:1.1",
        )

        self.assertNotEqual(tms_402, tms_602)

    def test_source_artifact_round_trips_publication_component_identity(self) -> None:
        source = "Heading"
        artifact = DocumentSourceArtifact(
            artifact_id="sha256:combined-tms-artifact",
            edition_id="2016",
            publication_component_id="tms-402-16",
        )
        root = make_document_node(
            source_artifact=artifact,
            node_type=DocumentNodeType.DOCUMENT,
            locator="document",
            span=SourceSpan(start=0, end=len(source), text=source),
        )
        payload = {
            "ast_version": DOCUMENT_AST_VERSION,
            "type": "document_tree",
            "source_text": source,
            "source_artifact": artifact.to_dict(),
            "root": root.to_dict(),
            "diagnostics": [],
        }

        ast = document_ast_from_dict(payload)

        self.assertEqual(ast.source_artifact.publication_component_id, "tms-402-16")
        self.assertEqual(ast.to_dict(), payload)

    def test_tampered_span_text_is_rejected(self) -> None:
        payload = _load_fixture("document-definitions")
        payload["root"]["children"][0]["children"][1]["span"]["text"] = "tampered"

        with self.assertRaisesRegex(ValueError, "span text does not match"):
            document_ast_from_dict(payload)

    def test_child_span_must_remain_inside_parent(self) -> None:
        payload = _load_fixture("document-nested-list")
        subsection = payload["root"]["children"][0]["children"][1]["children"][1]
        subsection["span"] = copy.deepcopy(subsection["children"][0]["span"])

        with self.assertRaisesRegex(ValueError, "outside parent"):
            document_ast_from_dict(payload)

    def test_duplicate_locator_is_rejected(self) -> None:
        payload = _load_fixture("document-definitions")
        section_children = payload["root"]["children"][0]["children"]
        section_children.append(copy.deepcopy(section_children[1]))

        with self.assertRaisesRegex(ValueError, "duplicate document locator"):
            document_ast_from_dict(payload)

    def test_mismatched_node_id_is_rejected(self) -> None:
        payload = _load_fixture("document-table")
        payload["root"]["children"][0]["node_id"] = "docnode:" + "0" * 64

        with self.assertRaisesRegex(ValueError, "deterministic identity"):
            document_ast_from_dict(payload)

    def test_unsupported_structure_retains_source_and_diagnostic(self) -> None:
        source = "[ornamental divider]"
        payload = {
            "ast_version": DOCUMENT_AST_VERSION,
            "type": "document_tree",
            "source_text": source,
            "source_artifact": {
                "artifact_id": "synthetic:unsupported",
                "edition_id": "v1",
            },
            "root": {
                "node_id": document_node_id(
                    artifact_id="synthetic:unsupported",
                    edition_id="v1",
                    node_type=DocumentNodeType.DOCUMENT,
                    locator="document",
                ),
                "type": "document",
                "locator": "document",
                "span": {"start": 0, "end": len(source), "text": source},
                "label": None,
                "attributes": {},
                "children": [
                    {
                        "node_id": document_node_id(
                            artifact_id="synthetic:unsupported",
                            edition_id="v1",
                            node_type=DocumentNodeType.UNSUPPORTED,
                            locator="unsupported:1",
                        ),
                        "type": "unsupported",
                        "locator": "unsupported:1",
                        "span": {"start": 0, "end": len(source), "text": source},
                        "label": None,
                        "attributes": {"structure_hint": "ornamental_divider"},
                        "children": [],
                    }
                ],
            },
            "diagnostics": [
                {
                    "code": "unsupported-document-structure",
                    "severity": "warning",
                    "message": "The source structure is retained but not normalized.",
                    "span": {"start": 0, "end": len(source), "text": source},
                }
            ],
        }

        ast = document_ast_from_dict(payload)

        self.assertEqual(ast.root.children[0].node_type, DocumentNodeType.UNSUPPORTED)
        self.assertEqual(ast.diagnostics[0].code, "unsupported-document-structure")
        self.assertEqual(ast.to_dict(), payload)

    def test_semantic_fields_are_rejected_from_structural_nodes(self) -> None:
        payload = _load_fixture("document-definitions")
        payload["root"]["action"] = "interpretive field"

        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            document_ast_from_dict(payload)

    def test_schema_is_structural_not_semantic(self) -> None:
        schema = json.loads((ROOT / "schemas/document-ast.schema.json").read_text(encoding="utf-8"))
        node_types = set(schema["$defs"]["documentNode"]["properties"]["type"]["enum"])

        self.assertEqual(schema["properties"]["ast_version"]["const"], DOCUMENT_AST_VERSION)
        self.assertEqual(node_types, {member.value for member in DocumentNodeType})
        self.assertNotIn("modality", schema["properties"])
        self.assertNotIn("conditions", schema["properties"])
        self.assertNotIn("action", schema["properties"])


if __name__ == "__main__":
    unittest.main()
