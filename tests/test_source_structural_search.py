from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from building_code_ast.retrieval import (
    SourceArtifactIdentity,
    SourceEvidence,
    rebuild_evidence_store,
)
from building_code_ast.retrieval.structural_search import (
    StructuralCandidate,
    StructuralSearchFilters,
    structural_search_evidence_store,
)


class SourceStructuralSearchTests(unittest.TestCase):
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
                block_index=1,
                text="Table 8.2-1 synthetic minimum rate.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
                observed_metadata={"font.size": 9.0},
                derived_metadata={"candidate.table": True, "font.relative_size": 0.9},
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=2,
                block_index=1,
                text="Figure 8.2-1 synthetic minimum rate.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
                observed_metadata={"font.size": 12.0},
                derived_metadata={"candidate.figure": True, "font.relative_size": 1.2},
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=3,
                block_index=1,
                text="SYNTHETIC MINIMUM RATE",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
                observed_metadata={"font.size": 14.0},
                derived_metadata={"candidate.heading": True, "font.relative_size": 1.4},
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=3,
                block_index=2,
                text="Unannotated synthetic minimum rate.",
                bbox=(72.0, 110.0, 540.0, 130.0),
                extraction_method="synthetic/1",
            ),
        )

    def _store(self, directory: str) -> Path:
        path = Path(directory) / "evidence.sqlite3"
        rebuild_evidence_store(path, artifact=self.artifact, evidence=self.records)
        return path

    def test_candidate_filter_composes_with_lexical_search_without_changing_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            unfiltered = structural_search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum rate",
            )
            tables = structural_search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(candidate=StructuralCandidate.TABLE),
            )

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].evidence.evidence_id, self.records[0].evidence_id)
        original = next(result for result in unfiltered if result.evidence.evidence_id == tables[0].evidence.evidence_id)
        self.assertEqual(tables[0].retrieval_score, original.retrieval_score)
        self.assertEqual(tables[0].score_method, original.score_method)

    def test_page_range_filters_after_lexical_matching_in_source_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = structural_search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(pdf_page_min=2, pdf_page_max=3),
            )

        self.assertEqual([result.evidence.pdf_page for result in results], [2, 3, 3])

    def test_observed_and_derived_numeric_filters_exclude_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._store(directory)
            font = structural_search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(min_font_size=11.0, max_font_size=13.0),
            )
            relative = structural_search_evidence_store(
                path,
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(min_relative_font_size=1.3),
            )

        self.assertEqual([result.evidence.evidence_id for result in font], [self.records[1].evidence_id])
        self.assertEqual([result.evidence.evidence_id for result in relative], [self.records[2].evidence_id])

    def test_filtering_happens_before_result_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = structural_search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(candidate="heading"),
                limit=1,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].evidence.evidence_id, self.records[2].evidence_id)

    def test_invalid_filters_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "candidate"):
            StructuralSearchFilters(candidate="requirement")
        with self.assertRaisesRegex(ValueError, "page"):
            StructuralSearchFilters(pdf_page_min=0)
        with self.assertRaisesRegex(ValueError, "page range"):
            StructuralSearchFilters(pdf_page_min=3, pdf_page_max=2)
        with self.assertRaisesRegex(ValueError, "font size"):
            StructuralSearchFilters(min_font_size=-1.0)
        with self.assertRaisesRegex(ValueError, "font size range"):
            StructuralSearchFilters(min_font_size=14.0, max_font_size=12.0)

    def test_result_shape_remains_lexical_and_nonsemantic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results = structural_search_evidence_store(
                self._store(directory),
                artifact=self.artifact,
                query="minimum rate",
                filters=StructuralSearchFilters(candidate="table"),
            )

        payload = results[0].to_dict()
        self.assertIn("retrieval_score", payload)
        self.assertNotIn("confidence", payload)
        self.assertNotIn("semantic", payload)


if __name__ == "__main__":
    unittest.main()
