"""Source-preserving PDF enrichment derivative contracts and runtime."""

from .model import (
    DescriptiveMetadataOperation,
    EvidenceOrigin,
    OperationKind,
    OutlineEntry,
    OutlineOperation,
    PageLabelRange,
    PageLabelsOperation,
    PdfEnrichmentPlan,
    PdfEnrichmentReceipt,
    PdfSourceIdentity,
    PdfVerificationSummary,
    SearchableTextEntry,
    SearchableTextOperation,
    TextOrigin,
    plan_from_dict,
)
from .recovery import searchable_text_entry_from_recovery
from .runtime import enrich_pdf

__all__ = [
    "DescriptiveMetadataOperation",
    "EvidenceOrigin",
    "OperationKind",
    "OutlineEntry",
    "OutlineOperation",
    "PageLabelRange",
    "PageLabelsOperation",
    "PdfEnrichmentPlan",
    "PdfEnrichmentReceipt",
    "PdfSourceIdentity",
    "PdfVerificationSummary",
    "SearchableTextEntry",
    "SearchableTextOperation",
    "TextOrigin",
    "enrich_pdf",
    "plan_from_dict",
    "searchable_text_entry_from_recovery",
]
