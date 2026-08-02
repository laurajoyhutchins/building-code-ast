from __future__ import annotations

import hashlib
import unittest

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    WashingtonWacHtmlAdapter,
    publication_state_id,
    run_evidence_adapter,
)


BASE_STATE = PublicationIdentity(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    published_on="2020-10-23",
)


def _source(content: bytes) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id="wa:wac:51-50-0403:official-shaped",
        ast_source=AstSourceIdentity(
            artifact_id="wa:wac:51-50",
            edition_id="official-shaped:sha256:" + "a" * 64,
        ),
        title="Official-shaped WAC 51-50-0403",
        issuing_body="Washington State Building Code Council",
        evidence_role=EvidenceRole.JURISDICTIONAL_LAW,
        publication=PublicationIdentity(
            publication_family="WAC 51-50",
            edition="2021 IBC adoption",
            published_on="2023-11-15",
        ),
        retrieved_at="2026-08-02T12:00:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type="text/html",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://app.leg.wa.gov/WAC/default.aspx?cite=51-50-0403",
        jurisdiction="US-WA",
    )


class WashingtonOfficialHtmlTests(unittest.TestCase):
    def test_adapter_reads_leaf_spans_inside_official_section_page(self) -> None:
        html = """
<html><body>
<h1>WAC 51-50-0403</h1>
<div class="navigation"><span>403.5.4 navigation noise</span></div>
<div class="section-page">
  <div><span>403.4.8.3 Synthetic first replacement.</span></div>
  <div><span>403.5.4 Synthetic second replacement.</span></div>
  <div><span>[Statutory Authority: synthetic.]</span></div>
</div>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"403.4.8.3", "403.5.4"}),
            effective_dates_by_locator={
                "403.4.8.3": "2024-03-16",
                "403.5.4": "2024-03-15",
            },
        )
        result = run_evidence_adapter(adapter, _source(html), html)

        self.assertEqual(
            tuple(record.locator for record in result.records),
            ("403.4.8.3", "403.5.4"),
        )
        self.assertEqual(
            {record.locator: record.effective_from for record in result.records},
            {"403.4.8.3": "2024-03-16", "403.5.4": "2024-03-15"},
        )
        self.assertTrue(
            all("navigation noise" not in record.replacement_text for record in result.records)
        )
        self.assertEqual(result.diagnostics, ())

    def test_adapter_retains_old_heading_and_paragraph_fixture_shape(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0107</h3>
<p>107.2.9 Synthetic added section.</p>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            known_base_locators=frozenset({"107.2"}),
            effective_dates_by_wac={"51-50-0107": "2024-03-15"},
        )
        result = run_evidence_adapter(adapter, _source(html), html)

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].locator, "107.2.9")


if __name__ == "__main__":
    unittest.main()
