from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from building_code_ast.cli import main
from building_code_ast.retrieval import (
    GeneratedDraft,
    GroundedAnswerStatus,
    SourceArtifactIdentity,
    SourceEvidence,
    StructuralCandidate,
    StructuralSearchFilters,
    build_grounding_packet,
    rebuild_evidence_store,
    run_grounded_generation,
)


class SourceRagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:rag:2026",
            publication_key="synthetic-rag-2026",
            sha256="d" * 64,
            size=4321,
            page_count=3,
        )
        self.records = (
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=1,
                text="Synthetic ventilation systems shall provide outdoor air.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=1,
                block_index=2,
                text="Exception: synthetic laboratory exhaust follows Section 4.2.",
                bbox=(72.0, 105.0, 540.0, 125.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=2,
                block_index=1,
                text="Table 8.2-1 synthetic outdoor air values.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
                derived_metadata={"candidate.table": True},
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=2,
                block_index=2,
                text="Synthetic minimum outdoor air is 10 units.",
                bbox=(72.0, 105.0, 540.0, 125.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=self.artifact,
                pdf_page=3,
                block_index=1,
                text="Unrelated synthetic appendix text.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
        )

    def _store(self, directory: str) -> Path:
        path = Path(directory) / "evidence.sqlite3"
        rebuild_evidence_store(path, artifact=self.artifact, evidence=self.records)
        return path

    def _artifact_args(self, store: Path) -> list[str]:
        return [
            "--store",
            str(store),
            "--source-id",
            self.artifact.source_id,
            "--publication-key",
            self.artifact.publication_key,
            "--sha256",
            self.artifact.sha256,
            "--size",
            str(self.artifact.size),
            "--page-count",
            str(self.artifact.page_count),
        ]

    def test_grounding_packet_expands_hits_with_page_local_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet = build_grounding_packet(
                self._store(directory),
                artifact=self.artifact,
                query="outdoor air",
                limit=2,
                before=1,
                after=1,
                page_local=True,
            )

        self.assertEqual(packet.query, "outdoor air")
        self.assertEqual(len(packet.chunks), 2)
        self.assertEqual(packet.chunks[0].context.center.evidence_id, self.records[0].evidence_id)
        self.assertEqual(
            [item.evidence_id for item in packet.chunks[0].context.next],
            [self.records[1].evidence_id],
        )
        self.assertEqual(packet.chunks[1].context.center.evidence_id, self.records[2].evidence_id)
        self.assertEqual(
            [item.evidence_id for item in packet.chunks[1].context.next],
            [self.records[3].evidence_id],
        )
        self.assertNotIn("confidence", packet.to_dict())

    def test_structural_filtering_happens_before_grounding_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet = build_grounding_packet(
                self._store(directory),
                artifact=self.artifact,
                query="outdoor air",
                filters=StructuralSearchFilters(candidate=StructuralCandidate.TABLE),
                limit=1,
            )

        self.assertEqual(len(packet.chunks), 1)
        self.assertEqual(packet.chunks[0].context.center.evidence_id, self.records[2].evidence_id)

    def test_generation_accepts_only_citations_present_in_grounding_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)

            result = run_grounded_generation(
                store,
                artifact=self.artifact,
                query="outdoor air",
                generator=lambda packet: GeneratedDraft(
                    generator_id="synthetic-generator/1",
                    text="The retrieved synthetic evidence describes outdoor-air provisions.",
                    cited_evidence_ids=(packet.chunks[0].context.center.evidence_id,),
                ),
            )

        self.assertEqual(result.status, GroundedAnswerStatus.ANSWERED)
        self.assertEqual(result.generator_id, "synthetic-generator/1")
        self.assertEqual(result.cited_evidence_ids, (self.records[0].evidence_id,))
        self.assertNotIn("confidence", result.to_dict())
        self.assertNotIn("compliance", result.to_dict())

    def test_generation_may_cite_neighbor_context_but_not_unknown_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            result = run_grounded_generation(
                store,
                artifact=self.artifact,
                query="ventilation systems",
                before=0,
                after=1,
                generator=lambda packet: GeneratedDraft(
                    generator_id="synthetic-generator/1",
                    text="The neighboring synthetic exception is relevant context.",
                    cited_evidence_ids=(packet.chunks[0].context.next[0].evidence_id,),
                ),
            )

            with self.assertRaisesRegex(ValueError, "citation"):
                run_grounded_generation(
                    store,
                    artifact=self.artifact,
                    query="ventilation systems",
                    generator=lambda packet: GeneratedDraft(
                        generator_id="synthetic-generator/1",
                        text="Unsupported citation.",
                        cited_evidence_ids=("evidence:sha256:" + "0" * 64,),
                    ),
                )

        self.assertEqual(result.cited_evidence_ids, (self.records[1].evidence_id,))

    def test_answered_generation_requires_at_least_one_grounded_citation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "citation"):
                run_grounded_generation(
                    self._store(directory),
                    artifact=self.artifact,
                    query="outdoor air",
                    generator=lambda packet: GeneratedDraft(
                        generator_id="synthetic-generator/1",
                        text="Uncited answer.",
                        cited_evidence_ids=(),
                    ),
                )

    def test_no_hits_returns_insufficient_evidence_without_calling_generator(self) -> None:
        called = False

        def generator(packet):
            nonlocal called
            called = True
            raise AssertionError("generator must not run without retrieved evidence")

        with tempfile.TemporaryDirectory() as directory:
            result = run_grounded_generation(
                self._store(directory),
                artifact=self.artifact,
                query="nonexistent flux capacitor",
                generator=generator,
            )

        self.assertFalse(called)
        self.assertEqual(result.status, GroundedAnswerStatus.INSUFFICIENT_EVIDENCE)
        self.assertIsNone(result.answer_text)
        self.assertEqual(result.cited_evidence_ids, ())

    def test_source_rag_cli_emits_deterministic_grounding_packet_without_model_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        "source",
                        "rag",
                        "outdoor air",
                        *self._artifact_args(store),
                        "--limit",
                        "1",
                        "--before",
                        "0",
                        "--after",
                        "1",
                        "--candidate",
                        "table",
                        "--compact",
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["command"], "source.rag")
        self.assertEqual(payload["packet"]["query"], "outdoor air")
        self.assertEqual(len(payload["packet"]["chunks"]), 1)
        self.assertEqual(
            payload["packet"]["chunks"][0]["context"]["center"]["evidence_id"],
            self.records[2].evidence_id,
        )
        self.assertEqual(payload["generation"], "not_invoked")


if __name__ == "__main__":
    unittest.main()
