#!/usr/bin/env python3
"""Fail-closed unittest discovery and execution for this repository."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import subprocess
import sys


def unsupported_test_shapes(tests_root: Path) -> tuple[str, ...]:
    """Return test-shaped constructs that unittest discovery would ignore."""

    problems: list[str] = []
    for path in sorted(tests_root.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            problems.append(f"{path}: cannot inspect test module: {exc}")
            continue

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                relative_path = path.relative_to(tests_root)
                problems.append(
                    f"{relative_path}:{node.lineno}: module-level {node.name} is an "
                    "unsupported unittest discovery shape; use a unittest.TestCase test_* method"
                )

    return tuple(problems)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject unittest-incompatible test shapes, then run unittest discovery."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate discovery shape without executing the suite",
    )
    parser.add_argument(
        "tests_root",
        nargs="?",
        type=Path,
        default=Path("tests"),
        help="test directory (default: tests)",
    )
    args = parser.parse_args(argv)

    tests_root = args.tests_root.resolve()
    if not tests_root.is_dir():
        print(f"test directory does not exist: {tests_root}", file=sys.stderr)
        return 1

    problems = unsupported_test_shapes(tests_root)
    if problems:
        for problem in problems:
            print(f"unsupported unittest discovery shape: {problem}", file=sys.stderr)
        return 1

    if args.check_only:
        return 0

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(args.tests_root),
            "-v",
        ],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
