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

    def test_hosted_ci_bootstraps_lock_and_runs_same_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("python-version: 3.12.13", workflow)
        self.assertIn(
            "python -m pip install --no-deps --requirement requirements/verification.lock",
            workflow,
        )
        self.assertIn(
            "python -m pip install --no-deps --no-build-isolation -e .",
            workflow,
        )
        self.assertIn("python tools/verify_repository.py", workflow)
        self.assertNotIn("python tools/run_unit_tests.py", workflow)
        self.assertNotIn("python tools/validate_ibc_2018_corpus.py", workflow)
        self.assertNotIn("python tools/validate_ibc_2018_schemas.py", workflow)
        self.assertNotIn("python -m compileall", workflow)
        self.assertNotIn("python -m pip wheel", workflow)

    def test_receipt_path_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".building-code-ast/ci-evidence/", ignored)


if __name__ == "__main__":
    unittest.main()
