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

__all__ = [
    "SOURCE_EVIDENCE_IDENTITY_VERSION",
    "SourceArtifactIdentity",
    "SourceEvidence",
    "extract_layout_evidence",
    "source_evidence_id",
    "verify_source_artifact",
]
