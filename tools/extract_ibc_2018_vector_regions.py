#!/usr/bin/env python3
"""Extract private vector-region evidence from the exact 2018 IBC PDF."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from building_code_ast.ingest.ibc2018.vector_regions import (
    SOURCE_PAGE_COUNT,
    SOURCE_SHA256,
    SOURCE_SIZE_BYTES,
    extract_page_vector_regions,
    validate_vector_evidence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--chunk-size", type=int, default=16)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _chunks(values: Iterable[int], size: int) -> list[list[int]]:
    material = list(values)
    return [material[index : index + size] for index in range(0, len(material), size)]


def _extract_chunk(source_pdf: str, page_indexes: list[int]) -> list[dict[str, Any]]:
    import fitz

    document = fitz.open(source_pdf)
    try:
        return [
            extract_page_vector_regions(document[index], pdf_page=index + 1)
            for index in page_indexes
        ]
    finally:
        document.close()


def build_evidence(source_pdf: Path, *, workers: int, chunk_size: int) -> dict[str, Any]:
    size_bytes = source_pdf.stat().st_size
    if size_bytes != SOURCE_SIZE_BYTES:
        raise ValueError(f"source size mismatch: expected {SOURCE_SIZE_BYTES}, got {size_bytes}")
    digest = sha256_file(source_pdf)
    if digest != SOURCE_SHA256:
        raise ValueError(f"source SHA-256 mismatch: expected {SOURCE_SHA256}, got {digest}")

    import fitz

    document = fitz.open(source_pdf)
    try:
        page_count = int(document.page_count)
    finally:
        document.close()
    if page_count != SOURCE_PAGE_COUNT:
        raise ValueError(f"source page-count mismatch: expected {SOURCE_PAGE_COUNT}, got {page_count}")

    page_chunks = _chunks(range(page_count), max(1, chunk_size))
    if workers <= 1:
        nested = [_extract_chunk(str(source_pdf), indexes) for indexes in page_chunks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            nested = list(executor.map(_extract_chunk, [str(source_pdf)] * len(page_chunks), page_chunks))
    pages = sorted((page for group in nested for page in group), key=lambda item: int(item["pdf_page"]))
    evidence = {
        "schema_version": "0.1.0",
        "source_sha256": digest,
        "source_size_bytes": size_bytes,
        "source_page_count": page_count,
        "pages": pages,
    }
    validate_vector_evidence(evidence)
    return evidence


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be at least 1")
    evidence = build_evidence(args.source_pdf, workers=args.workers, chunk_size=args.chunk_size)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output_json),
                "page_count": evidence["source_page_count"],
                "region_count": sum(len(page["regions"]) for page in evidence["pages"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
