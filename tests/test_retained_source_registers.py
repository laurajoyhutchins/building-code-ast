from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast.evidence import (
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    source_register_from_dict,
)


ROOT = Path(__file__).resolve().parents[1]
RETRIEVED_AT = "2026-08-10T15:36:00+00:00"

EXPECTED = {
    "aci-318-19": {
        "path": "corpora/aci-318-19/aci-318-19-source-register.json",
        "sha256": "7b6b572e9e6532e0da1678080f63cb6b7a233f96caf2fc5a45350a056e18c53c",
        "roles": {"normative_text", "commentary"},
        "count": 2,
    },
    "ashrae-62.1-2016": {
        "path": "corpora/ashrae-62.1-2016/ashrae-62.1-2016-source-register.json",
        "sha256": "a751d154a734a6fb2f04ea2b6878d39a1878d270da49686d179e4e627808b759",
        "roles": {"normative_text"},
        "count": 1,
    },
    "ashrae-90.1-2016": {
        "path": "corpora/ashrae-90.1-2016/ashrae-90.1-2016-source-register.json",
        "sha256": "275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162",
        "roles": {"normative_text"},
        "count": 1,
    },
    "nec-2017": {
        "path": "corpora/nec-2017/nec-2017-source-register.json",
        "sha256": "603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7",
        "roles": {"normative_text"},
        "count": 1,
    },
    "nfpa-13-2019": {
        "path": "corpora/nfpa-13-2019/nfpa-13-2019-source-register.json",
        "sha256": "07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5",
        "roles": {"normative_text"},
        "count": 1,
    },
    "tms-402-602-16": {
        "path": "corpora/tms-402-602-16/tms-402-602-16-source-register.json",
        "sha256": "947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d",
        "roles": {"normative_text", "commentary"},
        "count": 4,
    },
}


class RetainedSourceRegisterTests(unittest.TestCase):
    def test_reader_round_trips_explicit_addenda_state(self) -> None:
        publication = PublicationIdentity(
            publication_family="Synthetic Standard",
            edition="2026",
            addenda_set="a,c",
            correction_set="unresolved",
        )
        entry = SourceRegisterEntry(
            source_id="source:synthetic:2026:pdf:" + "a" * 8,
            ast_source=AstSourceIdentity(
                artifact_id="sha256:" + "a" * 64,
                edition_id="synthetic-2026",
            ),
            title="Synthetic source",
            issuing_body="Synthetic Issuer",
            evidence_role=EvidenceRole.NORMATIVE_TEXT,
            publication=publication,
            retrieved_at=RETRIEVED_AT,
            sha256="a" * 64,
            media_type="application/pdf",
            access_scope=AccessScope.PRIVATE_LOCAL,
            rights_status=RightsStatus.UNCERTAIN_RESTRICTED,
            rights_note="Synthetic restricted fixture.",
        )
        rendered = SourceRegister(entries=(entry,)).to_dict()
        parsed = source_register_from_dict(rendered)
        self.assertEqual(parsed.entries[0].publication.addenda_set, "a,c")
        self.assertEqual(parsed.to_dict(), rendered)

    def test_exact_replayed_artifacts_have_durable_source_registers(self) -> None:
        for publication, expected in EXPECTED.items():
            with self.subTest(publication=publication):
                data = json.loads((ROOT / expected["path"]).read_text())
                register = source_register_from_dict(data)
                self.assertEqual(len(register.entries), expected["count"])
                self.assertEqual(
                    {entry.sha256 for entry in register.entries},
                    {expected["sha256"]},
                )
                self.assertEqual(
                    {entry.ast_source.artifact_id for entry in register.entries},
                    {"sha256:" + expected["sha256"]},
                )
                self.assertEqual(
                    {entry.evidence_role.value for entry in register.entries},
                    expected["roles"],
                )
                self.assertTrue(
                    all(entry.retrieved_at == RETRIEVED_AT for entry in register.entries)
                )
                self.assertTrue(all(entry.source_url is None for entry in register.entries))
                rendered = json.dumps(data, sort_keys=True)
                self.assertNotIn("drive.google.com", rendered)
                self.assertNotIn("object_id", rendered)
                self.assertNotIn("access_token", rendered)

    def test_multi_role_artifacts_preserve_distinct_source_identities(self) -> None:
        for publication in ("aci-318-19", "tms-402-602-16"):
            expected = EXPECTED[publication]
            data = json.loads((ROOT / expected["path"]).read_text())
            register = source_register_from_dict(data)
            self.assertEqual(
                len({entry.source_id for entry in register.entries}),
                expected["count"],
            )
            self.assertEqual(
                len({entry.ast_source.artifact_id for entry in register.entries}),
                1,
            )


if __name__ == "__main__":
    unittest.main()
