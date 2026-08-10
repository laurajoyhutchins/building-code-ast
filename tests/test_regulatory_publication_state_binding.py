from __future__ import annotations

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
)
from building_code_ast.model import SourceSpan


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_STATE_ID = "publication:" + "a" * 64


class RegulatoryPublicationStateBindingTests(unittest.TestCase):
    def test_document_source_artifact_carries_publication_state_without_changing_node_identity(self) -> None:
        legacy = DocumentSourceArtifact(
            artifact_id="sha256:" + "b" * 64,
            edition_id="ibc-2021",
        )
        bound = DocumentSourceArtifact(
            artifact_id=legacy.artifact_id,
            edition_id=legacy.edition_id,
            publication_state_id=PUBLICATION_STATE_ID,
        )

        legacy_id = document_node_id(
            artifact_id=legacy.artifact_id,
            edition_id=legacy.edition_id,
            node_type=DocumentNodeType.SECTION,
            locator="section:101.1",
        )
        bound_node = make_document_node(
            source_artifact=bound,
            node_type=DocumentNodeType.SECTION,
            locator="section:101.1",
            span=SourceSpan(start=0, end=4, text="Text"),
        )

        self.assertEqual(bound_node.node_id, legacy_id)
        self.assertEqual(bound.to_dict()["publication_state_id"], PUBLICATION_STATE_ID)

    def test_document_ast_round_trips_optional_publication_state_binding(self) -> None:
        source = "Text"
        artifact = DocumentSourceArtifact(
            artifact_id="sha256:" + "b" * 64,
            edition_id="ibc-2021",
            publication_state_id=PUBLICATION_STATE_ID,
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

        restored = document_ast_from_dict(payload)

        self.assertEqual(restored.source_artifact.publication_state_id, PUBLICATION_STATE_ID)
        self.assertEqual(restored.to_dict(), payload)

    def test_publication_state_binding_rejects_non_state_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "publication_state_id"):
            DocumentSourceArtifact(
                artifact_id="sha256:" + "b" * 64,
                edition_id="ibc-2021",
                publication_state_id="ibc-2021",
            )

    def test_document_schema_exposes_optional_publication_state_binding(self) -> None:
        schema = json.loads((ROOT / "schemas/document-ast.schema.json").read_text(encoding="utf-8"))
        source_artifact = schema["$defs"]["sourceArtifact"]

        self.assertNotIn("publication_state_id", source_artifact["required"])
        self.assertEqual(
            source_artifact["properties"]["publication_state_id"]["pattern"],
            r"^publication:[0-9a-f]{64}$",
        )


if __name__ == "__main__":
    unittest.main()
