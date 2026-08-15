from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from building_code_ast import document_model


MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_nfpa13_2019_ast.py"
SPEC = importlib.util.spec_from_file_location("extract_nfpa13_2019_ast_node_factory", MODULE_PATH)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


class Nfpa13SharedNodeFactoryTests(unittest.TestCase):
    def test_active_node_construction_routes_through_shared_factory(self) -> None:
        with patch.object(
            document_model,
            "make_document_node",
            wraps=document_model.make_document_node,
        ) as shared_factory:
            child = subject._node(
                "child",
                node_type="paragraph",
                locator="1.1#p1",
                start=0,
                end=5,
                attributes={"z": "last", "a": "first"},
            )
            root = subject._node(
                "child",
                node_type="document",
                locator="document",
                start=0,
                end=5,
                children=[child],
            )

        self.assertEqual(2, shared_factory.call_count)
        self.assertEqual({"a": "first", "z": "last"}, child["attributes"])
        self.assertEqual([child], root["children"])
        self.assertEqual("child", root["span"]["text"])


if __name__ == "__main__":
    unittest.main()
