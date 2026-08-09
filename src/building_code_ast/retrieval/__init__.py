"""Local source-retrieval contracts.

Retrieval consumes source authority; it does not replace the source register.
"""

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
    "source_evidence_id",
]
