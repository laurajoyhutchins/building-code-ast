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
from building_code_ast.evidence.errata import (
    ERRATA_RECORD_VERSION,
    ERRATUM_OPERATION_VALUES,
    TARGET_KIND_VALUES,
    ErratumOperation,
    ErratumRecord,
    IccErrataPdfAdapter,
    TargetKind,
    erratum_record_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
PDF_BYTES = b"synthetic ICC errata PDF bytes"
BASE_STATE = PublicationIdentity(
    publication_family="IBC",
    edition="2021",
    printing="first-printing",
    digital_revision=None,
    correction_set=None,
    published_on="2020-10-23",
    effective_on=None,
)


def _source(*, correction_set: str | None = "second-printing-editorial") -> SourceRegisterEntry:
    return SourceRegisterEntry(
        source_id="icc:ibc:2021:errata:second-printing",
        ast_source=AstSourceIdentity(
            artifact_id="icc:ibc",
            edition_id="2021:pdf:sha256:" + "a" * 64,
        ),
        title="2021 IBC editorial changes second printing",
        issuing_body="International Code Council",
        evidence_role=EvidenceRole.OFFICIAL_CORRECTION,
        publication=PublicationIdentity(
            publication_family="IBC",
            edition="2021",
            printing="second-printing",
            digital_revision=None,
            correction_set=correction_set,
            published_on="2021-01-01",
            effective_on=None,
        ),
        retrieved_at="2026-08-02T09:00:00-06:00",
        sha256=hashlib.sha256(PDF_BYTES).hexdigest(),
        media_type="application/pdf",
        access_scope=AccessScope.PUBLIC,
        rights_status=RightsStatus.PUBLIC_OFFICIAL,
        source_url="https://codes.iccsafe.org/content/IBC2021P2/editorial-changes-second-printing",
        jurisdiction=None,
        rights_note=None,
    )


def _record() -> ErratumRecord:
    return ErratumRecord(
        source_id="icc:ibc:2021:errata:second-printing",
        sequence=1,
        base_publication_state_id=publication_state_id(BASE_STATE),
        correction_set="second-printing-editorial",
        applies_to_printings=("first-printing",),
        target_kind=TargetKind.SECTION,
        target_locator="[F] 3313.5",
        target_page_label="33-5",
        operation=ErratumOperation.REPLACE,
        instruction="line 4 now reads",
        replacement_text="Synthetic corrected line.",
        source_page=2,
        source_anchor="errata:1",
    )


class IccErrataTests(unittest.TestCase):
    def test_record_round_trips_with_deterministic_identity(self) -> None:
        record = _record()
        payload = record.to_dict()
        restored = erratum_record_from_dict(payload)

        self.assertEqual(restored, record)
        self.assertEqual(restored.to_dict(), payload)
        self.assertEqual(payload["record_version"], ERRATA_RECORD_VERSION)
        self.assertRegex(payload["record_id"], r"^erratum:[0-9a-f]{64}$")
        self.assertEqual(payload["base_publication_state_id"], publication_state_id(BASE_STATE))

    def test_record_identity_is_printing_and_content_sensitive(self) -> None:
        record = _record()
        other_printing = ErratumRecord(
            **{
                **record.constructor_dict(),
                "applies_to_printings": ("first-printing", "second-printing"),
            }
        )
        other_text = ErratumRecord(
            **{
                **record.constructor_dict(),
                "replacement_text": "Different corrected line.",
            }
        )

        self.assertNotEqual(record.record_id, other_printing.record_id)
        self.assertNotEqual(record.record_id, other_text.record_id)

    def test_strict_deserialization_rejects_unknown_fields_and_bad_identity(self) -> None:
        payload = _record().to_dict()
        payload["invented"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            erratum_record_from_dict(payload)

        payload = _record().to_dict()
        payload["record_id"] = "erratum:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "record_id"):
            erratum_record_from_dict(payload)

    def test_deserialization_does_not_mutate_input(self) -> None:
        payload = _record().to_dict()
        before = copy.deepcopy(payload)
        erratum_record_from_dict(payload)
        self.assertEqual(payload, before)

    def test_schema_matches_runtime_enums(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/icc-errata-record.schema.json").read_text(encoding="utf-8")
        )
        properties = schema["properties"]
        self.assertEqual(properties["record_version"]["const"], ERRATA_RECORD_VERSION)
        self.assertEqual(set(properties["operation"]["enum"]), ERRATUM_OPERATION_VALUES)
        self.assertEqual(set(properties["target_kind"]["enum"]), TARGET_KIND_VALUES)

    def test_adapter_extracts_bounded_entries_and_preserves_source_regions(self) -> None:
        pages = (
            """EDITORIAL CHANGES – SECOND PRINTING
Page 2-9, definition [BS] DIAPHRAGM: sub-definitions have been added and now read . . .
Synthetic inserted definition text.

Page 33-5, Section [F] 3313.5: line 4 now reads . . .
Synthetic corrected line.
""",
            """Page 35-1, Referenced Standard AAMA 714—20 now reads . . .
714—19: Synthetic referenced-standard entry.
""",
        )
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            applies_to_printings=("first-printing",),
            page_text_extractor=lambda _: pages,
        )

        result = run_evidence_adapter(adapter, _source(), PDF_BYTES)

        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.records[0].operation, ErratumOperation.INSERT)
        self.assertEqual(result.records[0].target_kind, TargetKind.DEFINITION)
        self.assertEqual(result.records[0].target_page_label, "2-9")
        self.assertEqual(result.records[0].source_page, 1)
        self.assertEqual(result.records[1].target_locator, "[F] 3313.5")
        self.assertEqual(result.records[2].target_kind, TargetKind.REFERENCED_STANDARD)
        self.assertEqual(result.records[2].source_page, 2)
        self.assertEqual(result.diagnostics, ())
        self.assertEqual(result.unsupported_regions, ())

    def test_adapter_retains_unrecognized_entries_as_diagnostics(self) -> None:
        pages = (
            """Page APPENDIX H-4, Section H116.1: wording adjusted for publication consistency.
Synthetic ambiguous correction text.
""",
        )
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            applies_to_printings=("first-printing",),
            page_text_extractor=lambda _: pages,
        )

        result = run_evidence_adapter(adapter, _source(), PDF_BYTES)

        self.assertEqual(result.records, ())
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].code, "unsupported-erratum-directive")
        self.assertEqual(result.unsupported_regions[0].page, 1)

    def test_adapter_requires_correction_set_and_printing_scope(self) -> None:
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            applies_to_printings=("first-printing",),
            page_text_extractor=lambda _: (),
        )
        with self.assertRaisesRegex(ValueError, "correction_set"):
            run_evidence_adapter(adapter, _source(correction_set=None), PDF_BYTES)

        with self.assertRaisesRegex(ValueError, "applies_to_printings"):
            IccErrataPdfAdapter(
                base_publication_state_id=publication_state_id(BASE_STATE),
                applies_to_printings=(),
                page_text_extractor=lambda _: (),
            )

    def test_default_pdf_extractor_reports_optional_dependency(self) -> None:
        adapter = IccErrataPdfAdapter(
            base_publication_state_id=publication_state_id(BASE_STATE),
            applies_to_printings=("first-printing",),
        )
        try:
            result = run_evidence_adapter(adapter, _source(), PDF_BYTES)
        except RuntimeError as exc:
            self.assertIn("PyMuPDF", str(exc))
        else:
            self.assertIsInstance(result.records, tuple)


if __name__ == "__main__":
    unittest.main()
