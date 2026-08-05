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
from building_code_ast.ingest.layout_analysis import (
    BodyFontProfile,
    CleanedPage,
    PageLines,
    RuleSegment,
    visual_line_id,
)
from building_code_ast.ingest.ibc2018.pipeline import _announced_ruled_tables
from building_code_ast.ingest.ibc2018.text import (
    _join_text,
    _normalize_visual_text,
    build_hyphenation_lexicon,
    repair_source_spacing,
)
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

    def test_numeric_glyphs_use_geometry_aware_spacing(self) -> None:
        def chars(text: str, gaps: list[float]) -> list[dict[str, object]]:
            x = 0.0
            result: list[dict[str, object]] = []
            for index, character in enumerate(text):
                result.append({"c": character, "bbox": (x, 0.0, x + 4.0, 10.0)})
                if index < len(gaps):
                    x += 4.0 + gaps[index]
            return result

        self.assertEqual(
            reconstruct_glyph_line(chars("SECTION110", [0.3] * 6 + [3.0, 1.75, 1.75])),
            "SECTION 110",
        )
        self.assertEqual(
            reconstruct_glyph_line(chars("1000ml", [1.1, 0.3, 0.2, 3.2, 0.3])),
            "1000 ml",
        )
        self.assertEqual(
            reconstruct_glyph_line(chars("18925L", [1.0, 3.6, 0.4, 0.2, 3.2])),
            "18 925 L",
        )
        self.assertEqual(
            reconstruct_glyph_line(chars("owner’s", [0.3, 0.3, 0.3, 0.3, 0.3, 1.2, 0.3])),
            "owner’s",
        )
        self.assertEqual(_normalize_visual_text("owner’ s authorized"), "owner’s authorized")
        self.assertEqual(_normalize_visual_text("units’ water"), "units’ water")
        self.assertEqual(
            reconstruct_glyph_line(chars("(1)", [0.4, 1.1])),
            "(1)",
        )
        self.assertEqual(
            reconstruct_glyph_line(chars("1-percent", [1.3] + [0.3] * 7)),
            "1-percent",
        )
        self.assertEqual(
            reconstruct_glyph_line(chars("V1-30", [0.3, 1.3, 0.3, 0.3])),
            "V1-30",
        )

    def test_narrow_j_does_not_split_the_following_letter(self) -> None:
        chars = [
            {"c": "j", "bbox": (0.0, 0.0, 2.0, 10.0)},
            {"c": "u", "bbox": (2.95, 0.0, 7.5, 10.0)},
            {"c": "r", "bbox": (7.7, 0.0, 11.0, 10.0)},
        ]

        self.assertEqual(reconstruct_glyph_line(chars), "jur")
        business = [
            {"c": "B", "bbox": (0.0, 0.0, 6.0, 10.0)},
            {"c": "u", "bbox": (6.95, 0.0, 11.5, 10.0)},
            {"c": "s", "bbox": (11.7, 0.0, 15.2, 10.0)},
        ]
        self.assertEqual(reconstruct_glyph_line(business), "Bus")


    def test_superscript_fragment_attaches_to_its_visual_row(self) -> None:
        base = VisualLine(
            1,
            (10.0, 10.0, 18.0, 20.0),
            "5",
            (SourceFragment(1, (10.0, 10.0, 18.0, 20.0), 1, "5", 10.0),),
            font_size=10.0,
        )
        superscript = VisualLine(
            1,
            (18.5, 8.0, 22.0, 15.0),
            "2",
            (SourceFragment(1, (18.5, 8.0, 22.0, 15.0), 2, "2", 7.0),),
            font_size=7.0,
        )
        suffix = VisualLine(
            1,
            (22.5, 10.0, 32.0, 20.0),
            " ft",
            (SourceFragment(1, (22.5, 10.0, 32.0, 20.0), 3, " ft", 10.0),),
            font_size=10.0,
        )

        merged = merge_visual_fragments((superscript, suffix, base), page_width=200.0)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].text, "52 ft")
        self.assertEqual([fragment.block_number for fragment in merged[0].fragments], [1, 2, 3])

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


