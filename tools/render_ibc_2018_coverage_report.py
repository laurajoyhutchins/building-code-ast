#!/usr/bin/env python3
"""Render the IBC 2018 Markdown coverage report from source-safe JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from building_code_ast.ibc2018_reporting import render_coverage_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    return parser.parse_args()


def render_corpus(corpus_dir: Path) -> Path:
    coverage_path = corpus_dir / "ibc-2018-coverage-report.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    output = corpus_dir / "ibc-2018-coverage-report.md"
    output.write_text(render_coverage_markdown(coverage), encoding="utf-8")
    return output


def main() -> int:
    print(render_corpus(parse_args().corpus_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
