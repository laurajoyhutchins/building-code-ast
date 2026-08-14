#!/usr/bin/env python3
"""Materialize one source-preserving PDF enrichment derivative from a v1 plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from building_code_ast.pdf_enrichment import enrich_pdf, plan_from_dict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()

    if args.output.exists() or args.output.is_symlink():
        parser.error("derivative output path must not already exist")
    if args.receipt.exists() or args.receipt.is_symlink():
        parser.error("receipt path must not already exist")
    if args.receipt.resolve(strict=False) in {
        args.source.resolve(strict=False),
        args.output.resolve(strict=False),
    }:
        parser.error("receipt path must be distinct from source and derivative")

    plan = plan_from_dict(json.loads(args.plan.read_text(encoding="utf-8")))
    try:
        receipt = enrich_pdf(args.source, args.output, plan)
        args.receipt.write_text(
            json.dumps(receipt.to_dict(), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        if args.output.exists():
            args.output.unlink()
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