class SourceSpacingTests(unittest.TestCase):
    def _line(self, text: str, block: int) -> VisualLine:
        fragment = SourceFragment(1, (10.0, block * 12.0, 190.0, block * 12.0 + 10.0), block, text)
        return VisualLine(1, fragment.bbox, text, (fragment,))

    def test_repairs_repeated_missing_boundaries_from_source_evidence(self) -> None:
        lines = (
            self._line("means ofegress", 1),
            self._line("path ofegress", 2),
            self._line("means of egress", 3),
            self._line("portion of egress", 4),
            self._line("route of egress", 5),
            self._line("width of egress", 6),
            self._line("insufficient evidence", 7),
            self._line("in sufficient detail", 8),
            self._line("in sufficient quantity", 9),
        )
        page = PageLines(1, 200.0, 300.0, lines)

        repaired = repair_source_spacing((page,))[0]

        self.assertEqual(repaired.lines[0].text, "means of egress")
        self.assertEqual(repaired.lines[0].fragments[0].raw_text, "means of egress")
        self.assertEqual(repaired.lines[6].text, "insufficient evidence")
        self.assertNotEqual(repaired.lines[0].line_id, lines[0].line_id)



class HyphenationTests(unittest.TestCase):
    def _line(self, text: str, y: float) -> VisualLine:
        fragment = SourceFragment(1, (10.0, y, 190.0, y + 10.0), int(y), text)
        return VisualLine(1, fragment.bbox, text, (fragment,))

    def test_uses_intact_source_words_and_compounds(self) -> None:
        lexicon = build_hyphenation_lexicon(
            (
                self._line("replacement", 10.0),
                self._line("cross-sectional", 20.0),
                self._line("Manual wet.", 30.0),
            )
        )

        self.assertEqual(_join_text("replace-", "ment", lexicon), "replacement")
        self.assertEqual(
            _join_text("cross-", "sectional", lexicon),
            "cross-sectional",
        )
        self.assertEqual(_join_text("Manual-", "wet system", lexicon), "Manual wet system")

    def test_preserves_reviewed_and_chained_compounds(self) -> None:
        lexicon = build_hyphenation_lexicon(())

        self.assertEqual(_join_text("double-", "pivoted", lexicon), "double-pivoted")
        self.assertEqual(_join_text("out-to-", "out", lexicon), "out-to-out")
        self.assertEqual(_join_text("fixed-", "in-place", lexicon), "fixed-in-place")



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

    def test_split_definition_heading_remains_one_definition_block(self) -> None:
        lines = (
            self._line(1, 70, "CHAPTER 2"),
            self._line(1, 80, "SECTION 202"),
            self._line(1, 90, "[BS] CONVENTIONAL LIGHT-FRAME CONSTRUC-"),
            self._line(1, 100, "TION. Construction formed by repetitive framing."),
        )

        blocks = coalesce_visual_lines(lines, chapter_number="2")

        self.assertEqual(len(blocks), 3)
        self.assertEqual(
            blocks[-1].text,
            "[BS] CONVENTIONAL LIGHT-FRAME CONSTRUCTION. Construction formed by repetitive framing.",
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


    def test_committee_prefixed_table_label_announces_ruled_grid(self) -> None:
        def table_line(text: str, x0: float, y0: float, x1: float, block: int) -> VisualLine:
            fragment = SourceFragment(72, (x0, y0, x1, y0 + 8.0), block, text, 8.0)
            return VisualLine(72, fragment.bbox, text, (fragment,), font_size=8.0)

        page = CleanedPage(
            page_number=72,
            width=120.0,
            height=140.0,
            retained=(
                table_line("[F] TABLE 307.1", 10.0, 2.0, 110.0, 1),
                table_line("A", 20.0, 25.0, 40.0, 2),
                table_line("B", 70.0, 25.0, 90.0, 3),
                table_line("C", 20.0, 75.0, 40.0, 4),
                table_line("D", 70.0, 75.0, 90.0, 5),
            ),
            removed=(),
            rules=(
                RuleSegment(72, 10.0, 10.0, 110.0, 10.0),
                RuleSegment(72, 10.0, 60.0, 110.0, 60.0),
                RuleSegment(72, 10.0, 110.0, 110.0, 110.0),
                RuleSegment(72, 10.0, 10.0, 10.0, 110.0),
                RuleSegment(72, 60.0, 10.0, 60.0, 110.0),
                RuleSegment(72, 110.0, 10.0, 110.0, 110.0),
            ),
        )

        records = _announced_ruled_tables(page)

        self.assertEqual(len(records), 1)
        table, heading = records[0]
        self.assertEqual(heading.text, "[F] TABLE 307.1")
        self.assertEqual(table.normalized_text, "[F] TABLE 307.1\nA\tB\nC\tD")

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
