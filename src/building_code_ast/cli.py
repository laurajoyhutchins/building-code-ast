"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ingest.pdf_layout import extract_pdf_layout
from .parser import parse_provision
from .retrieval import (
    SOURCE_EVIDENCE_STORE_VERSION,
    LexicalSearchMode,
    SourceArtifactIdentity,
    expand_evidence_context,
    extract_layout_evidence,
    get_page_evidence,
    read_evidence_store,
    rebuild_evidence_store,
    search_evidence_store,
    verify_source_artifact,
)


def _read_source(args: argparse.Namespace) -> str:
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("provide provision text, --file, or standard input")


def _add_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-id", required=True, help="registered source provenance identity")
    parser.add_argument(
        "--publication-key",
        required=True,
        help="retrieval-local publication filter key",
    )
    parser.add_argument("--sha256", required=True, help="exact lowercase source SHA-256")
    parser.add_argument("--size", required=True, type=int, help="exact source byte size")
    parser.add_argument(
        "--page-count",
        required=True,
        type=int,
        help="exact physical PDF page count",
    )


def _add_store_and_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", required=True, help="local disposable SQLite evidence store")
    _add_artifact_arguments(parser)
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")


def _artifact_from_args(args: argparse.Namespace) -> SourceArtifactIdentity:
    return SourceArtifactIdentity(
        source_id=args.source_id,
        publication_key=args.publication_key,
        sha256=args.sha256,
        size=args.size,
        page_count=args.page_count,
    )


def _emit_json(payload: dict[str, Any], *, compact: bool) -> None:
    indent = None if compact else 2
    print(json.dumps(payload, indent=indent, sort_keys=True))


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

    source_command = subcommands.add_parser(
        "source",
        help="index and navigate local source retrieval evidence",
    )
    source_subcommands = source_command.add_subparsers(dest="source_command", required=True)

    index_command = source_subcommands.add_parser(
        "index",
        help="verify a PDF and rebuild its local retrieval evidence store",
    )
    index_command.add_argument("pdf", help="private PDF source path")
    index_command.add_argument("--store", required=True, help="local disposable SQLite evidence store")
    _add_artifact_arguments(index_command)
    index_command.add_argument(
        "--extraction-method",
        default="pymupdf-blocks/1",
        help="identity of the positioned-PDF extraction method",
    )
    index_command.add_argument("--compact", action="store_true", help="emit compact JSON")

    search_command = source_subcommands.add_parser("search", help="lexically search indexed evidence")
    search_command.add_argument("query", help="literal, phrase, or token query")
    _add_store_and_artifact_arguments(search_command)
    search_command.add_argument(
        "--mode",
        choices=[mode.value for mode in LexicalSearchMode],
        default=LexicalSearchMode.TOKEN.value,
    )
    search_command.add_argument("--limit", type=int, default=20)

    show_command = source_subcommands.add_parser("show", help="show one evidence record with context")
    show_command.add_argument("evidence_id", help="durable retrieval evidence ID")
    _add_store_and_artifact_arguments(show_command)
    show_command.add_argument("--before", type=int, default=1)
    show_command.add_argument("--after", type=int, default=1)
    show_command.add_argument(
        "--page-local",
        action="store_true",
        help="do not expand context across the physical PDF page boundary",
    )

    page_command = source_subcommands.add_parser("page", help="show all evidence on one PDF page")
    page_command.add_argument("pdf_page", type=int, help="one-based physical PDF page")
    _add_store_and_artifact_arguments(page_command)

    status_command = source_subcommands.add_parser("status", help="validate and summarize an evidence store")
    _add_store_and_artifact_arguments(status_command)

    return parser


def _run_source(args: argparse.Namespace) -> int:
    artifact = _artifact_from_args(args)

    if args.source_command == "index":
        source = Path(args.pdf)
        verify_source_artifact(source, artifact)
        layout = extract_pdf_layout(source)
        evidence = extract_layout_evidence(
            layout,
            artifact=artifact,
            extraction_method=args.extraction_method,
        )
        rebuild_evidence_store(args.store, artifact=artifact, evidence=evidence)
        _emit_json(
            {
                "command": "source.index",
                "source_id": artifact.source_id,
                "publication_key": artifact.publication_key,
                "source_sha256": artifact.sha256,
                "page_count": artifact.page_count,
                "evidence_count": len(evidence),
                "store_version": SOURCE_EVIDENCE_STORE_VERSION,
            },
            compact=args.compact,
        )
        return 0

    if args.source_command == "search":
        results = search_evidence_store(
            args.store,
            artifact=artifact,
            query=args.query,
            mode=args.mode,
            limit=args.limit,
        )
        _emit_json(
            {
                "command": "source.search",
                "artifact": artifact.to_dict(),
                "query": args.query,
                "mode": args.mode,
                "results": [result.to_dict() for result in results],
            },
            compact=args.compact,
        )
        return 0

    if args.source_command == "show":
        context = expand_evidence_context(
            args.store,
            artifact=artifact,
            evidence_id=args.evidence_id,
            before=args.before,
            after=args.after,
            page_local=args.page_local,
        )
        _emit_json(
            {
                "command": "source.show",
                "artifact": artifact.to_dict(),
                "context": context.to_dict(),
            },
            compact=args.compact,
        )
        return 0

    if args.source_command == "page":
        evidence = get_page_evidence(
            args.store,
            artifact=artifact,
            pdf_page=args.pdf_page,
        )
        _emit_json(
            {
                "command": "source.page",
                "artifact": artifact.to_dict(),
                "pdf_page": args.pdf_page,
                "evidence": [item.to_dict() for item in evidence],
            },
            compact=args.compact,
        )
        return 0

    if args.source_command == "status":
        evidence = read_evidence_store(args.store, artifact=artifact)
        _emit_json(
            {
                "command": "source.status",
                "artifact": artifact.to_dict(),
                "store_version": SOURCE_EVIDENCE_STORE_VERSION,
                "evidence_count": len(evidence),
            },
            compact=args.compact,
        )
        return 0

    raise AssertionError(f"unexpected source command: {args.source_command}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "source":
        return _run_source(args)
    if args.command != "parse":
        raise AssertionError(f"unexpected command: {args.command}")

    ast = parse_provision(
        _read_source(args),
        source_artifact_id=args.source_artifact_id,
        provision_locator=args.provision_locator,
    )
    _emit_json(ast.to_dict(), compact=args.compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
