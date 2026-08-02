from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

from building_code_ast.document_validation import validate_document_ast
from building_code_ast.ingest.ibc2018 import (
    ChapterLayout,
    ChapterSpec,
    IbcLayoutDocument,
    LogicalBlock,
    SourceFragment,
    VisualLine,
    build_chapter_seed,
    coalesce_visual_lines,
    merge_visual_fragments,
    parse_chapter_numbers,
    reconstruct_glyph_line,
)
from building_code_ast.ingest.layout_analysis import BodyFontProfile, visual_line_id
from building_code_ast.ingest.table_geometry import (
    TableCandidate,
    TableCellCandidate,
    TableRowCandidate,
)


class GlyphTests(unittest.TestCase):
    def test_reconstructs_words_from_positioned_glyphs(self) -> None:
        chars = [
            {"c": "C", "bbox": (0.0, 0.0, 5.0, 10.0)},
            {"c": "O", "bbox": (5.3, 0.0, 10.3, 10.0)},
            {"c": "D", "bbox": (10.5, 0.0, 15.5, 10.0)},
            {"c": "E", "bbox": (15.7, 0.0, 20.7, 10.0)},
            {"c": "1", "bbox": (24.0, 0.0, 28.0, 10.0)},
        ]

        self.assertEqual(reconstruct_glyph_line(chars), "CODE 1")

    def test_merges_split_same_baseline_word(self) -> None:
        first = VisualLine(
            1,
            (10.0, 10.0, 50.2, 20.0),
            "oper",
            (SourceFragment(1, (10.0, 10.0, 50.2, 20.0), 1, "oper"),),
        )
        second = VisualLine(
            1,
            (50.0, 10.1, 90.0, 20.1),
            "ators and",
            (SourceFragment(1, (50.0, 10.1, 90.0, 20.1), 2, "ators and"),),
        )

        merged = merge_visual_fragments((second, first), page_width=200.0)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].text, "operators and")
        self.assertEqual(len(merged[0].fragments), 2)

    def test_does_not_merge_opposite_columns_when_right_sorts_first(self) -> None:
        right = VisualLine(
            1,
            (120.0, 10.0, 190.0, 20.0),
            "right column",
            (SourceFragment(1, (120.0, 10.0, 190.0, 20.0), 2, "right column"),),
        )
        left = VisualLine(
            1,
            (10.0, 10.1, 80.0, 20.1),
            "left column",
            (SourceFragment(1, (10.0, 10.1, 80.0, 20.1), 1, "left column"),),
        )

        merged = merge_visual_fragments((left, right), page_width=200.0)

        self.assertEqual(len(merged), 2)
        self.assertEqual({line.text for line in merged}, {"left column", "right column"})


