from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast import (
    DOCUMENT_AST_VERSION,
    DocumentNodeType,
    DocumentSourceArtifact,
    document_ast_from_dict,
    make_document_node,
    validate_document_ast,
)
from building_code_ast.json_schema_validation import validate_instances
from building_code_ast.model import SourceSpan


ROOT = Path(__file__).resolve().parents[1]


class DocumentAppendixTests(unittest.TestCase):
    def test_appendix_is_a_first_class_structural_node(self) -> None:
        source = "Appendix A\nBody"
        artifact = DocumentSourceArtifact(
            artifact_id="synthetic:appendix",
            edition_id="v1",
        )
        paragraph = make_document_node(
            source_artifact=artifact,
            node_type=DocumentNodeType.PARAGRAPH,
            locator="appendix:A:paragraph:1",
            span=SourceSpan(start=11, end=15, text="Body"),
        )
        appendix = make_document_node(
            source_artifact=artifact,
            node_type="appendix",
            locator="appendix:A",
            span=SourceSpan(start=0, end=len(source), text=source),
            label="Appendix A",
            attributes={"source_role": "non_mandatory"},
            children=(paragraph,),
        )
        root = make_document_node(
            source_artifact=artifact,
            node_type=DocumentNodeType.DOCUMENT,
            locator="document",
            span=SourceSpan(start=0, end=len(source), text=source),
            children=(appendix,),
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
        validate_document_ast(restored)

        self.assertEqual(restored.root.children[0].node_type, DocumentNodeType.APPENDIX)
        self.assertEqual(dict(restored.root.children[0].attributes)["source_role"], "non_mandatory")
        self.assertEqual(restored.to_dict(), payload)

        schema = json.loads(
            (ROOT / "schemas/document-ast.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_instances([payload], schema), [])


if __name__ == "__main__":
    unittest.main()
