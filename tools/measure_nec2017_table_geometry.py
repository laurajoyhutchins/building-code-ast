#!/usr/bin/env python3
"""Replay source-safe NEC 2017 table geometry from an exact local PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

from building_code_ast.ingest.layout_analysis import (
    PageLines,
    RuleSegment,
    SourceFragment,
    VisualLine,
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
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required; install building-code-ast[nec-pdf]") from exc

    pages: list[PageLines] = []
    captions: list[TableCaptionAnchor] = []
    unsupported_nonhorizontal = 0
    with fitz.open(path) as document:
        if document.page_count != NEC2017_PAGE_COUNT:
            raise ValueError(f"NEC 2017 exact source requires {NEC2017_PAGE_COUNT} pages")
        for page_index in range(document.page_count):
            page_number = page_index + 1
            page = document[page_index]
            raw = page.get_text("dict", sort=False)
            lines: list[VisualLine] = []
            for raw_block in raw.get("blocks", ()):
                if int(raw_block.get("type", 0)) != 0:
                    continue
                block_number = int(raw_block.get("number", -1))
                block_parts: list[str] = []
                block_direction = (1.0, 0.0)
                direction_set = False
                for raw_line in raw_block.get("lines", ()):
                    fragments: list[SourceFragment] = []
                    for raw_span in raw_line.get("spans", ()):
                        text = str(raw_span.get("text", ""))
                        if not text:
                            continue
                        fragments.append(
                            SourceFragment(
                                page_number=page_number,
                                bbox=tuple(float(value) for value in raw_span.get("bbox", (0, 0, 0, 0))),
                                block_number=block_number,
                                raw_text=text,
                                font_size=float(raw_span.get("size", 0.0)),
                                font_name=str(raw_span.get("font", "")),
                            )
                        )
                    if not fragments:
                        continue
                    text = "".join(fragment.raw_text for fragment in fragments)
                    block_parts.append(text)
                    if not direction_set and text.strip():
                        direction = raw_line.get("dir", (1.0, 0.0))
                        block_direction = (float(direction[0]), float(direction[1]))
                        direction_set = True
                    bbox = tuple(float(value) for value in raw_line.get("bbox", (0, 0, 0, 0)))
                    font_size = statistics.median(
                        [fragment.font_size for fragment in fragments if fragment.font_size > 0.0]
                        or [0.0]
                    )
                    lines.append(
                        VisualLine(
                            page_number=page_number,
                            bbox=bbox,
                            text=text,
                            fragments=tuple(fragments),
                            font_size=font_size,
                            font_name=fragments[0].font_name,
                        )
                    )

                block_text = _normalize(" ".join(block_parts))
                if _TABLE_RE.match(block_text):
                    dx, dy = block_direction
                    block_bbox = tuple(
                        float(value) for value in raw_block.get("bbox", (0, 0, 0, 0))
                    )
                    if abs(dy) <= 1e-9 and dx > 0.0:
                        captions.append(
                            TableCaptionAnchor(
                                caption_id=f"p{page_number}:b{block_number}",
                                page_number=page_number,
                                bbox=block_bbox,
                            )
                        )
                    else:
                        unsupported_nonhorizontal += 1

            rules: list[RuleSegment] = []
            for drawing in page.get_drawings():
                for item in drawing.get("items", ()):
                    kind = item[0]
                    if kind == "l":
                        start, end = item[1], item[2]
                        rules.append(
                            RuleSegment(page_number, float(start.x), float(start.y), float(end.x), float(end.y))
                        )
                    elif kind == "re":
                        rect = item[1]
                        x0, y0, x1, y1 = float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)
                        rules.extend(
                            (
                                RuleSegment(page_number, x0, y0, x1, y0),
                                RuleSegment(page_number, x1, y0, x1, y1),
                                RuleSegment(page_number, x1, y1, x0, y1),
                                RuleSegment(page_number, x0, y1, x0, y0),
                            )
                        )
            pages.append(
                PageLines(
                    page_number=page_number,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    lines=tuple(lines),
                    rules=tuple(rules),
                )
            )
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
