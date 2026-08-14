from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from building_code_ast import document_io


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "tools" / "extract_nfpa13_2019_ast.py"
LEGACY_PATH = ROOT / "tools" / "_extract_nfpa13_2019_ast_legacy.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


subject = _load(MODULE_PATH, "extract_nfpa13_2019_ast_shared_validation")
legacy = _load(LEGACY_PATH, "extract_nfpa13_2019_ast_legacy_validation_reference")


class Nfpa13SharedValidationTests(unittest.TestCase):
    def test_valid_bundle_requires_shared_document_ast_validation(self) -> None:
        bundle = subject.synthetic_bundle("Clause text")
        with patch.object(
            document_io,
            "document_ast_from_dict",
            wraps=document_io.document_ast_from_dict,
        ) as shared_validator:
            report = subject.validate_bundle(bundle)

        self.assertTrue(report["passed"], report)
        shared_validator.assert_called_once_with(bundle["document_ast"])

    def test_shared_document_ast_rejection_fails_closed(self) -> None:
        bundle = subject.synthetic_bundle("Clause text")
        with patch.object(
            document_io,
            "document_ast_from_dict",
            side_effect=ValueError("shared document rejection"),
        ):
            with self.assertRaisesRegex(ValueError, "shared document rejection"):
                subject.validate_bundle(bundle)

    def test_legacy_validation_report_shape_is_preserved(self) -> None:
        valid_expected = legacy.validate_bundle(legacy.synthetic_bundle("Clause text"))
        valid_actual = subject.validate_bundle(subject.synthetic_bundle("Clause text"))
        self.assertEqual(valid_expected, valid_actual)

        invalid_expected_bundle = legacy.synthetic_bundle("Clause text")
        invalid_expected_bundle["document_ast"]["root"]["children"].append(
            invalid_expected_bundle["document_ast"]["root"]["children"][0]
        )
        invalid_actual_bundle = subject.synthetic_bundle("Clause text")
        invalid_actual_bundle["document_ast"]["root"]["children"].append(
            invalid_actual_bundle["document_ast"]["root"]["children"][0]
        )
        self.assertEqual(
            legacy.validate_bundle(invalid_expected_bundle),
            subject.validate_bundle(invalid_actual_bundle),
        )


if __name__ == "__main__":
    unittest.main()
