from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "extract_ibc_2018_vector_regions.py"


class VectorCliTests(unittest.TestCase):
    def test_tool_exposes_exact_source_identity(self) -> None:
        spec = importlib.util.spec_from_file_location("ibc_vector_tool", TOOL)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.SOURCE_SHA256, "c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d")
        self.assertEqual(module.SOURCE_SIZE_BYTES, 32_608_171)
        self.assertEqual(module.SOURCE_PAGE_COUNT, 761)


if __name__ == "__main__":
    unittest.main()
