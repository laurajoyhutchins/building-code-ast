"""Adapters from existing ingestion source maps into ``source-text/v1``.

These adapters intentionally consume already-reconstructed textual observations.
They do not invoke PDF extraction and do not add publication semantics.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .document_model import DocumentAst, DocumentSourceArtifact
from .source_text import (
    SourceTextBundle,
    SourceTextDiagnostic,
    SourceTextFragment,
    SourceTextProvenance,
    make_source_text_bundle,
)


NEC_SOURCE_TEXT_PROJECTION_ID = "building-code-ast:nec-source-map-to-source-text"
IBC_SOURCE_TEXT_PROJECTION_ID = "building-code-ast:ibc-logical-blocks-to-source-text"
SOURCE_TEXT_PROJECTION_VERSION = "0.1.0"


def _text_sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _diagnostics(values: Iterable[Any]) -> tuple[SourceTextDiagnostic, ...]:
    output: list[SourceTextDiagnostic] = []
    for item in values:
        span = getattr(item, "span", None)
        severity = getattr(getattr(item, "severity", None), "value", None)
        output.append(
            SourceTextDiagnostic(
                code=str(getattr(item, "code")),
                severity=str(severity or "warning"),
                message=str(getattr(item, "message")),
                start=None if span is None else int(span.start),
                end=None if span is None else int(span.end),
            )
        )
    return tuple(output)


def source_text_from_nec_source_map(
    *,
    source_manifest: Any,
    canonical_text: str,
    source_map: Sequence[Any],
    document_ast: DocumentAst | None = None,
    diagnostics: Iterable[Any] = (),
) -> SourceTextBundle:
    """Lift NEC normalized text plus block source-map records into the generic IR."""

    artifact = DocumentSourceArtifact(
        artifact_id=str(source_manifest.artifact_id),
        edition_id=str(source_manifest.edition_id),
    )
    fragments = tuple(
        SourceTextFragment(
            start=int(entry.normalized_start),
            end=int(entry.normalized_end),
            text_sha256=_text_sha256(str(entry.normalized_text)),
            provenance=(
                SourceTextProvenance(
                    page_number=int(entry.page_number),
                    bbox=tuple(float(value) for value in entry.bbox),
                    observation_id=f"pdf-block:{int(entry.block_number)}",
                ),
            ),
        )
        for entry in source_map
    )
    return make_source_text_bundle(
        source_artifact=artifact,
        source_sha256=str(source_manifest.sha256),
        source_size=int(source_manifest.size_bytes),
        extractor_id=str(source_manifest.extractor_id),
        extractor_version=str(source_manifest.extractor_version),
        projection_id=NEC_SOURCE_TEXT_PROJECTION_ID,
        projection_version=SOURCE_TEXT_PROJECTION_VERSION,
        canonical_text=canonical_text,
        fragments=fragments,
        document_ast=document_ast,
        diagnostics=_diagnostics(diagnostics),
    )


def source_text_from_ibc_source_map(
    *,
    source_manifest: Any,
    canonical_text: str,
    source_map: Sequence[Any],
    document_ast: DocumentAst | None = None,
    diagnostics: Iterable[Any] = (),
) -> SourceTextBundle:
    """Lift IBC logical-block text and source fragments into the generic IR."""

    artifact = DocumentSourceArtifact(
        artifact_id=str(source_manifest.artifact_id),
        edition_id=str(source_manifest.edition_id),
    )
    fragments: list[SourceTextFragment] = []
    for entry in source_map:
        provenance = tuple(
            SourceTextProvenance(
                page_number=int(fragment.page_number),
                bbox=tuple(float(value) for value in fragment.bbox),
                observation_id=f"pdf-block:{int(fragment.block_number)}",
            )
            for fragment in entry.fragments
        )
        fragments.append(
            SourceTextFragment(
                start=int(entry.normalized_start),
                end=int(entry.normalized_end),
                text_sha256=_text_sha256(str(entry.normalized_text)),
                provenance=provenance,
            )
        )
    return make_source_text_bundle(
        source_artifact=artifact,
        source_sha256=str(source_manifest.sha256),
        source_size=int(source_manifest.size_bytes),
        extractor_id=str(source_manifest.extractor_id),
        extractor_version=str(source_manifest.extractor_version),
        projection_id=IBC_SOURCE_TEXT_PROJECTION_ID,
        projection_version=SOURCE_TEXT_PROJECTION_VERSION,
        canonical_text=canonical_text,
        fragments=tuple(fragments),
        document_ast=document_ast,
        diagnostics=_diagnostics(diagnostics),
    )
