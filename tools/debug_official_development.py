from __future__ import annotations

from collections import Counter
from hashlib import sha256
from urllib.request import Request, urlopen

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    DevelopmentRecordKind,
    EvidenceRole,
    IccActionStage,
    IccCommitteeActionPdfAdapter,
    IccProposalMonographPdfAdapter,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    run_evidence_adapter,
)


URLS = {
    "proposal": "https://www.iccsafe.org/wp-content/uploads/IBC-General-2024.pdf",
    "action": "https://www.iccsafe.org/wp-content/uploads/GROUP-A-2024-REPORT-OF-THE-COMMITTEE-ACTION-HEARING-CAH-1.pdf",
}


def fetch(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "building-code-ast-validation/1.0"}), timeout=120) as response:
        return response.read()


def source(name: str, content: bytes) -> SourceRegisterEntry:
    digest = sha256(content).hexdigest()
    return SourceRegisterEntry(
        source_id=f"debug:{name}:{digest}",
        ast_source=AstSourceIdentity("icc:ibc", f"official:sha256:{digest}"),
        title=name,
        issuing_body="International Code Council",
        evidence_role=EvidenceRole.DEVELOPMENT_HISTORY,
        publication=PublicationIdentity(
            publication_family="ICC development",
            edition="2024",
            published_on="2024-03-01",
        ),
        retrieved_at="2026-08-02T17:55:00+00:00",
        sha256=digest,
        media_type="application/pdf",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url=URLS[name],
    )


def main() -> None:
    proposal_bytes = fetch(URLS["proposal"])
    action_bytes = fetch(URLS["action"])
    proposals = run_evidence_adapter(
        IccProposalMonographPdfAdapter(), source("proposal", proposal_bytes), proposal_bytes
    )
    mapping = {record.proposal_id: record.affected_locators for record in proposals.records}
    actions = run_evidence_adapter(
        IccCommitteeActionPdfAdapter(
            stage=IccActionStage(
                record_kind=DevelopmentRecordKind.COMMITTEE_ACTION,
                record_key_suffix="cah1",
                parent_key_suffix="proposal",
                sequence=2,
            ),
            affected_locators_by_proposal=mapping,
        ),
        source("action", action_bytes),
        action_bytes,
    )
    print(
        {
            "proposal_count": len(proposals.records),
            "proposal_ids": sorted(mapping)[:30],
            "proposal_diagnostics": dict(Counter(item.code for item in proposals.diagnostics)),
            "action_count": len(actions.records),
            "action_ids": sorted(record.proposal_id for record in actions.records)[:30],
            "action_diagnostics": dict(Counter(item.code for item in actions.diagnostics)),
        }
    )


if __name__ == "__main__":
    main()
