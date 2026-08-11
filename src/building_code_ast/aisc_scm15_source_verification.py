from __future__ import annotations

import argparse
import hashlib
import json
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence


PUBLICATION_KEY = "aisc-scm-15"
RETAINED_FILENAME = "scm-15.pdf"
EXPECTED_SIZE_BYTES = 221_820_282


class SourceVerificationError(ValueError):
    """Raised when exact-source verification cannot establish its contract."""


@dataclass(frozen=True, slots=True)
class ComponentRange:
    component_id: str
    first_pdf_page: int
    last_pdf_page: int

    def __post_init__(self) -> None:
        if not self.component_id.strip():
            raise SourceVerificationError("component id must not be empty")
        if self.first_pdf_page < 1 or self.last_pdf_page < 1:
            raise SourceVerificationError("component PDF pages must be positive")
        if self.first_pdf_page > self.last_pdf_page:
            raise SourceVerificationError(
                "component first PDF page must not exceed last PDF page"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "first_pdf_page": self.first_pdf_page,
            "last_pdf_page": self.last_pdf_page,
        }


def parse_component_range(value: str) -> ComponentRange:
    component_id, separator, page_span = value.partition("=")
    if not separator or not component_id.strip():
        raise SourceVerificationError(
            "component range must use ID=FIRST-LAST with a non-empty ID"
        )
    first_text, page_separator, last_text = page_span.partition("-")
    if not page_separator or not first_text or not last_text:
        raise SourceVerificationError(
            "component range must use ID=FIRST-LAST with integer PDF pages"
        )
    try:
        first_page = int(first_text)
        last_page = int(last_text)
    except ValueError as exc:
        raise SourceVerificationError(
            "component range PDF pages must be integers"
        ) from exc
    return ComponentRange(component_id.strip(), first_page, last_page)


def _verified_at_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _hash_regular_file(source: Path, *, expected_size_bytes: int) -> tuple[int, str]:
    try:
        initial = source.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise SourceVerificationError("retained source file does not exist") from exc

    if stat.S_ISLNK(initial.st_mode):
        raise SourceVerificationError("retained source path must not be a symlink")
    if not stat.S_ISREG(initial.st_mode):
        raise SourceVerificationError("retained source path must be a regular file")
    if initial.st_size != expected_size_bytes:
        raise SourceVerificationError(
            "retained source byte size does not match the expected artifact size: "
            f"expected {expected_size_bytes}, observed {initial.st_size}"
        )

    digest = hashlib.sha256()
    bytes_read = 0
    with source.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            bytes_read += len(chunk)

    final = source.stat(follow_symlinks=False)
    if (
        bytes_read != initial.st_size
        or final.st_size != initial.st_size
        or final.st_mtime_ns != initial.st_mtime_ns
    ):
        raise SourceVerificationError(
            "retained source changed while exact-byte verification was running"
        )
    return bytes_read, digest.hexdigest()


def _sanitize_pdf_observation(observation: Mapping[str, object]) -> dict[str, object]:
    page_count = observation.get("page_count")
    if isinstance(page_count, bool) or not isinstance(page_count, int) or page_count < 1:
        raise SourceVerificationError("PDF observation page_count must be positive")

    allowed_keys = (
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
    sanitized = {
        key: observation[key]
        for key in allowed_keys
        if key in observation
    }
    try:
        json.dumps(sanitized, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise SourceVerificationError(
            "PDF observation contains non-serializable factual metadata"
        ) from exc
    return sanitized


def _observe_pdf_with_pymupdf(source: Path) -> dict[str, object]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SourceVerificationError(
            "PyMuPDF is required for PDF inspection; install the evidence-pdf extra"
        ) from exc

    try:
        document = fitz.open(source)
    except Exception as exc:
        raise SourceVerificationError("retained source could not be opened as PDF") from exc

    try:
        page_count = int(document.page_count)
        metadata = document.metadata or {}
        format_text = str(metadata.get("format") or "").strip()
        pdf_version = (
            format_text.removeprefix("PDF ").strip() if format_text else "unknown"
        )
        encrypted = bool(getattr(document, "is_encrypted", False))
        needs_password = bool(getattr(document, "needs_pass", False))
        permissions_raw = int(getattr(document, "permissions", 0))
        if needs_password:
            raise SourceVerificationError(
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
            "page_geometry": {
                "distinct_page_sizes": distinct_page_sizes,
            },
            "tool": {
                "name": "PyMuPDF",
                "version": str(getattr(fitz, "VersionBind", "unknown")),
            },
        }
    finally:
        document.close()


def inspect_source(
    source: Path | str,
    *,
    expected_size_bytes: int = EXPECTED_SIZE_BYTES,
    pdf_observer: Callable[[Path], Mapping[str, object]] | None = None,
    component_ranges: Sequence[ComponentRange] = (),
    verified_at_utc: str | None = None,
) -> dict[str, object]:
    source_path = Path(source)
    size_bytes, sha256 = _hash_regular_file(
        source_path,
        expected_size_bytes=expected_size_bytes,
    )
    observer = pdf_observer or _observe_pdf_with_pymupdf
    pdf = _sanitize_pdf_observation(observer(source_path))
    page_count = int(pdf["page_count"])

    seen_components: set[str] = set()
    normalized_ranges: list[ComponentRange] = []
    for component_range in component_ranges:
        if component_range.component_id in seen_components:
            raise SourceVerificationError(
                f"duplicate component range: {component_range.component_id}"
            )
        if component_range.last_pdf_page > page_count:
            raise SourceVerificationError(
                "component range exceeds observed PDF page count: "
                f"{component_range.component_id} ends at "
                f"{component_range.last_pdf_page}, page count is {page_count}"
            )
        seen_components.add(component_range.component_id)
        normalized_ranges.append(component_range)

    normalized_ranges.sort(
        key=lambda item: (
            item.first_pdf_page,
            item.last_pdf_page,
            item.component_id,
        )
    )

    return {
        "schema_version": 1,
        "publication_key": PUBLICATION_KEY,
        "verified_at_utc": verified_at_utc or _verified_at_now(),
        "artifact": {
            "filename": RETAINED_FILENAME,
            "size_bytes": size_bytes,
            "sha256": sha256,
        },
        "pdf": pdf,
        "component_ranges": [item.to_dict() for item in normalized_ranges],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the exact private AISC Steel Construction Manual 15th Edition "
            "scm-15.pdf and emit a source-safe factual receipt."
        )
    )
    parser.add_argument("source", type=Path, help="path to the private scm-15.pdf bytes")
    parser.add_argument(
        "--component-range",
        action="append",
        default=[],
        metavar="ID=FIRST-LAST",
        help=(
            "operator-verified one-based PDF range for a logical component; "
            "repeat for each verified component"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the JSON receipt to this path instead of stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        component_ranges = tuple(
            parse_component_range(value) for value in args.component_range
        )
        receipt = inspect_source(
            args.source,
            component_ranges=component_ranges,
        )
    except SourceVerificationError as exc:
        parser.error(str(exc))

    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
