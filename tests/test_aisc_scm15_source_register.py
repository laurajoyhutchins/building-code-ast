from __future__ import annotations

import json
import unittest
from pathlib import Path

from building_code_ast.evidence import source_register_from_dict
from building_code_ast.evidence.source_objects import (
    source_object_catalog_from_dict,
    validate_source_object_catalog,
)
from building_code_ast.json_schema_validation import validate_instances


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "corpora/aisc-scm-15/aisc-scm-15-source-register.json"
CATALOG_PATH = ROOT / "corpora/source-object-catalog.json"
SCHEMA_PATH = ROOT / "schemas/source-register.schema.json"
DIGEST = "c5fbe648fd81a7ecda10df115393bbb9492924c8ce22167fc6d86c8b87fd8e7f"
PUBLICATION_STATE_ID = (
    "publication:8d437e9cada7c5a90893cd3bccbbae72dddfc090df1e8f01d8f040cf80a92584"
)


class AiscScm15SourceRegisterTests(unittest.TestCase):
    def test_register_binds_exact_verified_manual_compilation(self) -> None:
        payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        register = source_register_from_dict(payload)

        self.assertEqual(len(register.entries), 1)
        entry = register.entries[0]
        self.assertEqual(entry.source_id, "source:aisc:scm:15:pdf:c5fbe648")
        self.assertEqual(entry.ast_source.artifact_id, f"sha256:{DIGEST}")
        self.assertEqual(entry.ast_source.edition_id, "aisc-scm-15")
        self.assertEqual(entry.sha256, DIGEST)
        self.assertEqual(entry.media_type, "application/pdf")
        self.assertEqual(entry.title, "Steel Construction Manual")
        self.assertEqual(entry.issuing_body, "American Institute of Steel Construction")
        self.assertEqual(entry.evidence_role.value, "secondary_analysis")
        self.assertEqual(entry.access_scope.value, "licensed_local")
        self.assertEqual(entry.rights_status.value, "licensed")
        self.assertIsNone(entry.source_url)
        self.assertIsNone(entry.jurisdiction)
        self.assertIsNotNone(entry.rights_note)

        publication = entry.publication.to_dict()
        self.assertEqual(publication["state_id"], PUBLICATION_STATE_ID)
        self.assertEqual(publication["publication_family"], "Steel Construction Manual")
        self.assertEqual(publication["edition"], "Fifteenth Edition")
        self.assertEqual(publication["printing"], "Second Printing, June 2018")
        self.assertIsNone(publication["digital_revision"])
        self.assertIsNone(publication["correction_set"])
        self.assertIsNone(publication["published_on"])
        self.assertIsNone(publication["effective_on"])

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_instances([payload], schema), [])

    def test_catalog_maps_verified_manual_bytes_to_one_logical_object(self) -> None:
        register_payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        register = source_register_from_dict(register_payload)
        catalog_payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        catalog = source_object_catalog_from_dict(catalog_payload)

        matching = [
            entry
            for entry in catalog.entries
            if entry.source_id == "source:aisc:scm:15:pdf:c5fbe648"
        ]
        self.assertEqual(len(matching), 1)
        requirement = matching[0]
        self.assertEqual(requirement.object_key, "building-code-ast/aisc-scm-15/source")
        self.assertEqual(requirement.sha256, DIGEST)
        self.assertEqual(requirement.size, 221_820_282)
        self.assertEqual(requirement.media_type, "application/pdf")
        validate_source_object_catalog(
            source_object_catalog_from_dict(
                {
                    "catalog_version": catalog_payload["catalog_version"],
                    "type": catalog_payload["type"],
                    "entries": [requirement.to_dict()],
                }
            ),
            register,
        )


if __name__ == "__main__":
    unittest.main()
