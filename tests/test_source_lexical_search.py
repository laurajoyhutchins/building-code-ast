from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from building_code_ast.retrieval import (
    SourceArtifactIdentity,
    SourceEvidence,
    rebuild_evidence_store,
)
from building_code_ast.retrieval.search import (
    LexicalSearchMode,
    search_evidence_store,
)


class SourceLexicalSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=3,
        )
        self.records = (
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=2,
                text="Table 8.2-1 Minimum ventilation rate for synthetic spaces.",
                bbox=(72.0, 100.0, 540.0, 120.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=2,
                block_index=1,
                text="Equation 8.2-1 uses a synthetic design value.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=3,
                block_index=7,
                text="Minimum outdoor AIR ventilation RATE appears here.",
                bbox=(72.0, 140.0, 540.0, 160.0),
                extraction_method="synthetic/1",
            ),
        )

    def _store(self, directory: str) -> Path:
        path = Path(directory) / "evidence.sqlite3"
        rebuild_evidence_store(path, artifact=self.artifact, evidence=self.records)
        return path

    def test_exact_search_finds_literal_identifier_with_exact_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="8.2-1",
                mode=LexicalSearchMode.EXACT,
            )

        self.assertEqual([result.evidence.pdf_page for result in results], [1, 2])
        self.assertEqual([result.evidence.evidence_id for result in results], [self.records[0].evidence_id, self.records[1].evidence_id])
        self.assertTrue(all(result.mode is LexicalSearchMode.EXACT for result in results))
        self.assertTrue(all(result.retrieval_score > 0 for result in results))

    def test_phrase_search_is_case_insensitive_and_contiguous(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="minimum outdoor air ventilation rate",
                mode="phrase",
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].evidence.evidence_id, self.records[2].evidence_id)

    def test_token_search_matches_all_terms_independent_of_query_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            first = search_evidence_store(
                path,
                artifact=self.artifact,
                query="rate ventilation minimum",
                mode=LexicalSearchMode.TOKEN,
            )
            repeated = search_evidence_store(
                path,
                artifact=self.artifact,
                query="rate ventilation minimum",
                mode=LexicalSearchMode.TOKEN,
            )

        self.assertEqual(first, repeated)
        self.assertEqual([result.evidence.pdf_page for result in first], [1, 3])
        self.assertTrue(all(result.score_method in {"sqlite_fts5_bm25", "token_coverage_fallback"} for result in first))

    def test_source_and_publication_filters_fail_closed_to_no_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            wrong_source = search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum",
                source_id="synthetic:other:2026",
            )
            wrong_publication = search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum",
                publication_key="other-2026",
            )

        self.assertEqual(wrong_source, ())
        self.assertEqual(wrong_publication, ())

    def test_limit_and_result_shape_are_deterministic_and_nonsemantic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="minimum",
                mode="token",
                limit=1,
            )

        self.assertEqual(len(results), 1)
        payload = results[0].to_dict()
        self.assertEqual(payload["evidence_id"], results[0].evidence.evidence_id)
        self.assertEqual(payload["pdf_page"], results[0].evidence.pdf_page)
        self.assertIn("retrieval_score", payload)
        self.assertNotIn("confidence", payload)
        self.assertNotIn("ast", payload)

    def test_invalid_search_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            with self.assertRaisesRegex(ValueError, "query"):
                search_evidence_store(path, artifact=self.artifact, query="   ")
            with self.assertRaisesRegex(ValueError, "limit"):
                search_evidence_store(path, artifact=self.artifact, query="minimum", limit=0)
            with self.assertRaisesRegex(ValueError, "mode"):
                search_evidence_store(path, artifact=self.artifact, query="minimum", mode="semantic")


if __name__ == "__main__":
    unittest.main()
