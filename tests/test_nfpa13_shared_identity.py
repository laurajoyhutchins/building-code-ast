from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from building_code_ast import document_model
from building_code_ast.nfpa13_bundle import canonical_json_bytes


MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_nfpa13_2019_ast.py"
SPEC = importlib.util.spec_from_file_location("extract_nfpa13_2019_ast_identity", MODULE_PATH)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


class Nfpa13SharedIdentityTests(unittest.TestCase):
    def test_node_id_routes_to_shared_document_model(self) -> None:
        with patch.object(
            document_model,
            "document_node_id",
            return_value="docnode:shared",
        ) as shared_node_id:
            self.assertEqual("docnode:shared", subject._node_id("10.1", "section"))

        shared_node_id.assert_called_once_with(
            artifact_id=subject.ARTIFACT_ID,
            edition_id=subject.EDITION_ID,
            node_type="section",
            locator="10.1",
        )

    def test_canonical_json_bytes_is_shared_bundle_primitive(self) -> None:
        self.assertIs(subject.canonical_json_bytes, canonical_json_bytes)


if __name__ == "__main__":
    unittest.main()
