from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from building_code_ast.retrieval import SourceArtifactIdentity, SourceEvidence
from building_code_ast.retrieval.store import (
    SOURCE_EVIDENCE_STORE_VERSION,
    read_evidence_store,
    rebuild_evidence_store,
)


class SourceEvidenceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=2,
        )
        self.first = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=1,
            block_index=4,
            text="First synthetic block.\n",
            bbox=(72.0, 100.0, 280.0, 120.0),
            extraction_method="pymupdf-blocks/1",
            printed_page="1",
            observed_metadata={"font_size": 10.0},
        )
        self.second = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=2,
            block_index=1,
            text="Second synthetic block.\n",
            bbox=(72.0, 80.0, 540.0, 100.0),
            extraction_method="pymupdf-blocks/1",
            derived_metadata={"candidate": True},
        )

    def test_rebuild_round_trips_in_source_order_independent_of_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(
                path,
                artifact=self.artifact,
                evidence=(self.second, self.first),
            )

            loaded = read_evidence_store(path, artifact=self.artifact)

            self.assertEqual(loaded, (self.first, self.second))
            with sqlite3.connect(path) as database:
                version = database.execute(
                    "SELECT schema_version FROM artifact_manifest"
                ).fetchone()[0]
                count = database.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
            self.assertEqual(version, SOURCE_EVIDENCE_STORE_VERSION)
            self.assertEqual(count, 2)

    def test_rebuild_replaces_stale_rows_instead_of_merging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(
                path,
                artifact=self.artifact,
                evidence=(self.first, self.second),
            )
            rebuild_evidence_store(path, artifact=self.artifact, evidence=(self.first,))

            self.assertEqual(read_evidence_store(path, artifact=self.artifact), (self.first,))

    def test_rebuild_rejects_evidence_from_another_source(self) -> None:
        other_artifact = SourceArtifactIdentity(
            source_id="synthetic:other:2026",
            publication_key="synthetic-2026",
            sha256="b" * 64,
            size=1234,
            page_count=2,
        )
        foreign = SourceEvidence.create(
            artifact=other_artifact,
            pdf_page=1,
            block_index=4,
            text="Foreign block.",
            bbox=(72.0, 100.0, 280.0, 120.0),
            extraction_method="pymupdf-blocks/1",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            with self.assertRaisesRegex(ValueError, "source identity"):
                rebuild_evidence_store(path, artifact=self.artifact, evidence=(foreign,))

    def test_read_rejects_store_manifest_for_different_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(path, artifact=self.artifact, evidence=(self.first,))
            wrong = SourceArtifactIdentity(
                source_id=self.artifact.source_id,
                publication_key=self.artifact.publication_key,
                sha256="b" * 64,
                size=self.artifact.size,
                page_count=self.artifact.page_count,
            )

            with self.assertRaisesRegex(ValueError, "artifact manifest"):
                read_evidence_store(path, artifact=wrong)

    def test_read_rejects_tampered_evidence_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(path, artifact=self.artifact, evidence=(self.first,))
            with sqlite3.connect(path) as database:
                database.execute(
                    "UPDATE evidence SET evidence_id = ?",
                    ("evidence:sha256:" + "0" * 64,),
                )
                database.commit()

            with self.assertRaisesRegex(ValueError, "evidence_id"):
                read_evidence_store(path, artifact=self.artifact)


if __name__ == "__main__":
    unittest.main()
