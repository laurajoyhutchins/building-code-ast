from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from building_code_ast.cli import main
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfPage
from building_code_ast.retrieval import SourceArtifactIdentity, SourceEvidence, rebuild_evidence_store


class SourceSearchCliTests(unittest.TestCase):
    def _artifact_args(self, artifact: SourceArtifactIdentity) -> list[str]:
        return [
            "--source-id", artifact.source_id,
            "--publication-key", artifact.publication_key,
            "--sha256", artifact.sha256,
            "--size", str(artifact.size),
            "--page-count", str(artifact.page_count),
        ]

    def _capture(self, argv: list[str]) -> tuple[int, object]:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(argv)
        return code, json.loads(stream.getvalue())

    def test_source_index_verifies_extracts_and_rebuilds_store(self) -> None:
        content = b"synthetic pdf bytes"
        artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
            page_count=1,
        )
        layout = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=1,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(
                            page_number=1,
                            bbox=(72.0, 100.0, 540.0, 120.0),
                            text="Table 8.2-1 synthetic block.",
                            block_number=2,
                        ),
                    ),
                ),
            ),
            outline=(),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            store = Path(directory) / "evidence.sqlite3"
            source.write_bytes(content)
            with patch("building_code_ast.cli.extract_pdf_layout", return_value=layout) as extract:
                code, payload = self._capture([
                    "source", "index", str(source), "--store", str(store),
                    *self._artifact_args(artifact),
                ])

            self.assertEqual(code, 0)
            self.assertEqual(payload["command"], "source.index")
            self.assertEqual(payload["evidence_count"], 1)
            self.assertEqual(payload["source_sha256"], artifact.sha256)
            self.assertTrue(store.is_file())
            extract.assert_called_once_with(source)

    def test_search_show_page_and_status_emit_provenance_first_json(self) -> None:
        artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=2,
        )
        records = (
            SourceEvidence.create(
                artifact=artifact,
                pdf_page=1,
                block_index=1,
                text="Table 8.2-1 synthetic minimum rate.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
            SourceEvidence.create(
                artifact=artifact,
                pdf_page=2,
                block_index=1,
                text="Other synthetic evidence.",
                bbox=(72.0, 80.0, 540.0, 100.0),
                extraction_method="synthetic/1",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(store, artifact=artifact, evidence=records)
            common = ["--store", str(store), *self._artifact_args(artifact)]

            _, search = self._capture([
                "source", "search", "8.2-1", *common, "--mode", "exact",
            ])
            _, shown = self._capture([
                "source", "show", records[0].evidence_id, *common,
                "--before", "1", "--after", "1",
            ])
            _, page = self._capture(["source", "page", "1", *common])
            _, status = self._capture(["source", "status", *common])

        self.assertEqual(search["command"], "source.search")
        self.assertEqual(search["results"][0]["evidence_id"], records[0].evidence_id)
        self.assertNotIn("confidence", search["results"][0])
        self.assertEqual(shown["command"], "source.show")
        self.assertEqual(shown["context"]["center"]["source_sha256"], artifact.sha256)
        self.assertEqual(page["command"], "source.page")
        self.assertEqual(page["evidence"][0]["pdf_page"], 1)
        self.assertEqual(status["command"], "source.status")
        self.assertEqual(status["evidence_count"], 2)
        self.assertEqual(status["artifact"]["sha256"], artifact.sha256)

    def test_source_commands_support_compact_json(self) -> None:
        artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "evidence.sqlite3"
            rebuild_evidence_store(store, artifact=artifact, evidence=())
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main([
                    "source", "status", "--store", str(store),
                    *self._artifact_args(artifact), "--compact",
                ])
        self.assertEqual(code, 0)
        self.assertNotIn("\n  ", stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())["evidence_count"], 0)

    def test_existing_parse_command_remains_available(self) -> None:
        code, payload = self._capture(["parse", "Equipment shall be guarded.", "--compact"])
        self.assertEqual(code, 0)
        self.assertEqual(payload["source_text"], "Equipment shall be guarded.")


if __name__ == "__main__":
    unittest.main()
