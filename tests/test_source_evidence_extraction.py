from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfPage
from building_code_ast.retrieval import SourceArtifactIdentity
from building_code_ast.retrieval.extraction import (
    extract_layout_evidence,
    verify_source_artifact,
)


class SourceEvidenceExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=2,
        )

    def test_layout_extraction_is_deterministic_under_discovery_reordering(self) -> None:
        left = PdfBlock(
            page_number=1,
            bbox=(72.0, 100.0, 280.0, 120.0),
            text="First synthetic block.\n",
            block_number=4,
        )
        right = PdfBlock(
            page_number=1,
            bbox=(320.0, 100.0, 540.0, 120.0),
            text="Second synthetic block.\n",
            block_number=9,
        )
        later = PdfBlock(
            page_number=2,
            bbox=(72.0, 80.0, 540.0, 100.0),
            text="Third synthetic block.\n",
            block_number=1,
        )
        ordered = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(page_number=1, width=612.0, height=792.0, blocks=(left, right)),
                PdfPage(page_number=2, width=612.0, height=792.0, blocks=(later,)),
            ),
            outline=(),
        )
        shuffled = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(page_number=2, width=612.0, height=792.0, blocks=(later,)),
                PdfPage(page_number=1, width=612.0, height=792.0, blocks=(right, left)),
            ),
            outline=(),
        )

        first = extract_layout_evidence(
            ordered,
            artifact=self.artifact,
            extraction_method="pymupdf-blocks/1",
        )
        second = extract_layout_evidence(
            shuffled,
            artifact=self.artifact,
            extraction_method="pymupdf-blocks/1",
        )

        self.assertEqual(first, second)
        self.assertEqual([(item.pdf_page, item.block_index) for item in first], [(1, 4), (1, 9), (2, 1)])
        self.assertEqual(first[0].text, "First synthetic block.\n")
        self.assertEqual(first[0].bbox, (72.0, 100.0, 280.0, 120.0))

    def test_layout_extraction_can_attach_printed_page_labels_without_identity_change(self) -> None:
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
                            text="Synthetic body.",
                            block_number=2,
                        ),
                    ),
                ),
                PdfPage(page_number=2, width=612.0, height=792.0, blocks=()),
            ),
            outline=(),
        )

        unlabeled = extract_layout_evidence(
            layout,
            artifact=self.artifact,
            extraction_method="pymupdf-blocks/1",
        )
        labeled = extract_layout_evidence(
            layout,
            artifact=self.artifact,
            extraction_method="pymupdf-blocks/1",
            printed_pages={1: "A-1"},
        )

        self.assertEqual(unlabeled[0].evidence_id, labeled[0].evidence_id)
        self.assertIsNone(unlabeled[0].printed_page)
        self.assertEqual(labeled[0].printed_page, "A-1")

    def test_layout_extraction_rejects_page_count_and_block_page_mismatch(self) -> None:
        short = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(PdfPage(page_number=1, width=612.0, height=792.0, blocks=()),),
            outline=(),
        )
        with self.assertRaisesRegex(ValueError, "page_count"):
            extract_layout_evidence(
                short,
                artifact=self.artifact,
                extraction_method="pymupdf-blocks/1",
            )

        mismatched = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(
                    page_number=1,
                    width=612.0,
                    height=792.0,
                    blocks=(
                        PdfBlock(
                            page_number=2,
                            bbox=(72.0, 100.0, 540.0, 120.0),
                            text="Wrong page.",
                            block_number=0,
                        ),
                    ),
                ),
                PdfPage(page_number=2, width=612.0, height=792.0, blocks=()),
            ),
            outline=(),
        )
        with self.assertRaisesRegex(ValueError, "block page_number"):
            extract_layout_evidence(
                mismatched,
                artifact=self.artifact,
                extraction_method="pymupdf-blocks/1",
            )

    def test_layout_extraction_rejects_duplicate_page_or_block_coordinates(self) -> None:
        duplicate_page = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(page_number=1, width=612.0, height=792.0, blocks=()),
                PdfPage(page_number=1, width=612.0, height=792.0, blocks=()),
            ),
            outline=(),
        )
        with self.assertRaisesRegex(ValueError, "duplicate page_number"):
            extract_layout_evidence(
                duplicate_page,
                artifact=self.artifact,
                extraction_method="pymupdf-blocks/1",
            )

        duplicate_block = PdfBlock(
            page_number=1,
            bbox=(72.0, 100.0, 540.0, 120.0),
            text="Duplicate coordinate.",
            block_number=3,
        )
        duplicate_blocks = PdfLayoutDocument(
            file_name="synthetic.pdf",
            pages=(
                PdfPage(page_number=1, width=612.0, height=792.0, blocks=(duplicate_block, duplicate_block)),
                PdfPage(page_number=2, width=612.0, height=792.0, blocks=()),
            ),
            outline=(),
        )
        with self.assertRaisesRegex(ValueError, "duplicate block_number"):
            extract_layout_evidence(
                duplicate_blocks,
                artifact=self.artifact,
                extraction_method="pymupdf-blocks/1",
            )

    def test_verify_source_artifact_hashes_exact_bytes_before_extraction(self) -> None:
        content = b"synthetic pdf bytes"
        artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
            page_count=2,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.pdf"
            path.write_bytes(content)
            verify_source_artifact(path, artifact)

            path.write_bytes(content + b" changed")
            with self.assertRaisesRegex(ValueError, "size|SHA-256"):
                verify_source_artifact(path, artifact)


if __name__ == "__main__":
    unittest.main()
