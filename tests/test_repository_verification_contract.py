from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryVerificationContractTests(unittest.TestCase):
    def test_verification_contract_has_one_repository_owned_gate(self) -> None:
        contract = json.loads((ROOT / ".ci" / "contract.json").read_text(encoding="utf-8"))

        self.assertEqual(contract["version"], 1)
        self.assertEqual(
            contract["verify"]["commands"],
            [["python", "tools/verify_repository.py"]],
        )
        self.assertEqual(
            contract["evidence"]["path"],
            ".building-code-ast/ci-evidence/verification.json",
        )
        self.assertEqual(
            contract["requirements"],
            {"clean_tree": True, "locked_dependencies": True},
        )

    def test_verification_dependencies_and_build_backend_are_exactly_pinned(self) -> None:
        lock_lines = [
            line.strip()
            for line in (ROOT / "requirements" / "verification.lock").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(lock_lines)
        for line in lock_lines:
            self.assertRegex(line, r"^[A-Za-z0-9_.-]+==[^=<>!~]+$")

        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(pyproject["build-system"]["requires"], ["setuptools==84.0.0"])

    def test_receipt_path_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".building-code-ast/ci-evidence/", ignored)


if __name__ == "__main__":
    unittest.main()
