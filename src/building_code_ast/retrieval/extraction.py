"""Deterministic extraction of retrieval evidence from positioned PDF layout.

This module deliberately performs no publication-specific classification and no
text normalization. It verifies exact source bytes separately, then projects the
existing positioned-PDF observations into the shared retrieval evidence model.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

from ..ingest.pdf_layout import PdfLayoutDocument
from .model import SourceArtifactIdentity, SourceEvidence


def verify_source_artifact(
    path: Path | str,
    artifact: SourceArtifactIdentity,
) -> None:
    """Fail closed unless ``path`` matches the exact retrieval artifact identity."""

    if not isinstance(artifact, SourceArtifactIdentity):
        raise ValueError("artifact must be a SourceArtifactIdentity")

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)

    observed_size = source.stat().st_size
    if observed_size != artifact.size:
        raise ValueError(
            f"source artifact size mismatch: expected {artifact.size}, got {observed_size}"
        )

    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    observed_sha256 = digest.hexdigest()
    if observed_sha256 != artifact.sha256:
        raise ValueError("source artifact SHA-256 does not match retrieval identity")


def extract_layout_evidence(
    layout: PdfLayoutDocument,
    *,
    artifact: SourceArtifactIdentity,
    extraction_method: str,
    printed_pages: Mapping[int, str] | None = None,
) -> tuple[SourceEvidence, ...]:
    """Project positioned PDF blocks into deterministic source evidence.

    Pages are emitted in ascending physical PDF-page order and blocks in their
    extractor-assigned ``block_number`` order. Discovery tuple ordering therefore
    does not affect the output. Raw block text and bounding boxes are preserved.
    """

    if not isinstance(layout, PdfLayoutDocument):
        raise ValueError("layout must be a PdfLayoutDocument")
    if not isinstance(artifact, SourceArtifactIdentity):
        raise ValueError("artifact must be a SourceArtifactIdentity")
    if not isinstance(extraction_method, str) or not extraction_method or extraction_method != extraction_method.strip():
        raise ValueError("extraction_method must be a non-empty trimmed string")
    if layout.page_count != artifact.page_count:
        raise ValueError(
            "layout page_count must match the exact source artifact page_count"
        )

    page_by_number = {}
    for page in layout.pages:
        if page.page_number in page_by_number:
            raise ValueError(f"duplicate page_number: {page.page_number}")
        page_by_number[page.page_number] = page

    expected_pages = set(range(1, artifact.page_count + 1))
    if set(page_by_number) != expected_pages:
        raise ValueError("layout page numbers must cover the exact source artifact page range")

    labels = {} if printed_pages is None else dict(printed_pages)
    for page_number, label in labels.items():
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number not in expected_pages:
            raise ValueError("printed page labels must reference valid PDF pages")
        if not isinstance(label, str) or not label or label != label.strip():
            raise ValueError("printed page labels must be non-empty trimmed strings")

    evidence: list[SourceEvidence] = []
    for page_number in sorted(page_by_number):
        page = page_by_number[page_number]
        block_by_number = {}
        for block in page.blocks:
            if block.page_number != page.page_number:
                raise ValueError("block page_number must match its containing PDF page")
            if block.block_number in block_by_number:
                raise ValueError(
                    f"duplicate block_number {block.block_number} on PDF page {page.page_number}"
                )
            block_by_number[block.block_number] = block

        for block_number in sorted(block_by_number):
            block = block_by_number[block_number]
            evidence.append(
                SourceEvidence.create(
                    artifact=artifact,
                    pdf_page=page.page_number,
                    block_index=block.block_number,
                    text=block.text,
                    bbox=block.bbox,
                    extraction_method=extraction_method,
                    printed_page=labels.get(page.page_number),
                )
            )

    return tuple(evidence)
