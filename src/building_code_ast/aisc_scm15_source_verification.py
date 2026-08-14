from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .pdf_inspection import (
    PdfObserver,
    RetainedPdfInspectionError,
    inspect_retained_pdf,
)


PUBLICATION_KEY = "aisc-scm-15"
RETAINED_FILENAME = "scm-15.pdf"
EXPECTED_SIZE_BYTES = 221_820_282

# Compatibility name for existing AISC callers. The underlying failure is now
# publication-neutral retained-PDF inspection failure.
SourceVerificationError = RetainedPdfInspectionError


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


def inspect_source(
    source: Path | str,
    *,
    expected_size_bytes: int = EXPECTED_SIZE_BYTES,
    pdf_observer: PdfObserver | None = None,
    component_ranges: Sequence[ComponentRange] = (),
    verified_at_utc: str | None = None,
) -> dict[str, object]:
    """Wrap generic retained-PDF facts in the AISC publication receipt contract."""

    inspected = inspect_retained_pdf(
        Path(source),
        expected_size_bytes=expected_size_bytes,
        pdf_observer=pdf_observer,
    )
    pdf = inspected["pdf"]
    if not isinstance(pdf, Mapping):  # pragma: no cover - generic contract guard
        raise SourceVerificationError("generic PDF inspection returned invalid factual metadata")
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
            "size_bytes": inspected["size_bytes"],
            "sha256": inspected["sha256"],
        },
        "pdf": dict(pdf),
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
