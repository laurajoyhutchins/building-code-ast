from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegisterEntry,
    publication_state_id,
    run_evidence_adapter,
)
from building_code_ast.evidence.amendments import (
    AMENDMENT_OPERATION_VALUES,
    AMENDMENT_PATCH_VERSION,
    AmendmentOperation,
    AmendmentSet,
    JurisdictionalAmendmentPatch,
    NormalizedWashingtonWacHtmlAdapter,
    amendment_patch_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
HTML_BYTES = b"<html>synthetic Washington WAC amendments</html>"
BASE_STATE = PublicationIdentity(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    digital_revision=None,
    correction_set=None,
    published_on="2020-10-23",
    effective_on=None,
)


def _source(content: bytes = HTML_BYTES) -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id="wa:wac:51-50:2021-ibc-amendments",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="Synthetic chapter 51-50 WAC amendments",
        issuing_body="Washington State Building Code Council",
        evidence_role=EvidenceRole.JURISDICTIONAL_LAW,
        publication=PublicationIdentity(
            publication_family="WAC 51-50",
            edition="2021 IBC adoption",
            printing=None,
            digital_revision="synthetic",
            correction_set=None,
            published_on="2023-09-15",
            effective_on="2024-03-15",
        ),
        retrieved_at="2026-08-02T10:30:00-06:00",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type="text/html",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://app.leg.wa.gov/wac/default.aspx?cite=51-50&full=true",
        jurisdiction="US-WA",
        rights_note=None,
    )


def _patch(
    *,
    wac_citation: str = "51-50-0107",
    locator: str = "107.3",
    operation: AmendmentOperation = AmendmentOperation.ADD,
    effective_from: str = "2024-03-15",
    effective_to: str | None = None,
    replacement_text: str | None = "Synthetic added section text.",
    scope: str | None = None,
    sequence: int = 1,
) -> JurisdictionalAmendmentPatch:
    return JurisdictionalAmendmentPatch(
        source_id="wa:wac:51-50:2021-ibc-amendments",
        jurisdiction="US-WA",
        authority="Washington State Building Code Council",
        base_publication_state_id=publication_state_id(BASE_STATE),
        wac_citation=wac_citation,
        locator=locator,
        operation=operation,
        effective_from=effective_from,
        effective_to=effective_to,
        replacement_text=replacement_text,
        scope=scope,
        sequence=sequence,
        source_anchor=f"wac:{wac_citation}",
    )


