"""Optional materialization and verification for PDF enrichment derivatives."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from .model import (
    DescriptiveMetadataOperation,
    OutlineOperation,
    PageLabelsOperation,
    PdfEnrichmentPlan,
    PdfEnrichmentReceipt,
    PdfVerificationSummary,
    SearchableTextOperation,
)


_LABEL_STYLE = {
    "decimal": "D",
    "roman_lower": "r",
    "roman_upper": "R",
    "alpha_lower": "a",
    "alpha_upper": "A",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} does not exist") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} must be a regular file, not a symlink")


def _has_struct_tree(document: Any) -> bool:
    key_type, _ = document.xref_get_key(document.pdf_catalog(), "StructTreeRoot")
    return key_type not in {"null", ""}


def _pixmap_digest(page: Any, fitz: Any) -> str:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False, annots=True)
    return hashlib.sha256(pixmap.samples).hexdigest()


def _verify_source_identity(source: Path, plan: PdfEnrichmentPlan, fitz: Any) -> None:
    _regular_file(source, "source PDF")
    observed_size = source.stat().st_size
    if observed_size != plan.source.size:
        raise ValueError(f"source size mismatch: expected {plan.source.size}, observed {observed_size}")
    observed_sha = _sha256(source)
    if observed_sha != plan.source.sha256:
        raise ValueError(f"source sha256 mismatch: expected {plan.source.sha256}, observed {observed_sha}")
    with fitz.open(source) as document:
        if document.page_count != plan.source.page_count:
            raise ValueError("source page_count mismatch")
        if document.is_encrypted or document.needs_pass:
            raise ValueError("encrypted PDFs are not supported by PDF enrichment v1")
        if document.is_repaired:
            raise ValueError("repaired/malformed PDFs are not supported by PDF enrichment v1")
        if document.get_sigflags() not in {-1, 0}:
            raise ValueError("digitally signed PDFs are not supported by PDF enrichment v1")


def _validate_conflicts(document: Any, plan: PdfEnrichmentPlan) -> None:
    for operation in plan.operations:
        if isinstance(operation, SearchableTextOperation):
            for entry in operation.entries:
                if entry.page_number > document.page_count:
                    raise ValueError(f"searchable-text page {entry.page_number} is outside the document")
                if document[entry.page_number - 1].get_text("text").strip():
                    raise ValueError(f"page {entry.page_number} already contains usable text")
        elif isinstance(operation, OutlineOperation):
            if document.get_toc(simple=True):
                raise ValueError("existing outline conflicts with requested outline enrichment")
            for entry in operation.entries:
                if entry.page_number > document.page_count:
                    raise ValueError(f"outline destination page {entry.page_number} is outside the document")
        elif isinstance(operation, PageLabelsOperation):
            if document.get_page_labels():
                raise ValueError("existing page labels conflict with requested page-label enrichment")
            if any(item.start_page_number > document.page_count for item in operation.ranges):
                raise ValueError("page-label range starts outside the document")
        elif isinstance(operation, DescriptiveMetadataOperation):
            metadata = document.metadata
            for key, value in operation.values:
                existing = (metadata.get(key) or "").strip()
                if existing and existing != value:
                    raise ValueError(f"existing metadata field {key!r} conflicts with requested enrichment")


def _insert_hidden_text(page: Any, entry: Any, fitz: Any) -> None:
    rectangle = fitz.Rect(*entry.bbox)
    for fontsize in range(10, 0, -1):
        shape = page.new_shape()
        result = shape.insert_textbox(
            rectangle,
            entry.text,
            fontsize=fontsize,
            render_mode=3,
        )
        if result >= 0:
            shape.commit(overlay=True)
            return
    raise ValueError(f"searchable text does not fit requested bbox on page {entry.page_number}")


def _apply_operations(document: Any, plan: PdfEnrichmentPlan, fitz: Any) -> tuple[dict[str, Any], ...]:
    summaries: list[dict[str, Any]] = []
    for operation in plan.operations:
        if isinstance(operation, SearchableTextOperation):
            entries = []
            for entry in operation.entries:
                page = document[entry.page_number - 1]
                _insert_hidden_text(page, entry, fitz)
                entries.append(
                    {
                        "page_number": entry.page_number,
                        "text_sha256": hashlib.sha256(entry.text.encode("utf-8")).hexdigest(),
                        "text_origin": entry.text_origin.value,
                    }
                )
            summaries.append(
                {
                    "kind": operation.kind.value,
                    "evidence_origin": operation.evidence_origin.value,
                    "entries": entries,
                }
            )
        elif isinstance(operation, OutlineOperation):
            document.set_toc([[item.level, item.title, item.page_number] for item in operation.entries])
            summaries.append(
                {
                    "kind": operation.kind.value,
                    "evidence_origin": operation.evidence_origin.value,
                    "entries": [
                        {
                            "level": item.level,
                            "page_number": item.page_number,
                            "title_sha256": hashlib.sha256(item.title.encode("utf-8")).hexdigest(),
                        }
                        for item in operation.entries
                    ],
                }
            )
        elif isinstance(operation, PageLabelsOperation):
            labels = [
                {
                    "startpage": item.start_page_number - 1,
                    "prefix": item.prefix,
                    "style": _LABEL_STYLE[item.style],
                    "firstpagenum": item.first_page_number,
                }
                for item in operation.ranges
            ]
            document.set_page_labels(labels)
            summaries.append(
                {
                    "kind": operation.kind.value,
                    "evidence_origin": operation.evidence_origin.value,
                    "ranges": [item.to_dict() for item in operation.ranges],
                }
            )
        elif isinstance(operation, DescriptiveMetadataOperation):
            metadata = document.metadata
            for key, value in operation.values:
                metadata[key] = value
            document.set_metadata(metadata)
            summaries.append(
                {
                    "kind": operation.kind.value,
                    "evidence_origin": operation.evidence_origin.value,
                    "values": {
                        key: hashlib.sha256(value.encode("utf-8")).hexdigest()
                        for key, value in operation.values
                    },
                }
            )
    return tuple(summaries)


def _requested_text_pages(plan: PdfEnrichmentPlan) -> tuple[int, ...]:
    for operation in plan.operations:
        if isinstance(operation, SearchableTextOperation):
            return tuple(entry.page_number for entry in operation.entries)
    return ()


def _verify_derivative(source: Path, derivative: Path, plan: PdfEnrichmentPlan, fitz: Any) -> PdfVerificationSummary:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise RuntimeError("pypdf is required for independent PDF enrichment verification") from exc

    try:
        independent = PdfReader(str(derivative), strict=True)
        if len(independent.pages) != plan.source.page_count:
            raise ValueError("independent PDF parser observed page-count mismatch")
        for page_index, page in enumerate(independent.pages, start=1):
            if page.mediabox.width <= 0 or page.mediabox.height <= 0:
                raise ValueError(f"independent PDF parser observed invalid media box on page {page_index}")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("independent PDF structural validation failed") from exc

    target_pages = set(_requested_text_pages(plan))
    unchanged_native_pages: list[int] = []
    with fitz.open(source) as original, fitz.open(derivative) as enriched:
        if enriched.page_count != original.page_count:
            raise ValueError("derivative page count changed")
        source_tagged = _has_struct_tree(original)
        derivative_tagged = _has_struct_tree(enriched)
        if source_tagged and not derivative_tagged:
            raise ValueError("derivative lost source tagged structure")

        for index in range(original.page_count):
            source_page = original[index]
            derivative_page = enriched[index]
            source_rect = tuple(round(value, 6) for value in source_page.rect)
            derivative_rect = tuple(round(value, 6) for value in derivative_page.rect)
            if source_rect != derivative_rect:
                raise ValueError(f"page {index + 1} dimensions changed")
            if source_page.rotation != derivative_page.rotation:
                raise ValueError(f"page {index + 1} rotation changed")
            source_media = tuple(round(value, 6) for value in source_page.mediabox)
            derivative_media = tuple(round(value, 6) for value in derivative_page.mediabox)
            if source_media != derivative_media:
                raise ValueError(f"page {index + 1} MediaBox changed")
            source_crop = tuple(round(value, 6) for value in source_page.cropbox)
            derivative_crop = tuple(round(value, 6) for value in derivative_page.cropbox)
            if source_crop != derivative_crop:
                raise ValueError(f"page {index + 1} CropBox changed")
            if _pixmap_digest(source_page, fitz) != _pixmap_digest(derivative_page, fitz):
                raise ValueError(f"page {index + 1} visible rendering changed")

            page_number = index + 1
            source_text = source_page.get_text("text")
            derivative_text = derivative_page.get_text("text")
            if page_number in target_pages:
                if not derivative_text.strip():
                    raise ValueError(f"target page {page_number} did not gain searchable text")
            elif source_text.strip():
                if hashlib.sha256(source_text.encode("utf-8")).digest() != hashlib.sha256(derivative_text.encode("utf-8")).digest():
                    raise ValueError(f"native text changed on unselected page {page_number}")
                unchanged_native_pages.append(page_number)

        for operation in plan.operations:
            if isinstance(operation, OutlineOperation):
                observed = [(item[0], item[1], item[2]) for item in enriched.get_toc(simple=True)]
                expected = [(item.level, item.title, item.page_number) for item in operation.entries]
                if observed != expected:
                    raise ValueError("derivative outline does not match approved plan")
            elif isinstance(operation, PageLabelsOperation):
                observed = enriched.get_page_labels()
                expected = [
                    {
                        "startpage": item.start_page_number - 1,
                        "prefix": item.prefix,
                        "style": _LABEL_STYLE[item.style],
                        "firstpagenum": item.first_page_number,
                    }
                    for item in operation.ranges
                ]
                if observed != expected:
                    raise ValueError("derivative page labels do not match approved plan")
            elif isinstance(operation, DescriptiveMetadataOperation):
                for key, value in operation.values:
                    if enriched.metadata.get(key) != value:
                        raise ValueError(f"derivative metadata field {key!r} does not match approved plan")

    return PdfVerificationSummary(
        structural_valid=True,
        visual_pages_identical=True,
        tagged_structure_preserved=(not source_tagged) or derivative_tagged,
        independent_backend="pypdf",
        page_count=plan.source.page_count,
        searchable_text_target_pages=tuple(sorted(target_pages)),
        unchanged_native_text_pages=tuple(unchanged_native_pages),
    )


def enrich_pdf(source: str | os.PathLike[str], output: str | os.PathLike[str], plan: PdfEnrichmentPlan) -> PdfEnrichmentReceipt:
    """Materialize one additive enriched derivative and return a verified receipt.

    The source is never rewritten. Output is placed atomically only after the
    derivative passes independent structural and page-for-page visual checks.
    """

    if not isinstance(plan, PdfEnrichmentPlan):
        raise TypeError("plan must be a PdfEnrichmentPlan")
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - optional dependency boundary
        raise RuntimeError("PyMuPDF is required for PDF enrichment materialization") from exc

    source_path = Path(source)
    output_path = Path(output)
    if source_path.resolve(strict=False) == output_path.resolve(strict=False):
        raise ValueError("source and derivative output must be distinct paths")
    if output_path.exists() or output_path.is_symlink():
        raise ValueError("derivative output path must not already exist")

    _verify_source_identity(source_path, plan, fitz)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.parent.is_symlink():
        raise ValueError("derivative output parent must not be a symlink")

    fd, temporary_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".partial.pdf", dir=output_path.parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    temporary_path.unlink()

    summaries: tuple[dict[str, Any], ...]
    try:
        with fitz.open(source_path) as document:
            _validate_conflicts(document, plan)
            summaries = _apply_operations(document, plan, fitz)
            document.save(temporary_path, garbage=0, deflate=False, clean=False, incremental=False)

        verification = _verify_derivative(source_path, temporary_path, plan, fitz)
        derivative_sha = _sha256(temporary_path)
        derivative_size = temporary_path.stat().st_size
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    import pypdf

    return PdfEnrichmentReceipt(
        source=plan.source,
        derivative_sha256=derivative_sha,
        derivative_size=derivative_size,
        plan_sha256=plan.digest(),
        tools=(("PyMuPDF", fitz.VersionBind), ("pypdf", pypdf.__version__)),
        operations=summaries,
        verification=verification,
    )