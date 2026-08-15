#!/usr/bin/env python3
"""Generate private ArticleSeed JSON files from a locally supplied NEC 2017 PDF."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from building_code_ast.ingest.local_runner import (
    prepare_output_dir as _prepare_output_dir,
    source_digest,
    warn_private_output,
    write_json,
    write_manifest,
)
from building_code_ast.ingest.nec2017 import build_article_seed
from building_code_ast.ingest.pdf_layout import PdfLayoutDocument, extract_pdf_layout


DEFAULT_ARTICLES = ("90", "100", "110")


def parse_articles(value: str) -> tuple[str, ...]:
    articles = tuple(item.strip() for item in value.split(",") if item.strip())
    if not articles:
        raise argparse.ArgumentTypeError("at least one article number is required")
    if any(not article.isdigit() for article in articles):
        raise argparse.ArgumentTypeError("article numbers must contain digits only")
    if len(set(articles)) != len(articles):
        raise argparse.ArgumentTypeError("article numbers must not be duplicated")
    return articles


def prepare_output_dir(output_dir: Path, *, force: bool) -> None:
    """Prepare the NEC output directory using the shared local runner policy."""

    _prepare_output_dir(
        output_dir,
        force=force,
        generated_name_pattern=r"article-\d+\.json",
    )


def write_outputs(
    layout: PdfLayoutDocument,
    source_path: Path,
    output_dir: Path,
    *,
    articles: Iterable[str],
    force: bool,
) -> tuple[Path, ...]:
    """Write a private seed set from an already extracted PDF layout."""

    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    output = Path(output_dir)
    prepare_output_dir(output, force=force)

    source_sha256, source_size = source_digest(source)
    article_records: list[dict[str, str]] = []
    written: list[Path] = []
    first_manifest: dict[str, object] | None = None

    for article_number in tuple(articles):
        seed = build_article_seed(
            layout,
            article_number,
            source_sha256=source_sha256,
            source_size=source_size,
        )
        article_path = output / f"article-{article_number}.json"
        write_json(article_path, seed.to_dict())
        written.append(article_path)
        article_records.append(
            {
                "number": seed.article_number,
                "title": seed.article_title,
                "file": article_path.name,
            }
        )
        if first_manifest is None:
            first_manifest = seed.source_manifest.to_dict()

    if first_manifest is None:
        raise ValueError("at least one article number is required")

    return write_manifest(
        output,
        {
            "seed_set_version": "0.1.0",
            "source_manifest": first_manifest,
            "articles": article_records,
            "publication_boundary": "private-local-output",
        },
        written,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate private, provenance-preserving ArticleSeed files from a "
            "locally supplied 2017 NEC PDF."
        )
    )
    parser.add_argument("pdf", type=Path, help="path to the local NEC 2017 PDF")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="private output directory; generated files may contain NEC text",
    )
    parser.add_argument(
        "--articles",
        type=parse_articles,
        default=DEFAULT_ARTICLES,
        help="comma-separated article numbers (default: 90,100,110)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace a nonempty output directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    warn_private_output("NEC")
    layout = extract_pdf_layout(args.pdf)
    written = write_outputs(
        layout,
        args.pdf,
        args.output_dir,
        articles=args.articles,
        force=args.force,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())