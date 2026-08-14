"""Publication-neutral retained-PDF inspection and page-surface evidence.

This module owns factual inspection of immutable retained PDF bytes: regular-file
identity, exact hashing, basic PDF metadata, and text/image page-surface facts.
It contains no publication title, edition, printing, component range, locator
meaning, authority role, or semantic interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Callable, Mapping, Sequence


class RetainedPdfInspectionError(ValueError):
    """Raised when retained PDF identity or factual inspection fails closed."""


@dataclass(frozen=True, slots=True)
class PageSurfaceObservation:
    page_number: int
    has_embedded_text: bool
    raster_image_count: int
    max_image_coverage_ratio: float | None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.raster_image_count < 0:
            raise ValueError("raster_image_count must be non-negative")
        if self.max_image_coverage_ratio is not None and not 0.0 <= self.max_image_coverage_ratio <= 1.0:
            raise ValueError("max_image_coverage_ratio must be within 0..1")


PdfObserver = Callable[[Path], Mapping[str, object]]


def _full_page_single_image(item: PageSurfaceObservation) -> bool:
    return (
        not item.has_embedded_text
        and item.raster_image_count == 1
        and item.max_image_coverage_ratio is not None
        and item.max_image_coverage_ratio >= 0.995
    )


def summarize_image_only_pages(
    observations: Sequence[PageSurfaceObservation],
) -> dict[str, object]:
    """Return source-safe page-surface coverage for an arbitrary PDF component."""

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    expected_pages = tuple(range(1, len(ordered) + 1))
    actual_pages = tuple(item.page_number for item in ordered)
    if actual_pages != expected_pages:
        raise ValueError("observations must cover each one-based component page exactly once")

    image_only = tuple(item for item in ordered if not item.has_embedded_text)
    image_only_pages = tuple(item.page_number for item in image_only)

    runs: list[tuple[int, int]] = []
    for page in image_only_pages:
        if not runs or page != runs[-1][1] + 1:
            runs.append((page, page))
        else:
            start, _end = runs[-1]
            runs[-1] = (start, page)

    single_full_page = tuple(item for item in image_only if _full_page_single_image(item))

    return {
        "page_count": len(ordered),
        "embedded_text_page_count": len(ordered) - len(image_only),
        "image_only_page_count": len(image_only),
        "image_only_pages": list(image_only_pages),
        "image_only_run_count": len(runs),
        "image_only_runs": [
            {
                "start_page": start,
                "end_page": end,
                "page_count": end - start + 1,
            }
            for start, end in runs
        ],
        "single_full_page_image_count": len(single_full_page),
        "all_image_only_pages_are_single_full_page_images": len(single_full_page) == len(image_only),
    }


def _hash_regular_file(source: Path, expected_size_bytes: int) -> tuple[str, int]:
    if expected_size_bytes < 1:
        raise RetainedPdfInspectionError("expected size must be positive")

    try:
        before = os.lstat(source)
    except OSError as exc:
        raise RetainedPdfInspectionError(f"cannot stat retained source: {exc}") from exc
    if os.path.islink(source):
        raise RetainedPdfInspectionError("retained source must not be a symlink")
    if not source.is_file():
        raise RetainedPdfInspectionError("retained source must be a regular file")
    if before.st_size != expected_size_bytes:
        raise RetainedPdfInspectionError(
            f"retained source size mismatch: expected {expected_size_bytes}, got {before.st_size}"
        )

    digest = hashlib.sha256()
    observed_size = 0
    try:
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                observed_size += len(chunk)
    except OSError as exc:
        raise RetainedPdfInspectionError(f"cannot read retained source: {exc}") from exc

    try:
        after = os.lstat(source)
    except OSError as exc:
        raise RetainedPdfInspectionError(f"cannot restat retained source: {exc}") from exc
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or observed_size != expected_size_bytes
    ):
        raise RetainedPdfInspectionError("retained source changed during hashing")
    return digest.hexdigest(), observed_size


def sanitize_pdf_observation(observation: Mapping[str, object]) -> dict[str, object]:
    """Keep only factual, source-safe PDF inspection fields."""

    allowed = (
        "page_count",
        "pdf_version",
        "encrypted",
        "needs_password",
        "permissions_raw",
        "page_label_rules",
        "outline",
        "text_layer",
        "page_geometry",
        "tool",
    )
    missing = [key for key in allowed if key not in observation]
    if missing:
        raise RetainedPdfInspectionError(
            "PDF observer omitted required factual fields: " + ", ".join(missing)
        )
    return {key: observation[key] for key in allowed}


def observe_pdf_with_pymupdf(source: Path) -> dict[str, object]:
    """Inspect factual PDF metadata with the optional generic PDF dependency."""

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RetainedPdfInspectionError(
            "PyMuPDF is required for retained PDF inspection; install building-code-ast[pdf-inspection]"
        ) from exc

    try:
        document = fitz.open(source)
    except Exception as exc:  # pragma: no cover - delegated parser boundary
        raise RetainedPdfInspectionError(f"cannot open retained PDF: {exc}") from exc

    try:
        page_count = document.page_count
        metadata = document.metadata or {}
        toc = document.get_toc(simple=False) or []
        labels = document.get_page_labels() or []
        pages_without_text: list[int] = []
        sizes: set[tuple[float, float]] = set()
        for page_index in range(page_count):
            page = document[page_index]
            text = page.get_text("text")
            if not text.strip():
                pages_without_text.append(page_index + 1)
            sizes.add((round(float(page.rect.width), 3), round(float(page.rect.height), 3)))

        valid_targets = 0
        invalid_targets = 0
        max_depth = 0
        for item in toc:
            if len(item) < 3:
                continue
            level = int(item[0])
            target = int(item[2])
            max_depth = max(max_depth, level)
            if 1 <= target <= page_count:
                valid_targets += 1
            else:
                invalid_targets += 1

        version = str(metadata.get("format", ""))
        if version.lower().startswith("pdf "):
            version = version[4:]
        return {
            "page_count": page_count,
            "pdf_version": version,
            "encrypted": bool(document.is_encrypted),
            "needs_password": bool(document.needs_pass),
            "permissions_raw": int(document.permissions),
            "page_label_rules": labels,
            "outline": {
                "entry_count": len(toc),
                "max_depth": max_depth,
                "valid_target_count": valid_targets,
                "invalid_target_count": invalid_targets,
            },
            "text_layer": {
                "pages_with_text": page_count - len(pages_without_text),
                "pages_without_text": pages_without_text,
            },
            "page_geometry": {
                "distinct_page_sizes": [
                    {"width": width, "height": height} for width, height in sorted(sizes)
                ]
            },
            "tool": {"name": "PyMuPDF", "version": getattr(fitz, "VersionBind", "unknown")},
        }
    finally:
        document.close()


def inspect_retained_pdf(
    source: Path,
    *,
    expected_size_bytes: int,
    pdf_observer: PdfObserver | None = None,
) -> dict[str, object]:
    """Inspect immutable retained PDF bytes without publication interpretation."""

    digest, observed_size = _hash_regular_file(source, expected_size_bytes)
    observer = pdf_observer or observe_pdf_with_pymupdf
    pdf = sanitize_pdf_observation(observer(source))
    return {
        "size_bytes": observed_size,
        "sha256": digest,
        "pdf": pdf,
    }
