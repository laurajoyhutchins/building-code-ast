from __future__ import annotations

import unittest

from building_code_ast import document_io, document_model
from building_code_ast.model import SourceSpan


class DocumentNodeIoTests(unittest.TestCase):
    def test_single_node_reader_round_trips_strict_nested_node_shape(self) -> None:
        artifact = document_model.DocumentSourceArtifact(
            artifact_id="synthetic:node-reader",
            edition_id="v1",
        )
        child = document_model.make_document_node(
            source_artifact=artifact,
            node_type="paragraph",
            locator="1#p1",
            span=SourceSpan(start=0, end=4, text="Text"),
            attributes={"owns_source": "true"},
        )
        root = document_model.make_document_node(
            source_artifact=artifact,
            node_type="document",
            locator="document",
            span=SourceSpan(start=0, end=4, text="Text"),
            children=(child,),
        )

        parsed = document_io.document_node_from_dict(root.to_dict())

        self.assertEqual(root, parsed)
        self.assertEqual(root.to_dict(), parsed.to_dict())

    def test_single_node_reader_rejects_unknown_fields(self) -> None:
        payload = {
            "node_id": "docnode:" + "0" * 64,
            "type": "paragraph",
            "locator": "p1",
            "span": {"start": 0, "end": 1, "text": "x"},
            "label": None,
            "attributes": {},
            "children": [],
            "semantic_guess": "requirement",
        }

        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            document_io.document_node_from_dict(payload)


if __name__ == "__main__":
    unittest.main()
