from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_unit_tests.py"


class TestUnittestDiscoveryContract(unittest.TestCase):
    def test_module_level_test_function_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            tests_root = Path(temporary_directory)
            (tests_root / "test_pytest_style.py").write_text(
                textwrap.dedent(
                    """
                    def test_silently_ignored():
                        pass
                    """
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--check-only",
                    str(tests_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("unsupported unittest discovery shape", result.stderr)
        self.assertIn("test_silently_ignored", result.stderr)


if __name__ == "__main__":
    unittest.main()
