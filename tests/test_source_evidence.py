from __future__ import annotations

import unittest

from building_code_ast.source_evidence import SourceArtifactIdentity, SourceEvidence


class SourceEvidenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=12345,
            page_count=12,
        )

    def test_evidence_identity_is_deterministic_from_source_coordinates(self) -> None:
        first = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=3,
            block_index=7,
            text="Synthetic source evidence.",
            bbox=(72.0, 120.0, 540.0, 144.0),
            extraction_method="synthetic-layout/1",
        )
        repeated = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=3,
            block_index=7,
            text="Different extracted text does not redefine the source coordinate identity.",
            bbox=(72.0, 120.0, 540.0, 144.0),
            extraction_method="synthetic-layout/2",
        )

        self.assertEqual(first.evidence_id, repeated.evidence_id)
        self.assertTrue(first.evidence_id.startswith("evidence:sha256:"))

    def test_different_artifact_identity_changes_evidence_identity(self) -> None:
        other_artifact = SourceArtifactIdentity(
            publication_key="synthetic-2026",
            sha256="b" * 64,
            size=12345,
            page_count=12,
        )
        coordinates = dict(
            pdf_page=3,
            block_index=7,
            text="Synthetic source evidence.",
            bbox=(72.0, 120.0, 540.0, 144.0),
            extraction_method="synthetic-layout/1",
        )

        first = SourceEvidence.create(artifact=self.artifact, **coordinates)
        second = SourceEvidence.create(artifact=other_artifact, **coordinates)

        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_serialization_keeps_observed_and_derived_metadata_separate(self) -> None:
        evidence = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=3,
            printed_page="1",
            block_index=7,
            text="Synthetic source evidence.",
            bbox=(72.0, 120.0, 540.0, 144.0),
            extraction_method="synthetic-layout/1",
            observed_metadata={"font_name": "SyntheticSans", "font_size": 10.0},
            derived_metadata={"heading_candidate": True},
        )

        payload = evidence.to_dict()

        self.assertEqual(payload["publication_key"], "synthetic-2026")
        self.assertEqual(payload["source_sha256"], "a" * 64)
        self.assertEqual(payload["pdf_page"], 3)
        self.assertEqual(payload["printed_page"], "1")
        self.assertEqual(payload["bbox"], [72.0, 120.0, 540.0, 144.0])
        self.assertEqual(payload["observed_metadata"]["font_name"], "SyntheticSans")
        self.assertTrue(payload["derived_metadata"]["heading_candidate"])
        self.assertNotIn("heading_candidate", payload["observed_metadata"])

    def test_invalid_artifact_and_coordinates_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            SourceArtifactIdentity(
                publication_key="synthetic-2026",
                sha256="not-a-digest",
                size=12345,
                page_count=12,
            )

        with self.assertRaises(ValueError):
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=13,
                block_index=0,
                text="Outside artifact page range.",
                bbox=(0.0, 0.0, 10.0, 10.0),
                extraction_method="synthetic-layout/1",
            )

        with self.assertRaises(ValueError):
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=0,
                text="Invalid box.",
                bbox=(10.0, 10.0, 5.0, 5.0),
                extraction_method="synthetic-layout/1",
            )


if __name__ == "__main__":
    unittest.main()
