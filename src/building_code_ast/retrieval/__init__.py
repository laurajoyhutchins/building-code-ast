"""Local source-retrieval contracts.

Retrieval consumes source authority; it does not replace the source register.
"""

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
from .structural import annotate_structural_metadata

__all__ = [
    "SOURCE_EVIDENCE_IDENTITY_VERSION",
    "SOURCE_EVIDENCE_STORE_VERSION",
    "LexicalSearchMode",
    "LexicalSearchResult",
    "SourceArtifactIdentity",
    "SourceEvidence",
    "annotate_structural_metadata",
    "extract_layout_evidence",
    "read_evidence_store",
    "rebuild_evidence_store",
    "search_evidence_store",
    "source_evidence_id",
    "verify_source_artifact",
]
