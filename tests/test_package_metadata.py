from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_optional_dependencies_do_not_capture_project_classifiers(self) -> None:
        payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertIn("classifiers", payload["project"])
        self.assertEqual(
            payload["project"]["optional-dependencies"],
            {
                "ibc-pdf": ["PyMuPDF>=1.24,<2"],
                "nec-pdf": ["PyMuPDF>=1.24,<2"],
            },
        )


if __name__ == "__main__":
    unittest.main()