class BlockTests(unittest.TestCase):
    def _line(self, page: int, y: float, text: str) -> VisualLine:
        fragment = SourceFragment(
            page,
            (10.0, y, 190.0, y + 10.0),
            int(y),
            text,
        )
        return VisualLine(page, fragment.bbox, text, (fragment,))

    def test_trims_opening_commentary_and_repairs_line_hyphenation(self) -> None:
        lines = (
            self._line(1, 70, "CHAPTER 1"),
            self._line(1, 90, "SCOPE AND ADMINISTRATION"),
            self._line(1, 120, "User notes:"),
            self._line(1, 140, "Commentary that is not code text."),
            self._line(1, 180, "SECTION 101"),
            self._line(1, 200, "GENERAL"),
            self._line(1, 220, "101.1 Scope. The regula-"),
            self._line(1, 231, "tions apply."),
        )

        blocks = coalesce_visual_lines(lines, chapter_number="1")

        self.assertEqual(
            [block.text for block in blocks],
            [
                "CHAPTER 1",
                "SCOPE AND ADMINISTRATION",
                "SECTION 101",
                "GENERAL",
                "101.1 Scope. The regulations apply.",
            ],
        )

    def test_chapter_two_definition_becomes_definition_entry(self) -> None:
        fragment = SourceFragment(
            40,
            (10.0, 10.0, 100.0, 20.0),
            1,
            "[BG] TEST TERM. Synthetic definition.",
        )
        chapter = ChapterLayout(
            ChapterSpec("2", "Definitions", 40, 41),
            (
                LogicalBlock("CHAPTER 2", (fragment,)),
                LogicalBlock("SECTION 202", (fragment,)),
                LogicalBlock(
                    "[BG] TEST TERM. Synthetic definition.",
                    (fragment,),
                ),
            ),
        )
        layout = IbcLayoutDocument("synthetic.pdf", 100, (chapter,))

        seed = build_chapter_seed(
            layout,
            "2",
            source_sha256="a" * 64,
            source_size=123,
        )

        validate_document_ast(seed.document_ast)
        payload = seed.to_dict()
        nodes = payload["document_ast"]["root"]["children"][0]["children"]
        self.assertIn("definition_entry", {node["type"] for node in nodes})
        self.assertEqual(payload["source_manifest"]["artifact_id"], "icc:ibc")
        source = seed.document_ast.source_text
        for entry in seed.source_map:
            self.assertEqual(
                source[entry.normalized_start : entry.normalized_end],
                entry.normalized_text,
            )

    def test_unsupported_chapter_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "supports 1, 2, 3"):
            parse_chapter_numbers(("4",))

    def test_font_heading_evidence_projects_as_heading(self) -> None:
        chapter_line = self._line(1, 70, "CHAPTER 1")
        heading_fragment = SourceFragment(
            1,
            (10.0, 100.0, 190.0, 114.0),
            100,
            "General requirements",
            14.0,
            "SyntheticHeading",
        )
        heading_line = VisualLine(
            1,
            heading_fragment.bbox,
            heading_fragment.raw_text,
            (heading_fragment,),
            font_size=14.0,
            font_name="SyntheticHeading",
        )
        blocks = coalesce_visual_lines(
            (chapter_line, heading_line),
            chapter_number="1",
            body_font=BodyFontProfile(10.0, 11.5, 0.9, ("body_font:10.0",)),
        )
        chapter = ChapterLayout(ChapterSpec("1", "Scope", 1, 1), blocks)
        seed = build_chapter_seed(
            IbcLayoutDocument("synthetic.pdf", 1, (chapter,)),
            "1",
            source_sha256="b" * 64,
            source_size=100,
        )

        nodes = seed.to_dict()["document_ast"]["root"]["children"][0]["children"]
        self.assertEqual(nodes[1]["type"], "heading")

    def test_serialized_table_cells_retain_pdf_fragments(self) -> None:
        heading_fragment = SourceFragment(72, (10.0, 10.0, 100.0, 20.0), 1, "TABLE 1")
        first = SourceFragment(72, (10.0, 30.0, 40.0, 40.0), 2, "A")
        second = SourceFragment(72, (60.0, 30.0, 90.0, 40.0), 3, "B")
        row_line_id = visual_line_id(72, (first, second))
        table = TableCandidate(
            page_number=72,
            rows=(
                TableRowCandidate(
                    page_number=72,
                    source_line_ids=(row_line_id,),
                    cells=(
                        TableCellCandidate("A", (first,), 8, 9),
                        TableCellCandidate("B", (second,), 10, 11),
                    ),
                    bbox=(10.0, 30.0, 90.0, 40.0),
                    cell_starts=(10.0, 60.0),
                    fragments=(first, second),
                    font_size=10.0,
                    confidence=0.95,
                    evidence=("vector_rule_grid",),
                ),
            ),
            normalized_text="TABLE 1\nA\tB",
            confidence=0.95,
            evidence=("vector_rule_grid",),
        )
        block = LogicalBlock(
            text=table.normalized_text,
            fragments=(heading_fragment, first, second),
            table_like=True,
            source_line_ids=(visual_line_id(72, (heading_fragment,)), row_line_id),
            confidence=0.95,
            evidence=table.evidence,
            table=table,
        )
        chapter = ChapterLayout(ChapterSpec("3", "Occupancy", 72, 72), (block,))
        seed = build_chapter_seed(
            IbcLayoutDocument("synthetic.pdf", 100, (chapter,)),
            "3",
            source_sha256="c" * 64,
            source_size=100,
        )

        table_layout = seed.to_dict()["source_map"][0]["table_layout"]
        first_cell = table_layout["rows"][0]["cells"][0]
        self.assertEqual(first_cell["normalized_span"]["text"], "A")
        self.assertEqual(first_cell["fragments"][0]["raw_text"], "A")
        self.assertEqual(table_layout["rows"][0]["source_line_ids"], [row_line_id])


def _load_cli_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "ingest_ibc_2018.py"
    spec = importlib.util.spec_from_file_location("ingest_ibc_2018_cli", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CliTests(unittest.TestCase):
    def test_force_refuses_unrecognized_contents(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            output.mkdir()
            (output / "keep.txt").write_text("owner data", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "unexpected entries"):
                cli.prepare_output_dir(output, force=True)

            self.assertTrue((output / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
