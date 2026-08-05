from __future__ import annotations

import unittest

import building_code_ast.nec as nec


class NecChangeHistoryExportTests(unittest.TestCase):
    def test_change_history_contracts_are_available_from_nec_package(self) -> None:
        expected_names = {
            "CHANGE_HISTORY_VERSION",
            "ChangeType",
            "DevelopmentDisposition",
            "DevelopmentRecord",
            "DevelopmentRecordType",
            "DevelopmentStage",
            "ExpectationConfidence",
            "ExpectedChange",
            "ExpectedDisposition",
            "ObservedChange",
            "Reconciliation",
            "ReconciliationOutcome",
            "ResolvedReference",
            "SourceLocator",
            "SourceManifestEntry",
            "project_expected_changes",
            "reconcile_changes",
            "resolve_nec_reference",
        }

        self.assertTrue(expected_names.issubset(set(nec.__all__)))
        for name in expected_names:
            self.assertIsNotNone(getattr(nec, name))


if __name__ == "__main__":
    unittest.main()
