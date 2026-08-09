"""Local source-retrieval contracts.

Retrieval consumes source authority; it does not replace the source register.
"""

from .context import (
    EvidenceContext,
    expand_evidence_context,
    get_evidence_by_id,
    get_page_evidence,
)
from .extraction import extract_layout_evidence, verify_source_artifact
from .model import (
    SOURCE_EVIDENCE_IDENTITY_VERSION,
    SourceArtifactIdentity,
    SourceEvidence,
    source_evidence_id,
)
from .search import LexicalSearchMode, LexicalSearchResult, search_evidence_store
from .store import (
    SOURCE_EVIDENCE_STORE_VERSION,
    read_evidence_store,
    rebuild_evidence_store,
)

__all__ = [
    "SOURCE_EVIDENCE_IDENTITY_VERSION",
    "SOURCE_EVIDENCE_STORE_VERSION",
    "EvidenceContext",
    "LexicalSearchMode",
    "LexicalSearchResult",
    "SourceArtifactIdentity",
    "SourceEvidence",
    "expand_evidence_context",
    "extract_layout_evidence",
    "get_evidence_by_id",
    "get_page_evidence",
    "read_evidence_store",
    "rebuild_evidence_store",
    "search_evidence_store",
    "source_evidence_id",
    "verify_source_artifact",
]
