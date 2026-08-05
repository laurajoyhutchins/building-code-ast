from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]


def _load_cli_module():
    script_path = _ROOT / "scripts" / "build_nec_2020_expected_changelog.py"
    spec = importlib.util.spec_from_file_location("nec_change_history_fixture_cli", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load expected changelog CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NecChangeHistoryFixtureTests(unittest.TestCase):
    def test_synthetic_vertical_slice_matches_reviewed_projection(self) -> None:
        cli = _load_cli_module()
        fixture_dir = _ROOT / "fixtures" / "nec-change-history"
        input_bundle = json.loads(
            (fixture_dir / "input.synthetic.json").read_text(encoding="utf-8")
        )
        expected = json.loads(
            (fixture_dir / "expected.synthetic.json").read_text(encoding="utf-8")
        )

        actual = cli.build_dataset(input_bundle)

        self.assertEqual(actual, expected)
        self.assertEqual(actual["diagnostics"], [])
        self.assertEqual(
            {item["outcome"] for item in actual["reconciliations"]},
            {"confirmed"},
        )


if __name__ == "__main__":
    unittest.main()
