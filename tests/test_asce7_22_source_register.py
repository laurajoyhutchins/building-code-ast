from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast import DocumentSourceArtifact
from building_code_ast.evidence import source_register_from_dict
from building_code_ast.json_schema_validation import validate_instances


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "corpora/asce-7-22/asce-7-22-source-register.json"
SCHEMA_PATH = ROOT / "schemas/source-register.schema.json"
DIGEST = "522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0"
PUBLICATION_STATE_ID = (
    "publication:f83874da470a117b932998d3167b5b65099a60a2253452a43b55ca975ae840bf"
)


class Asce722SourceRegisterTests(unittest.TestCase):
    def test_register_binds_exact_retained_artifact_and_unresolved_publication_state(self) -> None:
        payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        register = source_register_from_dict(payload)

        self.assertEqual(len(register.entries), 1)
        entry = register.entries[0]
        self.assertEqual(entry.source_id, "source:asce:7:2022:pdf:522d341d")
        self.assertEqual(entry.ast_source.artifact_id, f"sha256:{DIGEST}")
        self.assertEqual(entry.ast_source.edition_id, "asce-7-22")
        self.assertEqual(entry.sha256, DIGEST)
        self.assertEqual(entry.media_type, "application/pdf")
        self.assertEqual(
            entry.title,
            "ASCE/SEI 7-22 Minimum Design Loads and Associated Criteria for Buildings and Other Structures",
        )
        self.assertEqual(entry.issuing_body, "American Society of Civil Engineers")
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
            "Minimum Design Loads and Associated Criteria for Buildings and Other Structures",
        )
        self.assertEqual(publication["edition"], "2022")
        self.assertIsNone(publication["printing"])
        self.assertIsNone(publication["digital_revision"])
        self.assertEqual(
            publication["addenda_set"],
            "unresolved:retained-artifact-does-not-identify-incorporated-addenda-set",
        )
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