class WashingtonAmendmentTests(unittest.TestCase):
    def test_patch_round_trips_with_deterministic_identity(self) -> None:
        patch = _patch()
        payload = patch.to_dict()
        restored = amendment_patch_from_dict(payload)

        self.assertEqual(restored, patch)
        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(payload["patch_version"], AMENDMENT_PATCH_VERSION)
        self.assertRegex(payload["patch_id"], r"^amendment:[0-9a-f]{64}$")

    def test_patch_identity_changes_with_operation_effective_date_and_scope(self) -> None:
        first = _patch()
        replaced = _patch(operation=AmendmentOperation.REPLACE)
        later = _patch(effective_from="2025-01-01")
        scoped = _patch(scope="Only for synthetic occupancies.")

        self.assertNotEqual(first.patch_id, replaced.patch_id)
        self.assertNotEqual(first.patch_id, later.patch_id)
        self.assertNotEqual(first.patch_id, scoped.patch_id)

    def test_strict_deserialization_and_schema_alignment(self) -> None:
        payload = _patch().to_dict()
        before = copy.deepcopy(payload)
        amendment_patch_from_dict(payload)
        self.assertEqual(payload, before)

        payload["invented"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            amendment_patch_from_dict(payload)

        payload = _patch().to_dict()
        payload["patch_id"] = "amendment:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "patch_id"):
            amendment_patch_from_dict(payload)

        schema = json.loads(
            (ROOT / "schemas/jurisdictional-amendment-patch.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["patch_version"]["const"], AMENDMENT_PATCH_VERSION)
        self.assertEqual(
            set(schema["properties"]["operation"]["enum"]), AMENDMENT_OPERATION_VALUES
        )

    def test_patch_active_interval_is_half_open(self) -> None:
        patch = _patch(effective_to="2025-01-01")

        self.assertFalse(patch.is_active_on("2024-03-14"))
        self.assertTrue(patch.is_active_on("2024-03-15"))
        self.assertTrue(patch.is_active_on("2024-12-31"))
        self.assertFalse(patch.is_active_on("2025-01-01"))

    def test_operation_payload_requirements_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "replacement_text"):
            _patch(replacement_text=None)
        with self.assertRaisesRegex(ValueError, "must be null"):
            _patch(operation=AmendmentOperation.DELETE, replacement_text="not allowed")
        with self.assertRaisesRegex(ValueError, "scope"):
            _patch(
                operation=AmendmentOperation.SCOPE,
                replacement_text=None,
                scope=None,
            )

    def test_amendment_set_orders_patches_and_rejects_base_mismatch(self) -> None:
        later = _patch(effective_from="2025-01-01", sequence=2)
        earlier = _patch(effective_from="2024-03-15", sequence=1)
        amendment_set = AmendmentSet(patches=(later, earlier))

        self.assertEqual(amendment_set.ordered(), (earlier, later))

        other = JurisdictionalAmendmentPatch(
            **{
                **earlier.constructor_dict(),
                "base_publication_state_id": "publication:" + "0" * 64,
                "sequence": 3,
            }
        )
        with self.assertRaisesRegex(ValueError, "base publication state"):
            AmendmentSet(patches=(earlier, other))

    def test_amendment_set_rejects_overlapping_conflicts_but_allows_revisions(self) -> None:
        first = _patch(effective_to="2025-01-01", sequence=1)
        overlapping = _patch(
            operation=AmendmentOperation.REPLACE,
            effective_from="2024-06-01",
            effective_to=None,
            replacement_text="Conflicting synthetic text.",
            sequence=2,
        )
        with self.assertRaisesRegex(ValueError, "overlapping amendment conflict"):
            AmendmentSet(patches=(first, overlapping))

        revision = _patch(
            operation=AmendmentOperation.REPLACE,
            effective_from="2025-01-01",
            effective_to=None,
            replacement_text="Later synthetic text.",
            sequence=2,
        )
        amendment_set = AmendmentSet(patches=(first, revision))
        self.assertEqual(amendment_set.active_for("107.3", "2025-02-01"), (revision,))

    def test_adapter_extracts_add_replace_delete_reserve_and_scope(self) -> None:
        html = """
<html><body>
<section><h3>WAC 51-50-0107</h3><p>Section 107.3 is added.</p><p>Synthetic added section text.</p></section>
<section><h3>WAC 51-50-0403</h3><p>Section 403 is replaced.</p><p>Synthetic replacement text.</p></section>
<section><h3>WAC 51-50-0110</h3><p>Section 110 is deleted.</p></section>
<section><h3>WAC 51-50-0312</h3><p>Section 312 is reserved.</p></section>
<section><h3>WAC 51-50-0007</h3><p>Section 101.4.7 applies only as follows.</p><p>Only to synthetic existing buildings.</p></section>
</body></html>
"""
        content = html.encode("utf-8")
        adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            effective_from="2024-03-15",
            known_base_locators=frozenset({"107.3", "403", "110", "312", "101.4.7"}),
        )
        result = run_evidence_adapter(adapter, _source(content), content)

        self.assertEqual(
            tuple(record.operation for record in result.records),
            (
                AmendmentOperation.ADD,
                AmendmentOperation.REPLACE,
                AmendmentOperation.DELETE,
                AmendmentOperation.RESERVE,
                AmendmentOperation.SCOPE,
            ),
        )
        self.assertEqual(result.records[0].replacement_text, "Synthetic added section text.")
        self.assertIsNone(result.records[2].replacement_text)
        self.assertEqual(result.records[4].scope, "Only to synthetic existing buildings.")
        self.assertEqual(result.diagnostics, ())
        AmendmentSet(patches=result.records)

    def test_adapter_retains_unknown_directives_and_unresolved_locators(self) -> None:
        html = """
<html><body>
<section><h3>WAC 51-50-0999</h3><p>Section 999 is clarified.</p><p>Synthetic ambiguous wording.</p></section>
<section><h3>WAC 51-50-0888</h3><p>Section 888 is replaced.</p><p>Synthetic replacement text.</p></section>
</body></html>
"""
        content = html.encode("utf-8")
        adapter = NormalizedWashingtonWacHtmlAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            effective_from="2024-03-15",
            known_base_locators=frozenset({"107.3"}),
        )
        result = run_evidence_adapter(adapter, _source(content), content)

        self.assertEqual(result.records, ())
        self.assertEqual(
            tuple(diagnostic.code for diagnostic in result.diagnostics),
            ("unsupported-amendment-directive", "unresolved-base-locator"),
        )
        self.assertEqual(len(result.unsupported_regions), 2)


if __name__ == "__main__":
    unittest.main()
