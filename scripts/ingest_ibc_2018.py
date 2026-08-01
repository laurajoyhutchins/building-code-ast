#!/usr/bin/env python3
"""Generate private ChapterSeed JSON files from a local 2018 IBC PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

from building_code_ast.ingest.ibc2018 import (
    build_chapter_seed,
    extract_ibc2018_layout,
    parse_chapter_numbers,
)


DEFAULT_CHAPTERS = ("1", "2", "3")


def parse_chapters(value: str) -> tuple[str, ...]:
    try:
        return parse_chapter_numbers(
            item.strip() for item in value.split(",") if item.strip()
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def prepare_output_dir(output_dir: Path, *, force: bool) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
        return

    children = tuple(output_dir.iterdir())
    if not children:
        return
    if not force:
        raise FileExistsError(
            f"output directory is not empty: {output_dir}; pass --force to replace it"
        )

    unexpected = [
        child.name
        for child in children
        if not child.is_file()
        or (
            child.name != "manifest.json"
            and re.fullmatch(r"chapter-\d+\.json", child.name) is None
        )
    ]
    if unexpected:
        raise FileExistsError(
            "output directory contains unexpected entries and will not be deleted: "
            + ", ".join(sorted(unexpected))
        )
    for child in children:
        child.unlink()


def _source_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_outputs(
    source_path: Path,
    output_dir: Path,
    *,
    chapters: Iterable[str],
    force: bool,
) -> tuple[Path, ...]:
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    selected = parse_chapter_numbers(chapters)
    prepare_output_dir(Path(output_dir), force=force)
    layout = extract_ibc2018_layout(source, selected)
    source_sha256, source_size = _source_digest(source)
    records: list[dict[str, object]] = []
    written: list[Path] = []
    first_manifest: dict[str, object] | None = None

    for chapter_number in selected:
        seed = build_chapter_seed(
            layout,
            chapter_number,
            source_sha256=source_sha256,
            source_size=source_size,
        )
        chapter_path = Path(output_dir) / f"chapter-{chapter_number}.json"
        _write_json(chapter_path, seed.to_dict())
        written.append(chapter_path)
        records.append(
            {
                "number": seed.chapter_number,
                "title": seed.chapter_title,
                "physical_pdf_pages": list(seed.source_pages),
                "file": chapter_path.name,
            }
        )
        if first_manifest is None:
            first_manifest = seed.source_manifest.to_dict()

    if first_manifest is None:
        raise ValueError("at least one chapter number is required")

    manifest_path = Path(output_dir) / "manifest.json"
    _write_json(
        manifest_path,
        {
            "seed_set_version": "0.1.0",
            "source_manifest": first_manifest,
            "chapters": records,
            "publication_boundary": "private-local-output",
            "reconstruction": "positioned-glyph visual-line reconstruction",
        },
    )
    return (manifest_path, *written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate private, provenance-preserving ChapterSeed files from a "
            "locally supplied 2018 IBC PDF."
        )
    )
    parser.add_argument("pdf", type=Path, help="path to the local IBC 2018 PDF")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="private output directory; generated files may contain IBC text",
    )
    parser.add_argument(
        "--chapters",
        type=parse_chapters,
        default=DEFAULT_CHAPTERS,
        help="comma-separated supported chapters (default: 1,2,3)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace only recognized generated files in a nonempty output directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(
        "Warning: generated files may contain copyrighted IBC text. "
        "Keep the output private and outside public Git.",
        file=sys.stderr,
    )
    written = write_outputs(
        args.pdf,
        args.output_dir,
        chapters=args.chapters,
        force=args.force,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
