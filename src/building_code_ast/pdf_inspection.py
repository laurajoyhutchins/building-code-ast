"""Publication-neutral retained-PDF inspection and page-surface evidence.

This module owns factual inspection of immutable retained PDF bytes: regular-file
identity, exact hashing, basic PDF metadata, and text/image page-surface facts.
It contains no publication title, edition, printing, component range, locator
meaning, authority role, or semantic interpretation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Mapping, Sequence


_FULL_PAGE_IMAGE_COVERAGE = 0.999


class RetainedPdfInspectionError(ValueError):
    """Raised when retained PDF identity or factual inspection fails closed."""


@dataclass(frozen=True, slots=True)
class PageSurfaceObservation:
    """Non-reconstructive page facts used to classify image-only pages."""

    page_number: int
    has_embedded_text: bool
    image_placement_count: int
    maximum_image_coverage_ratio: float

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.image_placement_count < 0:
            raise ValueError("image_placement_count must be non-negative")
        if not 0.0 <= self.maximum_image_coverage_ratio <= 1.0001:
            raise ValueError("maximum_image_coverage_ratio must be a page-area ratio")


PdfObserver = Callable[[Path], Mapping[str, object]]


def _contiguous_runs(page_numbers: Sequence[int]) -> list[list[int]]:
    if not page_numbers:
        return []
    runs: list[list[int]] = []
    first = previous = page_numbers[0]
    for page_number in page_numbers[1:]:
        if page_number == previous + 1:
            previous = page_number
            continue
        runs.append([first, previous])
        first = previous = page_number
    runs.append([first, previous])
    return runs


def summarize_image_only_pages(
    observations: Sequence[PageSurfaceObservation],
) -> dict[str, object]:
    """Return deterministic source-safe page-surface facts for any PDF component."""

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    expected_pages = tuple(range(1, len(ordered) + 1))
    observed_pages = tuple(item.page_number for item in ordered)
    if observed_pages != expected_pages:
        raise ValueError("observations must cover each one-based page exactly once")

    image_only = tuple(item for item in ordered if not item.has_embedded_text)
    image_only_pages = [item.page_number for item in image_only]
    runs = _contiguous_runs(image_only_pages)
    maximum_run_length = max((last - first + 1 for first, last in runs), default=0)
    all_single_full_page = all(
        item.image_placement_count == 1
        and item.maximum_image_coverage_ratio >= _FULL_PAGE_IMAGE_COVERAGE
        for item in image_only
    )

    return {
        "page_count": len(ordered),
        "pages_with_embedded_text": len(ordered) - len(image_only),
        "image_only_page_count": len(image_only),
        "image_only_pages": image_only_pages,
        "image_only_run_count": len(runs),
        "maximum_image_only_run_length": maximum_run_length,
        "all_image_only_pages_are_single_full_page_images": all_single_full_page,
        "full_page_image_minimum_coverage_ratio": _FULL_PAGE_IMAGE_COVERAGE,
        "image_only_runs": runs,
    }


def _hash_regular_file(source: Path, expected_size_bytes: int) -> tuple[str, int]:
    if expected_size_bytes < 1:
        raise RetainedPdfInspectionError("expected size must be positive")

    try:
        before = os.lstat(source)
    except FileNotFoundError as exc:
        raise RetainedPdfInspectionError("retained source file does not exist") from exc
    except OSError as exc:
        raise RetainedPdfInspectionError(f"cannot stat retained source: {exc}") from exc
    if os.path.islink(source):
        raise RetainedPdfInspectionError("retained source path must not be a symlink")
    if not source.is_file():
        raise RetainedPdfInspectionError("retained source path must be a regular file")
    if before.st_size != expected_size_bytes:
        raise RetainedPdfInspectionError(
            "retained source byte size does not match the expected artifact size: "
            f"expected {expected_size_bytes}, observed {before.st_size}"
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
        raise RetainedPdfInspectionError(
            "retained source changed while exact-byte verification was running"
        )
    return digest.hexdigest(), observed_size


def sanitize_pdf_observation(observation: Mapping[str, object]) -> dict[str, object]:
    """Keep only factual, source-safe PDF inspection fields."""

    page_count = observation.get("page_count")
    if isinstance(page_count, bool) or not isinstance(page_count, int) or page_count < 1:
        raise RetainedPdfInspectionError("PDF observation page_count must be positive")

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
    sanitized = {key: observation[key] for key in allowed if key in observation}
    try:
        json.dumps(sanitized, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise RetainedPdfInspectionError(
            "PDF observation contains non-serializable factual metadata"
        ) from exc
    return sanitized


def observe_pdf_with_pymupdf(source: Path) -> dict[str, object]:
    """Inspect factual PDF metadata with the optional generic PDF dependency."""

    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RetainedPdfInspectionError(
            "PyMuPDF is required for PDF inspection; install building-code-ast[pdf-inspection]"
        ) from exc

    try:
        document = fitz.open(source)
    except Exception as exc:  # pragma: no cover - delegated parser boundary
        raise RetainedPdfInspectionError("retained source could not be opened as PDF") from exc

    try:
        page_count = int(document.page_count)
        metadata = document.metadata or {}
        format_text = str(metadata.get("format") or "").strip()
        pdf_version = format_text.removeprefix("PDF ").strip() if format_text else "unknown"
        encrypted = bool(getattr(document, "is_encrypted", False))
        needs_password = bool(getattr(document, "needs_pass", False))
        permissions_raw = int(getattr(document, "permissions", 0))
        if needs_password:
            raise RetainedPdfInspectionError(
                "retained PDF requires a password before physical inspection"
            )

        page_label_rules: list[dict[str, object]] = []
        try:
            raw_labels = document.get_page_labels() or []
        except Exception:
            raw_labels = []
        for rule in raw_labels:
            if not isinstance(rule, Mapping):
                continue
            page_label_rules.append(
                {
                    "pdf_page_start": int(rule.get("startpage", 0)) + 1,
                    "style": str(rule.get("style", "")),
                    "prefix": str(rule.get("prefix", "")),
                    "first_page_number": int(rule.get("firstpagenum", 1)),
                }
            )

        try:
            toc = document.get_toc(simple=False) or []
        except Exception:
            toc = []
        outline_depths: list[int] = []
        valid_target_count = 0
        invalid_target_count = 0
        for entry in toc:
            if not isinstance(entry, Sequence) or len(entry) < 3:
                invalid_target_count += 1
                continue
            try:
                depth = int(entry[0])
                target_page = int(entry[2])
            except (TypeError, ValueError):
                invalid_target_count += 1
                continue
            outline_depths.append(depth)
            if 1 <= target_page <= page_count:
                valid_target_count += 1
            else:
                invalid_target_count += 1

        pages_with_text = 0
        pages_without_text: list[int] = []
        page_sizes: Counter[tuple[float, float]] = Counter()
        for page_index in range(page_count):
            page = document.load_page(page_index)
            if page.get_text("words"):
                pages_with_text += 1
            else:
                pages_without_text.append(page_index + 1)
            page_sizes[
                (round(float(page.rect.width), 3), round(float(page.rect.height), 3))
            ] += 1

        distinct_page_sizes = [
            {
                "width_points": width,
                "height_points": height,
                "page_count": count,
            }
            for (width, height), count in sorted(page_sizes.items())
        ]

        return {
            "page_count": page_count,
            "pdf_version": pdf_version,
            "encrypted": encrypted,
            "needs_password": needs_password,
            "permissions_raw": permissions_raw,
            "page_label_rules": page_label_rules,
            "outline": {
                "entry_count": len(toc),
                "max_depth": max(outline_depths, default=0),
                "valid_target_count": valid_target_count,
                "invalid_target_count": invalid_target_count,
            },
            "text_layer": {
                "pages_with_text": pages_with_text,
                "pages_without_text": pages_without_text,
            },
            "page_geometry": {"distinct_page_sizes": distinct_page_sizes},
            "tool": {
                "name": "PyMuPDF",
                "version": str(getattr(fitz, "VersionBind", "unknown")),
            },
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
    return {"size_bytes": observed_size, "sha256": digest, "pdf": pdf}
