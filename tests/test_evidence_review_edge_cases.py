from __future__ import annotations

import hashlib
import unittest

from provenance_fixtures import bound_source

from building_code_ast.evidence import (
    PublicationState,
    BoundArtifact,
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    RightsStatus,
    run_evidence_adapter,
)
from building_code_ast.evidence.amendments import (
    AmendmentOperation,
    WashingtonWacHtmlAdapter,
)
from building_code_ast.evidence.errata import ErratumOperation, IccErrataPdfAdapter


BASE_STATE = PublicationState(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    published_on="2020-10-23",
)


def _source(
    content: bytes,
    *,
    role: EvidenceRole,
    media_type: str,
    correction_set: str | None = None,
    effective_on: str | None = None,
    jurisdiction: str | None = None,
) -> BoundArtifact:
    return bound_source(
        source_id=f"synthetic:{role.value}",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="Synthetic review source",
        issuing_body="Synthetic Issuing Body",
        evidence_role=role,
        publication=PublicationState(
            publication_family="Synthetic evidence",
            edition="2021",
            correction_set=correction_set,
            published_on="2023-11-15",
            effective_on=effective_on,
        ),
        retrieved_at="2026-08-02T10:30:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type=media_type,
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://example.invalid/evidence",
        jurisdiction=jurisdiction,
    )


class EvidenceReviewEdgeCaseTests(unittest.TestCase):
    def test_wac_body_citation_does_not_start_a_new_section(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0107</h3>
<h3>Section 107—Construction documents.</h3>
<p>107.2.9 Synthetic new subsection.</p>
<p>See WAC 51-50-0110 for synthetic coordination.</p>
<p>[Statutory Authority: synthetic history.]</p>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=BASE_STATE.publication_id,
            known_base_locators=frozenset({"107.2"}),
            effective_dates_by_wac={"51-50-0107": "2024-03-15"},
        )

        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].operation, AmendmentOperation.ADD)
        self.assertIn("See WAC 51-50-0110", result.records[0].replacement_text)
        self.assertEqual(result.diagnostics, ())

    def test_wac_missing_date_and_unmapped_reserved_section_fail_closed(self) -> None:
        html = """
<html><body>
<h3>PDF WAC 51-50-0107</h3>
<p>107.2.9 Synthetic new subsection.</p>
<h3>PDF WAC 51-50-0110</h3>
<h3>Reserved.</h3>
</body></html>
""".encode("utf-8")
        adapter = WashingtonWacHtmlAdapter(
            base_publication_state_id=BASE_STATE.publication_id,
            known_base_locators=frozenset({"107.2", "110"}),
            effective_dates_by_wac={"51-50-0110": "2024-03-15"},
        )

        result = run_evidence_adapter(
            adapter,
            _source(
                html,
                role=EvidenceRole.JURISDICTIONAL_LAW,
                media_type="text/html",
                jurisdiction="US-WA",
            ),
            html,
        )

        self.assertEqual(result.records, ())
        self.assertEqual(
            tuple(item.code for item in result.diagnostics),
            ("missing-amendment-effective-date", "unresolved-reserved-locator"),
        )
        self.assertEqual(len(result.unsupported_regions), 2)

    def test_errata_period_headers_do_not_contaminate_prior_records(self) -> None:
        pdf_bytes = b"synthetic errata bytes"
        pages = (
            """Page 14-4, Section 1404.3.1 now reads . . .
Synthetic first replacement.
Page 14-4. Section 1404.3.2 has been deleted
Page 14-4. Section 1404.3.2.1 has been renumbered and now reads . . .
Synthetic renumbered replacement.
""",
        )
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=BASE_STATE.publication_id,
            applies_to_printings=("first-printing",),
            page_text_extractor=lambda _: pages,
        )

        result = run_evidence_adapter(
            adapter,
            _source(
                pdf_bytes,
                role=EvidenceRole.OFFICIAL_CORRECTION,
                media_type="application/pdf",
                correction_set="second-printing-editorial",
            ),
            pdf_bytes,
        )

        self.assertEqual(len(result.records), 3)
        self.assertEqual(
            tuple(record.operation for record in result.records),
            (
                ErratumOperation.REPLACE,
                ErratumOperation.DELETE,
                ErratumOperation.REPLACE,
            ),
        )
        self.assertEqual(result.records[0].replacement_text, "Synthetic first replacement.")
        self.assertEqual(result.records[1].target_locator, "1404.3.2")
        self.assertEqual(result.records[2].target_locator, "1404.3.2.1")
        self.assertEqual(
            result.records[2].replacement_text,
            "Synthetic renumbered replacement.",
        )
        self.assertEqual(result.diagnostics, ())


if __name__ == "__main__":
    unittest.main()
