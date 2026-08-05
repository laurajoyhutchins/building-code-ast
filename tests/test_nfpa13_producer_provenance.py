from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest


MODULE_PATH = Path(__file__).parents[1] / "tools" / "build_nfpa13_2019_bundle.py"
SPEC = importlib.util.spec_from_file_location("build_nfpa13_2019_bundle", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProducerProvenanceTests(unittest.TestCase):
    def test_rejects_supplied_commit_that_does_not_match_checkout_head(self) -> None:
        def run(*args, **kwargs):
            return subprocess.CompletedProcess(args, 0, stdout="a" * 40 + "\n", stderr="")

        with self.assertRaisesRegex(ValueError, "does not match checkout HEAD"):
            MODULE.verified_producer_commit(Path("/repo"), "b" * 40, run=run)

    def test_rejects_dirty_producer_files(self) -> None:
        calls = iter(
            [
                subprocess.CompletedProcess([], 0, stdout="a" * 40 + "\n", stderr=""),
                subprocess.CompletedProcess([], 1, stdout="", stderr="dirty"),
            ]
        )

        with self.assertRaisesRegex(ValueError, "producer files are dirty"):
            MODULE.verified_producer_commit(
                Path("/repo"), "a" * 40, run=lambda *args, **kwargs: next(calls)
            )

    def test_returns_verified_clean_checkout_head(self) -> None:
        calls = iter(
            [
                subprocess.CompletedProcess([], 0, stdout="a" * 40 + "\n", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            ]
        )
        self.assertEqual(
            MODULE.verified_producer_commit(
                Path("/repo"), "a" * 40, run=lambda *args, **kwargs: next(calls)
            ),
            "a" * 40,
        )


if __name__ == "__main__":
    unittest.main()
