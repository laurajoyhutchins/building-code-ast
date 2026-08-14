from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from building_code_ast.document_validation import validate_document_ast
from building_code_ast.ingest.nec2017 import (
    build_article_seed,
    select_article_blocks,
)
from building_code_ast.ingest.pdf_layout import (
    LEGACY_CONTENT_ORDER_POLICY,
    PdfBlock,
    PdfLayoutDocument,
    PdfOutlineItem,
    PdfPage,
    normalize_block_text,
    order_content_blocks,
)


class PdfLayoutTests(unittest.TestCase):
    def test_normalize_block_text_repairs_line_break_hyphen(self) -> None:
        self.assertEqual(
            normalize_block_text("consid‐\nered necessary"),
            "considered necessary",
        )

    def test_normalize_block_text_preserves_real_hyphen(self) -> None:
        self.assertEqual(
            normalize_block_text("ground-fault protection"),
            "ground-fault protection",
        )

    def test_order_content_blocks_reads_left_column_before_right(self) -> None:
        blocks = (
            PdfBlock(page_number=1, bbox=(327.0, 100.0, 576.0, 130.0), text="right"),
            PdfBlock(page_number=1, bbox=(54.0, 100.0, 303.0, 130.0), text="left"),
        )

        ordered = order_content_blocks(blocks, page_width=612.0)

        self.assertEqual([block.text for block in ordered], ["left", "right"])

    def test_order_content_blocks_removes_page_header_and_footer(self) -> None:
        blocks = (
            PdfBlock(page_number=1, bbox=(54.0, 46.0, 576.0, 58.0), text="header"),
            PdfBlock(page_number=1, bbox=(54.0, 100.0, 303.0, 130.0), text="content"),
            PdfBlock(page_number=1, bbox=(54.0, 741.0, 576.0, 752.0), text="footer"),
        )

        ordered = order_content_blocks(blocks, page_width=612.0)

        self.assertEqual([block.text for block in ordered], ["content"])

    def test_fixed_band_midpoint_order_is_explicit_legacy_compatibility_policy(self) -> None:
        self.assertEqual(
            LEGACY_CONTENT_ORDER_POLICY.name,
            "legacy-fixed-bands-midpoint-v1",
        )
        self.assertEqual(LEGACY_CONTENT_ORDER_POLICY.top_content_y, 65.0)
        self.assertEqual(LEGACY_CONTENT_ORDER_POLICY.bottom_content_y, 730.0)
        self.assertIn("compatibility", order_content_blocks.__doc__.casefold())
        self.assertIn("layout_analysis", order_content_blocks.__doc__)


def _synthetic_layout() -> PdfLayoutDocument:
    return PdfLayoutDocument(
        file_name="synthetic-nec.pdf",
        outline=(
            PdfOutlineItem(2, "100 Definitions", 1),
            PdfOutlineItem(2, "110 Requirements for Electrical Installations", 2),
            PdfOutlineItem(2, "200 Use and Identification", 3),
        ),
        pages=(
            PdfPage(
                page_number=1,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(1, (54.0, 100.0, 303.0, 130.0), "ARTICLE 100\nDefinitions"),
                    PdfBlock(
                        1,
                        (54.0, 150.0, 303.0, 190.0),
                        "Synthetic Term. A project-authored definition used for testing.",
                    ),
                ),
            ),
            PdfPage(
                page_number=2,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(2, (54.0, 100.0, 303.0, 130.0), "Article 100 tail paragraph."),
                    PdfBlock(
                        2,
                        (327.0, 100.0, 576.0, 130.0),
                        "ARTICLE 110\nRequirements for Electrical Installations",
                    ),
                    PdfBlock(
                        2,
                        (327.0, 150.0, 576.0, 200.0),
                        "110.1 Scope. This synthetic article covers test installations.",
                    ),
                    PdfBlock(
                        2,
                        (339.0, 210.0, 564.0, 250.0),
                        "Informational Note: This note is synthetic.",
                    ),
                ),
            ),
            PdfPage(
                page_number=3,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(3, (250.0, 80.0, 370.0, 100.0), "Chapter 2 Wiring and Protection"),
                    PdfBlock(3, (54.0, 120.0, 303.0, 150.0), "ARTICLE 200\nUse and Identification"),
                ),
            ),
        ),
    )


