from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    DevelopmentLineage,
    DevelopmentRecordKind,
    EvidenceRole,
    IccActionStage,
    IccCommitteeActionPdfAdapter,
    IccErrataPdfAdapter,
    IccProposalMonographPdfAdapter,
    NormalizedWashingtonWacHtmlAdapter,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    WashingtonWacHtmlAdapter,
    publication_state_id,
    run_evidence_adapter,
)


USER_AGENT = (
    "building-code-ast-official-evidence-validation/1.0 "
    "(+https://github.com/laurajoyhutchins/building-code-ast)"
)
VALIDATED_AT = "2026-08-02T17:55:00+00:00"

SOURCES = {
    "icc_proposal_monograph": (
        "https://www.iccsafe.org/wp-content/uploads/IBC-General-2024.pdf"
    ),
    "icc_committee_action": (
        "https://www.iccsafe.org/wp-content/uploads/"
        "GROUP-A-2024-REPORT-OF-THE-COMMITTEE-ACTION-HEARING-CAH-1.pdf"
    ),
    "icc_errata": (
        "https://www.iccsafe.org/wp-content/uploads/errata_central/"
        "2020-ICC-500-Errata-10-12-23.pdf"
    ),
    "washington_wac_0403": (
        "https://app.leg.wa.gov/WAC/default.aspx?cite=51-50-0403"
    ),
}


def fetch(url: str) -> tuple[bytes, str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=120) as response:
        content = response.read()
        return content, response.headers.get_content_type()


def source_entry(
    *,
    name: str,
    content: bytes,
    media_type: str,
    role: EvidenceRole,
    publication_family: str,
    edition: str,
    published_on: str,
    source_url: str,
    jurisdiction: str | None = None,
    correction_set: str | None = None,
    rights_status: RightsStatus = RightsStatus.PUBLIC_OFFICIAL,
) -> SourceRegisterEntry:
    digest = sha256(content).hexdigest()
    return SourceRegisterEntry(
        source_id=f"validation:{name}:{digest}",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc" if jurisdiction is None else "wa:wac:51-50",
            edition_id=f"official:sha256:{digest}",
        ),
        title=f"Official evidence validation source: {name}",
        issuing_body=(
            "International Code Council"
            if jurisdiction is None
            else "Washington State Building Code Council"
        ),
        evidence_role=role,
        publication=PublicationIdentity(
            publication_family=publication_family,
            edition=edition,
            correction_set=correction_set,
            published_on=published_on,
        ),
        retrieved_at=VALIDATED_AT,
        sha256=digest,
        media_type=media_type,
        access_scope=AccessScope.PUBLIC,
        rights_status=rights_status,
        source_url=source_url,
        jurisdiction=jurisdiction,
    )


def projection_digest(records: tuple[object, ...]) -> str:
    payload = [record.to_dict() for record in records]  # type: ignore[attr-defined]
    payload.sort(key=lambda item: item.get("record_id", item.get("patch_id", "")))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def result_receipt(result: object) -> dict[str, object]:
    records = result.records  # type: ignore[attr-defined]
    diagnostics = result.diagnostics  # type: ignore[attr-defined]
    return {
        "adapter_id": result.adapter_id,  # type: ignore[attr-defined]
        "adapter_version": result.adapter_version,  # type: ignore[attr-defined]
        "record_count": len(records),
        "diagnostic_count": len(diagnostics),
        "diagnostic_codes": dict(sorted(Counter(item.code for item in diagnostics).items())),
        "unsupported_region_count": len(result.unsupported_regions),  # type: ignore[attr-defined]
        "projection_sha256": projection_digest(records),
    }


def pdf_pages(content: bytes) -> tuple[str, ...]:
    import fitz

    document = fitz.open(stream=content, filetype="pdf")
    try:
        return tuple(page.get_text("text") for page in document)
    finally:
        document.close()


def icc_500_errata_pages(content: bytes) -> tuple[str, ...]:
    normalized_pages: list[str] = []
    for page_number, page in enumerate(pdf_pages(content), start=1):
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        normalized: list[str] = []
        for index, line in enumerate(lines[:-1]):
            if not line.casefold().startswith("errata"):
                continue
            target = lines[index + 1].strip().rstrip(")")
            if not target.casefold().startswith("figure "):
                continue
            if "removed" not in line.casefold():
                continue
            normalized.append(f"Page {page_number}, {target}: is deleted.")
        normalized_pages.append("\n".join(normalized))
    return tuple(normalized_pages)


