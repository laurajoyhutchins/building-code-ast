"""Cheap persisted Source Text IR lookup command.

This module intentionally depends only on the durable source-text contract and
Python's standard library. It does not import PDF extraction, hierarchy
reconstruction, or semantic parsing modules.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from .source_text import SourceTextBundle


def _emit_json(payload: dict[str, Any], *, compact: bool) -> None:
    print(json.dumps(payload, indent=None if compact else 2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="building-code-text")
    subcommands = parser.add_subparsers(dest="command", required=True)

    get_command = subcommands.add_parser(
        "get",
        help="read exact canonical text and provenance for one persisted locator",
    )
    get_command.add_argument("bundle", help="private source-text/v1 JSON bundle")
    get_command.add_argument("locator", help="canonical document locator")
    get_command.add_argument("--compact", action="store_true", help="emit compact JSON")

    status_command = subcommands.add_parser(
        "status",
        help="validate and summarize one persisted source-text/v1 bundle",
    )
    status_command.add_argument("bundle", help="private source-text/v1 JSON bundle")
    status_command.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bundle = SourceTextBundle.load(args.bundle)

    if args.command == "get":
        selection = bundle.get(args.locator)
        _emit_json(
            {
                "command": "text.get",
                "schema": bundle.schema,
                "identity": bundle.identity.to_dict(),
                "locator": selection.locator,
                "document_node_id": selection.document_node_id,
                "span": {"start": selection.start, "end": selection.end},
                "text": selection.text,
                "provenance": [fragment.to_dict() for fragment in selection.fragments],
                "text_sha256": bundle.text_sha256,
                "bundle_sha256": bundle.bundle_sha256,
            },
            compact=args.compact,
        )
        return 0

    if args.command == "status":
        _emit_json(
            {
                "command": "text.status",
                "schema": bundle.schema,
                "identity": bundle.identity.to_dict(),
                "canonical_text_bytes": len(bundle.canonical_text.encode("utf-8")),
                "fragment_count": len(bundle.fragments),
                "index_count": len(bundle.index),
                "diagnostic_count": len(bundle.diagnostics),
                "text_sha256": bundle.text_sha256,
                "bundle_sha256": bundle.bundle_sha256,
            },
            compact=args.compact,
        )
        return 0

    raise AssertionError(f"unexpected source text command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