class ArticleSeedTests(unittest.TestCase):
    def test_same_page_article_boundary_does_not_leak_adjacent_text(self) -> None:
        layout = _synthetic_layout()

        article_100 = select_article_blocks(layout, "100")
        article_110 = select_article_blocks(layout, "110")

        self.assertEqual(
            [normalize_block_text(block.text) for block in article_100],
            [
                "ARTICLE 100 Definitions",
                "Synthetic Term. A project-authored definition used for testing.",
                "Article 100 tail paragraph.",
            ],
        )
        self.assertEqual(
            [normalize_block_text(block.text) for block in article_110],
            [
                "ARTICLE 110 Requirements for Electrical Installations",
                "110.1 Scope. This synthetic article covers test installations.",
                "Informational Note: This note is synthetic.",
            ],
        )

    def test_article_100_builds_definition_entry_and_exact_provenance(self) -> None:
        seed = build_article_seed(
            _synthetic_layout(),
            "100",
            source_sha256="a" * 64,
            source_size=1234,
        )

        validate_document_ast(seed.document_ast)
        payload = seed.to_dict()
        nodes = payload["document_ast"]["root"]["children"][0]["children"]
        self.assertIn("definition_entry", {node["type"] for node in nodes})
        self.assertEqual(payload["source_manifest"]["artifact_id"], "nfpa:70")
        self.assertEqual(
            payload["source_manifest"]["edition_id"],
            "2017:pdf:sha256:" + "a" * 64,
        )
        self.assertNotIn("/", payload["source_manifest"]["file_name"])

        source_text = seed.document_ast.source_text
        for entry in seed.source_map:
            self.assertEqual(
                source_text[entry.normalized_start : entry.normalized_end],
                entry.normalized_text,
            )

    def test_missing_article_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "article 250"):
            select_article_blocks(_synthetic_layout(), "250")


class CliTests(unittest.TestCase):
    def _module(self):
        module_path = Path(__file__).resolve().parents[1] / "tools" / "ingest_nec2017.py"
        spec = importlib.util.spec_from_file_location("ingest_nec2017", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_force_refuses_to_delete_unrecognized_directory_contents(self) -> None:
        module = self._module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            (output / "unrecognized.txt").write_text("keep me", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "unrecognized"):
                module.prepare_output_directory(output, force=True)

            self.assertTrue((output / "unrecognized.txt").exists())

    def test_force_replaces_only_known_generated_files(self) -> None:
        module = self._module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            for name in module.KNOWN_OUTPUT_FILES:
                (output / name).write_text("old", encoding="utf-8")

            module.prepare_output_directory(output, force=True)

            self.assertEqual(list(output.iterdir()), [])

    def test_nonempty_output_directory_requires_force(self) -> None:
        module = self._module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            (output / next(iter(module.KNOWN_OUTPUT_FILES))).write_text(
                "old", encoding="utf-8"
            )

            with self.assertRaisesRegex(RuntimeError, "not empty"):
                module.prepare_output_directory(output, force=False)

    def test_written_manifest_does_not_disclose_absolute_source_path(self) -> None:
        module = self._module()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            output.mkdir()
            source = Path(directory) / "private-nec.pdf"
            source.write_bytes(b"synthetic")
            payload = {
                "source_manifest": {
                    "artifact_id": "nfpa:70",
                    "edition_id": "2017:pdf:sha256:" + "a" * 64,
                    "file_name": source.name,
                    "sha256": "a" * 64,
                    "size_bytes": source.stat().st_size,
                }
            }
            module.write_json(output / "manifest.json", payload)
            rendered = (output / "manifest.json").read_text(encoding="utf-8")

            self.assertNotIn(str(source.parent), rendered)
            self.assertIn(source.name, rendered)


if __name__ == "__main__":
    unittest.main()
