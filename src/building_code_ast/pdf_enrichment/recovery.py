"""Verified bridge from private recovery evidence into PDF enrichment text.

Recovery observations remain evidence. This adapter permits recovered expression
to enter a PDF enrichment plan only when the observation explicitly declares a
private retrievable payload, the supplied expression matches its durable digest,
and the region is an explicit PDF-point rectangle.
"""

from __future__ import annotations

from ..recovery_observation import (
    CoordinateSpace,
    RecoveryObservation,
    RecoverySourceKind,
)
from .model import SearchableTextEntry, TextOrigin


def searchable_text_entry_from_recovery(
    observation: RecoveryObservation,
    recovered_text: str,
) -> SearchableTextEntry:
    """Create one enrichment text entry from a verified private recovery payload."""

    observation.verify_private_payload(recovered_text)
    if observation.region.coordinate_space is not CoordinateSpace.PDF_POINTS:
        raise ValueError("PDF enrichment requires recovery coordinates in PDF points")
    if observation.region.bbox is None:
        raise ValueError("PDF enrichment requires an explicit recovery-region bbox")

    if observation.source_kind is RecoverySourceKind.OCR_RECOVERY:
        origin = TextOrigin.OCR
    elif observation.source_kind is RecoverySourceKind.RASTER_RECOVERY:
        origin = TextOrigin.RASTER_RECOVERY
    else:  # pragma: no cover - closed enum guard
        raise ValueError("unsupported recovery source kind for PDF enrichment")

    return SearchableTextEntry(
        page_number=observation.region.page_number,
        text=recovered_text,
        bbox=observation.region.bbox,
        text_origin=origin,
    )
