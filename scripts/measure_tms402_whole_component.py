#!/usr/bin/env python3
"""Reproduce source-safe whole-component TMS 402/602-16 OCR measurements.

This script intentionally emits aggregate evidence only. Raster images, Tesseract TSV,
and recovered source expression live only in a temporary directory and are deleted at
process exit.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import fitz


SOURCE_SHA256 = "947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d"
SOURCE_BYTES = 53_081_346
SOURCE_PDF_PAGES = 430
DRIVE_OBJECT_ID = "196AOKw29ahOiQMhyqQJge1DaS_BlTXzd"
COMPONENT_FIRST_PAGE = 57
COMPONENT_FIRST_CODE_PAGE = 67
COMPONENT_LAST_PARALLEL_CANDIDATE_PAGE = 299
COMPONENT_LAST_PAGE = 320
RENDER_SCALE = 2.0
ENCODED_DPI = 96
EXPECTED_PYMUPDF = "1.26.7"
EXPECTED_TESSERACT = "5.5.0"
TESSERACT_PSM = 6
BODY_TOP_PT = 65.0
BODY_BOTTOM_PT = 750.0
AUTHORITY_BOUNDARY_X_PT = 306.0
RUNNING_HEADER_BOTTOM_PT = 100.0
_HEADER_CODE = re.compile(r"\bCODE\b")
_HEADER_COMMENTARY = re.compile(r"\bCOMMENTARY\b")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class RecoveredLine:
    page: int
    text: str
    left: float
    top: float
    right: float
    bottom: float


@dataclass(slots=True)
class _LineBuilder:
    words: list[str]
    left: int
    top: int
    right: int
    bottom: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tesseract_version() -> str:
    result = subprocess.run(
        ["tesseract", "--version"],
        check=True,
        text=True,
        capture_output=True,
    )
    first = result.stdout.splitlines()[0].strip()
    parts = first.split()
    if len(parts) < 2 or parts[0].lower() != "tesseract":
        raise RuntimeError(f"unexpected tesseract --version output: {first!r}")
    return parts[1]


def _verify_runtime(source: Path) -> tuple[str, str]:
    if not source.is_file():
        raise FileNotFoundError(source)
    size = source.stat().st_size
    if size != SOURCE_BYTES:
        raise ValueError(f"source byte count {size} != expected {SOURCE_BYTES}")
    digest = _sha256(source)
    if digest != SOURCE_SHA256:
        raise ValueError(f"source SHA-256 {digest} != expected {SOURCE_SHA256}")

    pymupdf_version = fitz.VersionBind
    if pymupdf_version != EXPECTED_PYMUPDF:
        raise RuntimeError(
            f"PyMuPDF {pymupdf_version} != evidence recipe {EXPECTED_PYMUPDF}"
        )
    tesseract_version = _tesseract_version()
    if tesseract_version != EXPECTED_TESSERACT:
        raise RuntimeError(
            f"Tesseract {tesseract_version} != evidence recipe {EXPECTED_TESSERACT}"
        )

    with fitz.open(source) as document:
        if document.page_count != SOURCE_PDF_PAGES:
            raise ValueError(
                f"source page count {document.page_count} != expected {SOURCE_PDF_PAGES}"
            )
    return pymupdf_version, tesseract_version


def _render_page(source: Path, page_number: int, image_path: Path) -> None:
    with fitz.open(source) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE),
            colorspace=fitz.csGRAY,
            alpha=False,
        )
        pixmap.set_dpi(ENCODED_DPI, ENCODED_DPI)
        pixmap.save(image_path)


def _ocr_page(source: Path, page_number: int, workdir: Path) -> Path:
    image_path = workdir / f"page-{page_number:03d}.png"
    tsv_path = workdir / f"page-{page_number:03d}.tsv"
    _render_page(source, page_number, image_path)
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "OMP_THREAD_LIMIT": "1"})
    with tsv_path.open("wb") as output:
        subprocess.run(
            [
                "tesseract",
                str(image_path),
                "stdout",
                "--psm",
                str(TESSERACT_PSM),
                "tsv",
            ],
            check=True,
            stdout=output,
            stderr=subprocess.PIPE,
            env=environment,
        )
    image_path.unlink()
    return tsv_path


def _aggregate_tsv(page_number: int, tsv_path: Path) -> tuple[RecoveredLine, ...]:
    groups: dict[tuple[int, int, int], _LineBuilder] = {}
    with tsv_path.open(encoding="utf-8") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            if row.get("level") != "5":
                continue
            text = (row.get("text") or "").strip()
            if not text:
                continue
            key = (
                int(row["block_num"]),
                int(row["par_num"]),
                int(row["line_num"]),
            )
            left = int(row["left"])
            top = int(row["top"])
            right = left + int(row["width"])
            bottom = top + int(row["height"])
            builder = groups.get(key)
            if builder is None:
                groups[key] = _LineBuilder(
                    words=[text],
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            else:
                builder.words.append(text)
                builder.left = min(builder.left, left)
                builder.top = min(builder.top, top)
                builder.right = max(builder.right, right)
                builder.bottom = max(builder.bottom, bottom)

    lines = [
        RecoveredLine(
            page=page_number,
            text=" ".join(builder.words),
            left=builder.left / RENDER_SCALE,
            top=builder.top / RENDER_SCALE,
            right=builder.right / RENDER_SCALE,
            bottom=builder.bottom / RENDER_SCALE,
        )
        for builder in groups.values()
    ]
    lines.sort(key=lambda line: (line.top, line.left, line.bottom, line.right, line.text))
    return tuple(lines)


def _has_parallel_header(lines: Iterable[RecoveredLine]) -> bool:
    for line in lines:
        if line.top >= RUNNING_HEADER_BOTTOM_PT:
            continue
        upper = line.text.upper()
        if _HEADER_CODE.search(upper) and _HEADER_COMMENTARY.search(upper):
            return True
    return False


def _parallel_pages(by_page: dict[int, tuple[RecoveredLine, ...]]) -> set[int]:
    supported = {COMPONENT_FIRST_CODE_PAGE}
    for page in range(
        COMPONENT_FIRST_CODE_PAGE + 1,
        COMPONENT_LAST_PARALLEL_CANDIDATE_PAGE + 1,
    ):
        if _has_parallel_header(by_page[page]):
            supported.add(page)
    return supported


def _role(line: RecoveredLine, parallel_pages: set[int]) -> str:
    if line.page not in parallel_pages:
        return "ambiguous"
    if line.top < BODY_TOP_PT or line.bottom > BODY_BOTTOM_PT:
        return "ambiguous"
    if line.right <= AUTHORITY_BOUNDARY_X_PT:
        return "normative"
    if line.left >= AUTHORITY_BOUNDARY_X_PT:
        return "commentary"
    return "ambiguous"


def _compact_ranges(values: Iterable[int]) -> str:
    numbers = sorted(set(values))
    ranges: list[str] = []
    index = 0
    while index < len(numbers):
        start = numbers[index]
        end = start
        while index + 1 < len(numbers) and numbers[index + 1] == end + 1:
            index += 1
            end = numbers[index]
        ranges.append(str(start) if start == end else f"{start}-{end}")
        index += 1
    return ", ".join(ranges)


def _duplicate_metrics(classified: Iterable[tuple[RecoveredLine, str]]) -> dict[str, int]:
    families: dict[str, list[str]] = defaultdict(list)
    for line, role in classified:
        if role == "ambiguous":
            continue
        normalized = _WHITESPACE.sub(" ", line.text).strip().casefold()
        if not normalized:
            continue
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        families[digest].append(role)

    duplicates = [roles for roles in families.values() if len(roles) > 1]
    return {
        "duplicate_digest_families": len(duplicates),
        "duplicate_occurrences_beyond_first": sum(len(roles) - 1 for roles in duplicates),
        "cross_role_duplicate_digest_families": sum(
            1
            for roles in duplicates
            if "normative" in roles and "commentary" in roles
        ),
    }


def measure(source: Path, *, workers: int) -> dict[str, Any]:
    pymupdf_version, tesseract_version = _verify_runtime(source)
    pages = tuple(range(COMPONENT_FIRST_PAGE, COMPONENT_LAST_PAGE + 1))
    by_page: dict[int, tuple[RecoveredLine, ...]] = {}

    with tempfile.TemporaryDirectory(prefix="tms402-replay-") as directory:
        workdir = Path(directory)
        if workers == 1:
            paths = [_ocr_page(source, page, workdir) for page in pages]
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                paths = list(
                    executor.map(
                        lambda page: _ocr_page(source, page, workdir),
                        pages,
                    )
                )
        for page, path in zip(pages, paths, strict=True):
            by_page[page] = _aggregate_tsv(page, path)

    parallel_pages = _parallel_pages(by_page)
    all_lines = tuple(line for page in pages for line in by_page[page])
    classified = tuple((line, _role(line, parallel_pages)) for line in all_lines)
    roles = Counter(role for _, role in classified)
    unsupported = [page for page in pages if page not in parallel_pages]
    representative_pages = (60, 67, 68, 300, 310, 320)
    duplicates = _duplicate_metrics(classified)

    return {
        "schema": "tms402-whole-component-replay-v2",
        "component": "tms-402-16",
        "source": {
            "drive_object_id": DRIVE_OBJECT_ID,
            "sha256": SOURCE_SHA256,
            "byte_count": SOURCE_BYTES,
            "pdf_page_count": SOURCE_PDF_PAGES,
            "canonical_pdf_pages": [COMPONENT_FIRST_PAGE, COMPONENT_LAST_PAGE],
        },
        "recovery": {
            "renderer": f"PyMuPDF {pymupdf_version}",
            "render_matrix": [RENDER_SCALE, RENDER_SCALE],
            "render_mode": "8-bit grayscale PNG",
            "encoded_dpi": ENCODED_DPI,
            "ocr": f"tesseract {tesseract_version}",
            "tesseract_psm": TESSERACT_PSM,
            "omp_thread_limit": 1,
            "ocr_invocation": "one isolated Tesseract process per PDF page",
            "tsv_aggregation": "non-empty level-5 words grouped by (block_num, par_num, line_num); bbox is word-bbox union",
            "coordinate_space": "pdf_points via raster coordinates / 2.0",
            "recovered_text_retained": False,
        },
        "layout_evidence": {
            "parallel_page_rule": (
                "PDF page 67, or PDF pages 68-299 with at least one recovered line "
                "above 100 PDF points containing whole-word CODE and COMMENTARY; "
                "all other pages fail closed as unsupported"
            ),
            "parallel_code_commentary_pages": len(parallel_pages),
            "unsupported_pages": len(unsupported),
            "unsupported_page_ranges": _compact_ranges(unsupported),
            "body_y_bounds_pdf_points": [BODY_TOP_PT, BODY_BOTTOM_PT],
            "parallel_authority_boundary_x_pdf_points": AUTHORITY_BOUNDARY_X_PT,
        },
        "measurement": {
            "recovered_lines": len(all_lines),
            "recognized_observations": roles["normative"] + roles["commentary"],
            "normative": roles["normative"],
            "commentary": roles["commentary"],
            "ambiguous": roles["ambiguous"],
            **duplicates,
        },
        "representative_recovered_line_counts": {
            str(page): len(by_page[page]) for page in representative_pages
        },
        "duplicate_policy": {
            "population": "recognized normative/commentary observations only",
            "normalization": "Unicode casefold after whitespace collapse and strip",
            "retained_values": "aggregate counts only; line text and digests are ephemeral",
        },
        "interpretation": [
            "This v2 replay replaces the irreproducible v1 measurement with a fully executable exact-source recipe.",
            "Only explicit recovered CODE/COMMENTARY running-header evidence permits parallel-layout authority assignment; unsupported layouts remain ambiguous.",
            "Recovered OCR expression, page images, TSV rows, and duplicate digests are not retained in Git.",
            "The ambiguous population is measured evidence and is not coerced into normative or commentary roles.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure the exact retained TMS 402 component without retaining recovered source expression."
    )
    parser.add_argument("source", type=Path, help="exact retained tms-402_602-2016.pdf")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel page-process orchestration; each Tesseract process remains OMP_THREAD_LIMIT=1",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    report = measure(args.source, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    measurement = report["measurement"]
    print(args.output)
    print(
        f"recovered_lines={measurement['recovered_lines']} "
        f"recognized={measurement['recognized_observations']} "
        f"ambiguous={measurement['ambiguous']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
