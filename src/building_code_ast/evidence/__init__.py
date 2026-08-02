"""Public source-evidence contracts."""

from .adapters import (
    AdapterResult,
    EvidenceAdapter,
    EvidenceDiagnostic,
    SourceRegion,
    run_evidence_adapter,
)
from .io import source_register_from_dict
from .model import (
    ACCESS_SCOPE_VALUES,
    EVIDENCE_ROLE_VALUES,
    RIGHTS_STATUS_VALUES,
    SOURCE_REGISTER_VERSION,
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    publication_state_id,
)

__all__ = [
    "ACCESS_SCOPE_VALUES",
    "EVIDENCE_ROLE_VALUES",
    "RIGHTS_STATUS_VALUES",
    "SOURCE_REGISTER_VERSION",
    "AccessScope",
    "AdapterResult",
    "AstSourceIdentity",
    "EvidenceAdapter",
    "EvidenceDiagnostic",
    "EvidenceRole",
    "PublicationIdentity",
    "RightsStatus",
    "SourceRegion",
    "SourceRegister",
    "SourceRegisterEntry",
    "publication_state_id",
    "run_evidence_adapter",
    "source_register_from_dict",
]
