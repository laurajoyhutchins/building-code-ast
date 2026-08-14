#!/usr/bin/env python3
"""Run the complete source-safe repository verification contract."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "requirements" / "verification.lock"
EXPECTED_PYTHON = (3, 12, 13)


def locked_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in LOCK_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, expected = line.partition("==")
        if not separator or not name or not expected:
            raise ValueError(f"verification lock entry is not exact: {raw_line!r}")
        result[name] = expected
    if not result:
        raise ValueError("verification lock is empty")
    return result


def verify_environment() -> None:
    observed_python = sys.version_info[:3]
    if observed_python != EXPECTED_PYTHON:
        expected = ".".join(str(part) for part in EXPECTED_PYTHON)
        observed = ".".join(str(part) for part in observed_python)
        raise RuntimeError(f"verification requires CPython {expected}; observed {observed}")

    mismatches: list[str] = []
    for distribution, expected in locked_versions().items():
        try:
            observed = version(distribution)
        except PackageNotFoundError:
            mismatches.append(f"{distribution}=={expected} is not installed")
            continue
        if observed != expected:
            mismatches.append(f"{distribution}: expected {expected}, observed {observed}")
    if mismatches:
        raise RuntimeError("verification dependency drift:\n" + "\n".join(mismatches))


def tracked_changes() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verification_commands(temp_root: Path) -> tuple[tuple[str, ...], ...]:
    return (
        (sys.executable, "tools/run_unit_tests.py"),
        (sys.executable, "tools/validate_ibc_2018_corpus.py", "corpora/ibc-2018"),
        (sys.executable, "tools/validate_ibc_2018_schemas.py", "corpora/ibc-2018", "schemas"),
        (sys.executable, "-m", "compileall", "-q", "src", "scripts", "tools", "tests"),
        (
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "-w",
            str(temp_root / "wheelhouse"),
        ),
    )


def main() -> int:
    verify_environment()
    before = tracked_changes()
    if before:
        raise RuntimeError(f"verification requires a clean tracked worktree:\n{before}")

    with tempfile.TemporaryDirectory(prefix="building-code-ast-verify-") as raw_temp:
        temp_root = Path(raw_temp)
        env = os.environ.copy()
        env["PYTHONPYCACHEPREFIX"] = str(temp_root / "pycache")
        for command in verification_commands(temp_root):
            subprocess.run(command, cwd=ROOT, env=env, check=True)

    after = tracked_changes()
    if after:
        raise RuntimeError(f"verification modified tracked source:\n{after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
