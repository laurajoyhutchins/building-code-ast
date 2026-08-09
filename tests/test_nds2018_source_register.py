from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast import DocumentSourceArtifact
from building_code_ast.evidence import source_register_from_dict
from building_code_ast.json_schema_validation import validate_instances


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "corpora/nds-2018/nds-2018-source-register.json"
SCHEMA_PATH = ROOT / "schemas/source-register.schema.json"
DIGEST = "581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4"
PUBLICATION_STATE_ID = (
    "publication:21a58c8ab0f4831b5ca3f443436078dd21d884da7ac9e071d34119902a95a5a4"
)


class Nds2018SourceRegisterTests(unittest.TestCase):
    def test_register_binds_exact_retained_artifact_and_unresolved_publication_state(self) -> None:
        payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        register = source_register_from_dict(payload)

        self.assertEqual(len(register.entries), 1)
        entry = register.entries[0]
        self.assertEqual(entry.source_id, "source:awc:nds:2018:pdf:581353da")
        self.assertEqual(entry.ast_source.artifact_id, "awc:nds")
        self.assertEqual(entry.ast_source.edition_id, f"2018:pdf:sha256:{DIGEST}")
        self.assertEqual(entry.sha256, DIGEST)
        self.assertEqual(entry.media_type, "application/pdf")
        self.assertEqual(entry.title, "2018 National Design Specification for Wood Construction")
        self.assertEqual(entry.issuing_body, "American Wood Council")
        self.assertEqual(entry.evidence_role.value, "normative_text")
        self.assertEqual(entry.access_scope.value, "licensed_local")
        self.assertEqual(entry.rights_status.value, "licensed")
        self.assertIsNone(entry.source_url)
        self.assertIsNone(entry.jurisdiction)
        self.assertIsNotNone(entry.rights_note)

        document_source = DocumentSourceArtifact(
            artifact_id=entry.ast_source.artifact_id,
            edition_id=entry.ast_source.edition_id,
        )
        self.assertEqual(document_source.to_dict(), entry.ast_source.to_dict())

        publication = entry.publication.to_dict()
        self.assertEqual(publication["state_id"], PUBLICATION_STATE_ID)
        self.assertEqual(
            publication["publication_family"],
            "National Design Specification for Wood Construction",
        )
        self.assertEqual(publication["edition"], "2018")
        self.assertIsNone(publication["printing"])
        self.assertEqual(publication["digital_revision"], "First Web Version, November 2017")
        self.assertEqual(
            publication["correction_set"],
            "unresolved:retained-artifact-does-not-identify-incorporated-correction-set",
        )
        self.assertIsNone(publication["published_on"])
        self.assertIsNone(publication["effective_on"])

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_instances([payload], schema), [])


if __name__ == "__main__":
    unittest.main()
