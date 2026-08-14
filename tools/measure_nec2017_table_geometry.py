#!/usr/bin/env python3
"""Replay source-safe NEC 2017 table geometry from an exact local PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from building_code_ast.ingest.layout_analysis import (
    PageLines,
    clean_recurring_margins,
    detect_recurring_margins,
)
from building_code_ast.ingest.table_candidate_ownership import TableCaptionAnchor
from building_code_ast.nec2017_table_geometry_measurement import (
    NEC2017_PAGE_COUNT,
    NEC2017_SHA256,
    NEC2017_SIZE_BYTES,
    measure_nec2017_table_geometry,
)
from building_code_ast.pdf_observation import observe_pdf_pages

_TABLE_RE = re.compile(r"^\s*Table\s+(?:\d|[A-Z]+-\d)", re.IGNORECASE)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _source_identity(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _extract(path: Path) -> tuple[tuple[PageLines, ...], tuple[TableCaptionAnchor, ...], int]:
    observed_pages = observe_pdf_pages(path, expected_page_count=NEC2017_PAGE_COUNT)
    pages: list[PageLines] = []
    captions: list[TableCaptionAnchor] = []
    unsupported_nonhorizontal = 0

    for observed_page in observed_pages:
        pages.append(observed_page.to_page_lines())
        for block in observed_page.blocks:
            block_text = _normalize(block.text)
            if not _TABLE_RE.match(block_text):
                continue

            block_direction = (1.0, 0.0)
            for line in block.lines:
                if line.text.strip():
                    block_direction = line.direction
                    break
            dx, dy = block_direction
            if abs(dy) <= 1e-9 and dx > 0.0:
                captions.append(
                    TableCaptionAnchor(
                        caption_id=block.block_id,
                        page_number=observed_page.page_number,
                        bbox=block.bbox,
                    )
                )
            else:
                unsupported_nonhorizontal += 1

    return tuple(pages), tuple(captions), unsupported_nonhorizontal


def _run(path: Path) -> dict[str, object]:
    pages, captions, unsupported_nonhorizontal = _extract(path)
    margins = detect_recurring_margins(pages)
    cleaned = clean_recurring_margins(pages, margins)
    return measure_nec2017_table_geometry(
        cleaned,
        captions,
        source_sha256=NEC2017_SHA256,
        source_size=NEC2017_SIZE_BYTES,
        unsupported_nonhorizontal_caption_starts=unsupported_nonhorizontal,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, help="local exact retained NEC 2017 PDF")
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    digest, size = _source_identity(args.pdf)
    if digest != NEC2017_SHA256 or size != NEC2017_SIZE_BYTES:
        raise SystemExit("source identity does not match registered NEC 2017 artifact")

    measurements = [_run(args.pdf) for _ in range(args.repetitions)]
    identical = all(item == measurements[0] for item in measurements[1:])
    payload = {
        "artifact": "nec-2017-table-geometry-measurement",
        "measurement": measurements[0],
        "measurement_repetitions": args.repetitions,
        "repetitions_identical": identical,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if identical else 2


if __name__ == "__main__":
    raise SystemExit(main())
