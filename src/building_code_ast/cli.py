"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import parse_provision


def _read_source(args: argparse.Namespace) -> str:
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("provide provision text, --file, or standard input")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="building-code-ast")
    subcommands = parser.add_subparsers(dest="command", required=True)

    parse_command = subcommands.add_parser("parse", help="parse one provision")
    parse_command.add_argument("text", nargs="?", help="provision text")
    parse_command.add_argument("--file", help="read provision text from a UTF-8 file")
    parse_command.add_argument(
        "--source-artifact-id",
        default="inline",
        help="durable identifier for the source document or edition",
    )
    parse_command.add_argument(
        "--provision-locator",
        default="inline",
        help="locator for this provision within the source artifact",
    )
    parse_command.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "parse":
        raise AssertionError(f"unexpected command: {args.command}")

    ast = parse_provision(
        _read_source(args),
        source_artifact_id=args.source_artifact_id,
        provision_locator=args.provision_locator,
    )
    indent = None if args.compact else 2
    print(json.dumps(ast.to_dict(), indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
