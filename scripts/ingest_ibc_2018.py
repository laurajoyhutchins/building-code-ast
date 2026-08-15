#!/usr/bin/env python3
"""Generate private ChapterSeed JSON files from a local 2018 IBC PDF."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from building_code_ast.ingest.ibc2018 import (
    LAYOUT_ANALYSIS_VERSION,
    SEED_VERSION,
    build_chapter_seed,
    extract_ibc2018_layout,
    parse_chapter_numbers,
)
from building_code_ast.ingest.local_runner import (
    prepare_output_dir as _prepare_output_dir,
    source_digest,
    warn_private_output,
    write_json,
    write_manifest,
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
    """Prepare the IBC output directory using the shared local runner policy."""

    _prepare_output_dir(
        output_dir,
        force=force,
        generated_name_pattern=r"chapter-\d+\.json",
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
    output = Path(output_dir)
    prepare_output_dir(output, force=force)
    layout = extract_ibc2018_layout(source, selected)
    source_sha256, source_size = source_digest(source)
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
        chapter_path = output / f"chapter-{chapter_number}.json"
        write_json(chapter_path, seed.to_dict())
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

    return write_manifest(
        output,
        {
            "seed_set_version": SEED_VERSION,
            "layout_analysis_version": LAYOUT_ANALYSIS_VERSION,
            "source_manifest": first_manifest,
            "chapters": records,
            "publication_boundary": "private-local-output",
            "reconstruction": "positioned-glyph adaptive layout reconstruction",
        },
        written,
    )


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
    warn_private_output("IBC")
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