def normalized_wac_bytes(records: tuple[object, ...]) -> tuple[tuple[bytes, str], ...]:
    derivatives: list[tuple[bytes, str]] = []
    for record in records:
        html = (
            "<html><body><section>"
            f"<h3>WAC {escape(record.wac_citation)}</h3>"  # type: ignore[attr-defined]
            f"<p>Section {escape(record.locator)} is replaced.</p>"  # type: ignore[attr-defined]
            f"<p>{escape(record.replacement_text)}</p>"  # type: ignore[attr-defined]
            "</section></body></html>"
        ).encode("utf-8")
        derivatives.append((html, record.effective_from))  # type: ignore[attr-defined]
    return tuple(derivatives)


def validate() -> dict[str, object]:
    fetched: dict[str, bytes] = {}
    media_types: dict[str, str] = {}
    source_receipts: dict[str, dict[str, object]] = {}
    for name, url in SOURCES.items():
        content, media_type = fetch(url)
        fetched[name] = content
        media_types[name] = media_type
        source_receipts[name] = {
            "url": url,
            "media_type": media_type,
            "byte_count": len(content),
            "sha256": sha256(content).hexdigest(),
        }

    proposal_source = source_entry(
        name="icc-proposal-monograph",
        content=fetched["icc_proposal_monograph"],
        media_type=media_types["icc_proposal_monograph"],
        role=EvidenceRole.DEVELOPMENT_HISTORY,
        publication_family="2024 Group A proposed changes",
        edition="IBC General",
        published_on="2024-03-01",
        source_url=SOURCES["icc_proposal_monograph"],
    )
    proposal_adapter = IccProposalMonographPdfAdapter()
    proposal_first = run_evidence_adapter(
        proposal_adapter,
        proposal_source,
        fetched["icc_proposal_monograph"],
    )
    proposal_second = run_evidence_adapter(
        proposal_adapter,
        proposal_source,
        fetched["icc_proposal_monograph"],
    )
    proposal_locator_map = {
        record.proposal_id: record.affected_locators for record in proposal_first.records
    }
    if not proposal_locator_map:
        raise RuntimeError("official proposal monograph produced no bounded proposal records")

    action_source = source_entry(
        name="icc-committee-action",
        content=fetched["icc_committee_action"],
        media_type=media_types["icc_committee_action"],
        role=EvidenceRole.DEVELOPMENT_HISTORY,
        publication_family="2024 Group A committee action report",
        edition="CAH1",
        published_on="2024-05-01",
        source_url=SOURCES["icc_committee_action"],
    )
    action_adapter = IccCommitteeActionPdfAdapter(
        stage=IccActionStage(
            record_kind=DevelopmentRecordKind.COMMITTEE_ACTION,
            record_key_suffix="cah1",
            parent_key_suffix="proposal",
            sequence=2,
            action_date="2024-04-14",
        ),
        affected_locators_by_proposal=proposal_locator_map,
    )
    action_first = run_evidence_adapter(
        action_adapter,
        action_source,
        fetched["icc_committee_action"],
    )
    action_second = run_evidence_adapter(
        action_adapter,
        action_source,
        fetched["icc_committee_action"],
    )
    if not action_first.records:
        raise RuntimeError("official committee-action report produced no linked action records")
    lineage = DevelopmentLineage(proposal_first.records + action_first.records)

    base_state = PublicationIdentity(
        publication_family="ICC 500",
        edition="2020",
        printing="first-printing",
        published_on="2020-01-01",
    )
    errata_source = source_entry(
        name="icc-errata",
        content=fetched["icc_errata"],
        media_type=media_types["icc_errata"],
        role=EvidenceRole.OFFICIAL_CORRECTION,
        publication_family="ICC 500 errata",
        edition="2020",
        published_on="2023-10-01",
        source_url=SOURCES["icc_errata"],
        correction_set="posted-2023-10",
    )
    errata_adapter = IccErrataPdfAdapter(
        base_publication_state_id=publication_state_id(base_state),
        applies_to_printings=("first-printing",),
        page_text_extractor=icc_500_errata_pages,
    )
    errata_first = run_evidence_adapter(
        errata_adapter,
        errata_source,
        fetched["icc_errata"],
    )
    errata_second = run_evidence_adapter(
        errata_adapter,
        errata_source,
        fetched["icc_errata"],
    )
    if not errata_first.records:
        raise RuntimeError("official ICC errata produced no bounded records")

    ibc_state = PublicationIdentity(
        publication_family="IBC",
        edition="2021",
        printing="first-printing",
        published_on="2020-10-23",
    )
    wac_source = source_entry(
        name="washington-wac-0403",
        content=fetched["washington_wac_0403"],
        media_type=media_types["washington_wac_0403"],
        role=EvidenceRole.JURISDICTIONAL_LAW,
        publication_family="WAC 51-50",
        edition="2021 IBC adoption",
        published_on="2023-11-15",
        source_url=SOURCES["washington_wac_0403"],
        jurisdiction="US-WA",
    )
    direct_wac_adapter = WashingtonWacHtmlAdapter(
        base_publication_state_id=publication_state_id(ibc_state),
        known_base_locators=frozenset({"403.4.8.3", "403.5.4"}),
        effective_dates_by_locator={
            "403.4.8.3": "2024-03-16",
            "403.5.4": "2024-03-15",
        },
    )
    direct_wac_first = run_evidence_adapter(
        direct_wac_adapter,
        wac_source,
        fetched["washington_wac_0403"],
    )
    direct_wac_second = run_evidence_adapter(
        direct_wac_adapter,
        wac_source,
        fetched["washington_wac_0403"],
    )
    if {record.locator for record in direct_wac_first.records} != {
        "403.4.8.3",
        "403.5.4",
    }:
        raise RuntimeError("official WAC extraction did not preserve the two reviewed locators")
    dates = {record.locator: record.effective_from for record in direct_wac_first.records}
    if dates != {"403.4.8.3": "2024-03-16", "403.5.4": "2024-03-15"}:
        raise RuntimeError("official WAC locator-specific effective dates were not preserved")

    normalized_receipts: list[dict[str, object]] = []
    normalized_digests: list[str] = []
    for ordinal, (derivative, effective_from) in enumerate(
        normalized_wac_bytes(direct_wac_first.records), start=1
    ):
        derivative_source = source_entry(
            name=f"washington-wac-0403-normalized-{ordinal}",
            content=derivative,
            media_type="text/html",
            role=EvidenceRole.JURISDICTIONAL_LAW,
            publication_family="Project-normalized WAC evidence",
            edition="2021 IBC adoption",
            published_on="2026-08-02",
            source_url=SOURCES["washington_wac_0403"],
            jurisdiction="US-WA",
            rights_status=RightsStatus.PROJECT_AUTHORED,
        )
        normalized_adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(ibc_state),
            effective_from=effective_from,
            known_base_locators=frozenset({"403.4.8.3", "403.5.4"}),
        )
        normalized_first = run_evidence_adapter(
            normalized_adapter,
            derivative_source,
            derivative,
        )
        normalized_second = run_evidence_adapter(
            normalized_adapter,
            derivative_source,
            derivative,
        )
        first_receipt = result_receipt(normalized_first)
        first_receipt["repeat_run_match"] = (
            projection_digest(normalized_first.records)
            == projection_digest(normalized_second.records)
        )
        first_receipt["upstream_source_sha256"] = wac_source.sha256
        first_receipt["derivative_sha256"] = derivative_source.sha256
        normalized_receipts.append(first_receipt)
        normalized_digests.append(projection_digest(normalized_first.records))

    validations = {
        "icc_proposal_monograph": {
            **result_receipt(proposal_first),
            "repeat_run_match": (
                projection_digest(proposal_first.records)
                == projection_digest(proposal_second.records)
            ),
        },
        "icc_committee_action": {
            **result_receipt(action_first),
            "repeat_run_match": (
                projection_digest(action_first.records)
                == projection_digest(action_second.records)
            ),
        },
        "icc_development_lineage": {
            "proposal_count": len(proposal_first.records),
            "action_count": len(action_first.records),
            "proposal_ids_with_actions": len(
                {record.proposal_id for record in action_first.records}
            ),
            "lineage_projection_sha256": projection_digest(lineage.records),
        },
        "icc_errata": {
            **result_receipt(errata_first),
            "repeat_run_match": (
                projection_digest(errata_first.records)
                == projection_digest(errata_second.records)
            ),
        },
        "washington_wac_direct": {
            **result_receipt(direct_wac_first),
            "repeat_run_match": (
                projection_digest(direct_wac_first.records)
                == projection_digest(direct_wac_second.records)
            ),
            "effective_dates_by_locator": dates,
        },
        "washington_wac_normalized": {
            "derivative_count": len(normalized_receipts),
            "validations": normalized_receipts,
            "aggregate_projection_sha256": sha256(
                "".join(sorted(normalized_digests)).encode("ascii")
            ).hexdigest(),
        },
    }

    repeat_flags = [
        validation["repeat_run_match"]
        for validation in validations.values()
        if isinstance(validation, dict) and "repeat_run_match" in validation
    ]
    repeat_flags.extend(
        item["repeat_run_match"] for item in normalized_receipts
    )
    if not all(repeat_flags):
        raise RuntimeError("official evidence validation was not deterministic")

    return {
        "schema_version": "0.1.0",
        "validated_at": VALIDATED_AT,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_text_included": False,
        "sources": source_receipts,
        "validations": validations,
        "all_repeat_runs_match": True,
    }


def main() -> None:
    receipt = validate()
    output = Path("official-evidence-validation.json")
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
