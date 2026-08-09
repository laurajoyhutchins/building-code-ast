from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from building_code_ast.retrieval import (
    SourceArtifactIdentity,
    SourceEvidence,
    rebuild_evidence_store,
)
from building_code_ast.retrieval.context import (
    EvidenceContext,
    expand_evidence_context,
    get_evidence_by_id,
    get_page_evidence,
)


class SourceContextNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=2,
        )
        self.records = (
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=1,
                text="First block.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=3,
                text="Second block.",
                bbox=(72.0, 110.0, 540.0, 130.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=8,
                text="Third block.",
                bbox=(72.0, 140.0, 540.0, 160.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=2,
                block_index=2,
                text="Fourth block.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
        )

    def _store(self, directory: str) -> Path:
        path = Path(directory) / "evidence.sqlite3"
        rebuild_evidence_store(path, artifact=self.artifact, evidence=reversed(self.records))
        return path

    def test_lookup_by_evidence_id_returns_exact_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            found = get_evidence_by_id(
                self._store(directory),
                artifact=self.artifact,
                evidence_id=self.records[1].evidence_id,
            )
        self.assertEqual(found, self.records[1])

    def test_page_retrieval_returns_only_page_records_in_source_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            page = get_page_evidence(
                self._store(directory),
                artifact=self.artifact,
                pdf_page=1,
            )
        self.assertEqual(page, self.records[:3])

    def test_context_expansion_can_cross_page_boundaries_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = expand_evidence_context(
                self._store(directory),
                artifact=self.artifact,
                evidence_id=self.records[2].evidence_id,
                before=2,
                after=1,
            )
        self.assertIsInstance(context, EvidenceContext)
        self.assertEqual(context.previous, self.records[:2])
        self.assertEqual(context.center, self.records[2])
        self.assertEqual(context.next, (self.records[3],))

    def test_page_local_context_never_leaks_adjacent_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = expand_evidence_context(
                self._store(directory),
                artifact=self.artifact,
                evidence_id=self.records[2].evidence_id,
                before=5,
                after=5,
                page_local=True,
            )
        self.assertEqual(context.previous, self.records[:2])
        self.assertEqual(context.next, ())

    def test_context_serialization_preserves_exact_identities_and_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = expand_evidence_context(
                self._store(directory),
                artifact=self.artifact,
                evidence_id=self.records[1].evidence_id,
                before=1,
                after=1,
            )
        payload = context.to_dict()
        self.assertEqual(payload["center"]["evidence_id"], self.records[1].evidence_id)
        self.assertEqual(payload["previous"][0]["pdf_page"], 1)
        self.assertEqual(payload["next"][0]["block_index"], 8)
        self.assertNotIn("confidence", payload)

    def test_missing_ids_pages_and_invalid_ranges_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            with self.assertRaisesRegex(KeyError, "evidence_id"):
                get_evidence_by_id(path, artifact=self.artifact, evidence_id="evidence:missing")
            with self.assertRaisesRegex(ValueError, "pdf_page"):
                get_page_evidence(path, artifact=self.artifact, pdf_page=0)
            with self.assertRaisesRegex(ValueError, "before"):
                expand_evidence_context(
                    path,
                    artifact=self.artifact,
                    evidence_id=self.records[0].evidence_id,
                    before=-1,
                )
            with self.assertRaisesRegex(ValueError, "after"):
                expand_evidence_context(
                    path,
                    artifact=self.artifact,
                    evidence_id=self.records[0].evidence_id,
                    after=-1,
                )


if __name__ == "__main__":
    unittest.main()
