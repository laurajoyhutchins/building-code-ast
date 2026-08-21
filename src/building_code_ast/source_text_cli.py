"""PDF-free command line access to persisted ``source-text/v1`` bundles."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .source_text import load_source_text_bundle, lookup_source_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="building-code-text")
    subcommands = parser.add_subparsers(dest="command", required=True)
    get_command = subcommands.add_parser("get", help="get exact compiled text by locator")
    get_command.add_argument("bundle", help="private source-text bundle directory")
    get_command.add_argument("locator", help="canonical Document AST locator")
    get_command.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def _emit(payload: dict[str, Any], *, compact: bool) -> None:
    print(json.dumps(payload, sort_keys=True, indent=None if compact else 2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "get":
        raise AssertionError(f"unexpected command: {args.command}")
    bundle = load_source_text_bundle(args.bundle)
    result = lookup_source_text(bundle, args.locator)
    _emit(
        {
            "command": "text.get",
            "bundle_sha256": bundle.bundle_sha256,
            "source_artifact": bundle.source_artifact.to_dict(),
            "result": result.to_dict(),
        },
        compact=args.compact,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
