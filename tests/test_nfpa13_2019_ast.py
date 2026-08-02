from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_nfpa13_2019_ast.py"
SPEC = importlib.util.spec_from_file_location("extract_nfpa13_2019_ast", MODULE_PATH)
assert SPEC and SPEC.loader
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


def raw(
    text: str,
    *,
    page: int = 1,
    x: float = 54.0,
    y: float = 100.0,
    width: float = 200.0,
    font: str = "NewBaskervilleStd-Roman",
    size: float = 9.0,
) -> object:
    return subject.RawLine(
        text=text,
        pdf_page=page,
        printed_page=f"13-{page}",
        column=0 if x < 306 else 1,
        bbox=(x, y, x + width, y + 10.0),
        fonts=(font,),
        sizes=(size,),
    )


class SourceStreamTests(unittest.TestCase):
    def test_filters_artifacts_and_orders_two_columns(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("2019 Edition", y=741, font="HelveticaNeueLTStd-Roman", size=7),
                raw("RIGHT SECOND", x=309, y=120),
                raw("13-1", y=35, font="NewBaskervilleStd-Bold", size=8),
                raw("LEFT FIRST", x=54, y=110),
                raw("N", x=43, y=130, font="NewBaskervilleStd-BoldIt"),
                raw("RIGHT FIRST", x=309, y=100),
            ]
        )
        self.assertEqual("LEFT FIRST\nRIGHT FIRST\nRIGHT SECOND", stream.text)
        self.assertEqual(["LEFT FIRST", "RIGHT FIRST", "RIGHT SECOND"], [line.text for line in stream.lines])
        self.assertEqual((0, 10), (stream.lines[0].start, stream.lines[0].end))
        self.assertEqual((11, 22), (stream.lines[1].start, stream.lines[1].end))

    def test_lines_in_uses_indexed_offset_boundaries(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [raw(f"line-{index}", y=100 + index) for index in range(100)]
        )
        selected = stream.lines_in(stream.lines[40].start, stream.lines[60].end)
        self.assertEqual(tuple(line.start for line in stream.lines), stream.starts)
        self.assertEqual("line-40", selected[0].text)
        self.assertEqual("line-60", selected[-1].text)
        self.assertEqual(21, len(selected))

    def test_preserves_exact_line_text(self) -> None:
        stream = subject.build_source_stream_from_lines([raw("  exact  text  ")])
        self.assertEqual("  exact  text  ", stream.text)
        self.assertEqual("  exact  text  ", stream.text[stream.lines[0].start : stream.lines[0].end])

    def test_filters_isolated_revision_marker_regardless_of_margin_position(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Clause text", y=100),
                raw("N", x=140, y=112, font="NewBaskervilleStd-BoldIt"),
                raw("continued", y=124),
            ]
        )
        self.assertEqual("Clause text\ncontinued", stream.text)


class RangeTests(unittest.TestCase):
    def test_ranges_end_at_next_same_or_shallower_anchor(self) -> None:
        parents = {
            "1": "document",
            "1.1": "1",
            "1.1.1": "1.1",
            "1.1.2": "1.1",
            "1.2": "1",
            "2": "document",
        }
        anchors = {"1": 0, "1.1": 10, "1.1.1": 20, "1.1.2": 30, "1.2": 40, "2": 50}
        ranges = subject.compute_structural_ranges(parents, anchors, source_length=60)
        self.assertEqual((10, 40), (ranges["1.1"].start, ranges["1.1"].end))
        self.assertEqual((20, 30), (ranges["1.1.1"].start, ranges["1.1.1"].end))
        self.assertEqual((0, 50), (ranges["1"].start, ranges["1"].end))

    def test_direct_intervals_remove_immediate_children(self) -> None:
        self.assertEqual(
            [(10, 20), (40, 50)],
            subject.direct_intervals(subject.StructuralRange(10, 50), [subject.StructuralRange(20, 40)]),
        )

    def test_implicit_ranges_expand_after_all_descendants_resolve(self) -> None:
        parents = {
            "A": "document",
            "A.10": "A",
            "A.10.2": "A.10",
            "A.10.2.4": "A.10.2",
            "A.10.2.5": "A.10.2",
            "A.10.3": "A.10",
        }
        anchors = {"A.10.2.4": 10, "A.10.2.5": 20, "A.10.3": 30}
        ranges = subject.compute_structural_ranges(parents, anchors, source_length=40)
        self.assertEqual((10, 30), (ranges["A.10.2"].start, ranges["A.10.2"].end))
        self.assertEqual((10, 40), (ranges["A.10"].start, ranges["A.10"].end))
        self.assertEqual((10, 40), (ranges["A"].start, ranges["A"].end))


class BlockTests(unittest.TestCase):
    def test_parses_nested_lists_and_continuations(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("10.1 Parent requirement:", y=100, font="NewBaskervilleStd-Bold"),
                raw("(1) First item", y=120, x=66),
                raw("continues here.", y=130, x=78),
                raw("(a) Nested item", y=146, x=78),
                raw("(i) Roman item", y=162, x=90),
                raw("(2) Second item", y=180, x=66),
            ]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="10.1",
            owner_heading="Parent requirement",
            owner_attributes={"chapter": "10"},
        )
        self.assertEqual(["paragraph", "list_item", "list_item"], [block["type"] for block in blocks])
        first = blocks[1]
        self.assertEqual("(1)", first["attributes"]["marker"])
        self.assertEqual("paragraph", first["children"][0]["type"])
        self.assertEqual("(a)", first["children"][1]["attributes"]["marker"])
        self.assertEqual("(i)", first["children"][1]["children"][1]["attributes"]["marker"])

    def test_attached_marker_is_a_list_item(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [raw("20.15.2.1(2) shall not be required where storage is protected.")]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="20.15.2.1",
            owner_heading=None,
            owner_attributes={"chapter": "20"},
        )
        self.assertEqual("list_item", blocks[0]["type"])
        self.assertEqual("(2)", blocks[0]["attributes"]["marker"])


    def test_rejects_unit_labels_and_graphical_tokens_as_list_markers(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("(mm)", y=100),
                raw("(continues)", y=120),
                raw("(1)", y=140, font="HelveticaNeueLTStd-Roman"),
                raw("(2) Valid item", y=160),
            ]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="10.1",
            owner_heading=None,
            owner_attributes={"chapter": "10"},
        )
        list_nodes = [block for block in blocks if block["type"] == "list_item"]
        self.assertEqual(1, len(list_nodes))
        self.assertEqual("(2)", list_nodes[0]["attributes"]["marker"])

    def test_break_in_list_continuity_starts_nonoverlapping_paragraph(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("(1) Item", y=100),
                raw("Far paragraph", y=140),
                raw("continues paragraph", y=148),
            ]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="10.1",
            owner_heading=None,
            owner_attributes={"chapter": "10"},
        )
        self.assertEqual(["list_item", "paragraph"], [block["type"] for block in blocks])
        self.assertEqual("(1) Item", blocks[0]["children"][0]["span"]["text"])
        self.assertEqual("Far paragraph\ncontinues paragraph", blocks[1]["span"]["text"])
        self.assertLess(blocks[0]["span"]["end"], blocks[1]["span"]["start"] + 1)

    def test_repeated_list_markers_receive_unique_occurrence_locators(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [raw("(2) First branch", y=100), raw("(2) Restarted branch", y=140)]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="10.1",
            owner_heading=None,
            owner_attributes={"chapter": "10"},
        )
        self.assertEqual(2, len(blocks))
        self.assertNotEqual(blocks[0]["locator"], blocks[1]["locator"])
        self.assertTrue(blocks[1]["locator"].endswith("~2"))

    def test_classifies_definition_note_exception_and_figure(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("3.3.1 Approved. Acceptable to the authority having jurisdiction.", y=100),
                raw("NOTE: This note is informative.", y=130),
                raw("Exception: Sprinklers shall not be required.", y=160),
                raw("FIGURE 10.2.1 Typical Arrangement.", y=190, font="NewBaskervilleStd-Bold"),
            ]
        )
        blocks = subject.parse_direct_blocks(
            stream,
            [(0, len(stream.text))],
            owner_locator="3.3.1",
            owner_heading="Approved",
            owner_attributes={"chapter": "3"},
        )
        self.assertEqual(
            ["definition_entry", "note", "note", "unsupported"],
            [block["type"] for block in blocks],
        )
        self.assertEqual("exception", blocks[2]["attributes"]["kind"])
        self.assertEqual("figure", blocks[3]["attributes"]["kind"])


class DocumentLevelTests(unittest.TestCase):
    def test_document_level_blocks_own_text_outside_structural_children(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [raw("Front matter", y=100), raw("Chapter 1", y=120), raw("Clause", y=140)]
        )
        child = subject.StructuralRange(stream.lines[1].start, len(stream.text))
        blocks = subject.document_level_blocks(stream, [child])
        self.assertEqual(1, len(blocks))
        self.assertEqual("Front matter", blocks[0]["span"]["text"])
        self.assertEqual("true", blocks[0]["attributes"]["owns_source"])


class CaptionTests(unittest.TestCase):
    def test_table_clips_stop_at_next_structural_line_in_same_column(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Table 10.2.1 Test Table", x=327, y=100, font="NewBaskervilleStd-Bold"),
                raw("10.2.2 Next clause", x=327, y=300, font="NewBaskervilleStd-Bold"),
                raw("Unrelated left text", x=54, y=200),
            ]
        )
        clips = subject.table_caption_clips(stream)
        self.assertEqual(1, len(clips))
        self.assertEqual("table:10.2.1", clips[0]["locator"])
        self.assertEqual(306.0, clips[0]["bbox"][0])
        self.assertLess(clips[0]["bbox"][3], 300.0)

    def test_table_extraction_uses_source_geometry_without_layout_solver(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Table 1.1 Example", x=54, y=100, font="NewBaskervilleStd-Bold"),
                raw("Column A", x=54, y=120, width=80, size=8),
                raw("Column B", x=160, y=120, width=80, size=8),
                raw("Value 1", x=54, y=140, width=80, size=8),
                raw("Value 2", x=160, y=140, width=80, size=8),
                raw("1.2 Next clause", x=54, y=180, font="NewBaskervilleStd-Bold"),
            ]
        )
        tables = subject._extract_tables(None, stream)
        self.assertEqual(1, len(tables))
        self.assertEqual("table:1.1", tables[0].locator)
        self.assertEqual(("Column A", "Column B"), tables[0].matrix[1])
        self.assertEqual(stream.lines[0].start, tables[0].start)
        self.assertEqual(stream.lines[4].end, tables[0].end)

    def test_table_source_index_queries_only_overlapping_lines(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Table 1.1 Example", y=100, font="NewBaskervilleStd-Bold"),
                raw("Cell", y=120),
                raw("1.2 Next clause", y=180, font="NewBaskervilleStd-Bold"),
            ]
        )
        table = subject._extract_tables(None, stream)[0]
        index = subject.TableSourceIndex.from_tables([table])
        self.assertEqual([table.locator], [item.locator for item in index.overlapping(0, stream.lines[1].end)])
        self.assertEqual([], index.overlapping(stream.lines[2].start, len(stream.text)))

    def test_table_node_emits_heading_rows_and_source_owning_cells(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Table 1.1 Example", x=54, y=100, font="NewBaskervilleStd-Bold"),
                raw("Column A", x=54, y=120, width=80, size=8),
                raw("Column B", x=160, y=120, width=80, size=8),
                raw("Value 1", x=54, y=140, width=80, size=8),
                raw("Value 2", x=160, y=140, width=80, size=8),
                raw("1.2 Next clause", x=54, y=180, font="NewBaskervilleStd-Bold"),
            ]
        )
        table = subject._extract_tables(None, stream)[0]
        node = subject._table_node(stream, table)
        self.assertEqual("false", node["attributes"]["owns_source"])
        self.assertEqual("table_heading", node["children"][0]["type"])
        rows = [child for child in node["children"] if child["type"] == "table_row"]
        self.assertEqual(2, len(rows))
        self.assertEqual(["Column A", "Column B"], [cell["span"]["text"] for cell in rows[0]["children"]])
        self.assertTrue(
            all(cell["attributes"]["owns_source"] == "true" for row in rows for cell in row["children"])
        )

    def test_table_splitting_removes_only_table_lines_from_canonical_stream(self) -> None:
        stream = subject.build_source_stream_from_lines(
            [
                raw("Table 1.1 Example", x=36, y=100, width=540, font="NewBaskervilleStd-Bold"),
                raw("Left cell", x=54, y=120),
                raw("Unrelated left-column prose", x=54, y=200),
                raw("Right cell", x=330, y=120),
                raw("1.2 Next clause", x=330, y=180, font="NewBaskervilleStd-Bold"),
            ]
        )
        table = subject._extract_tables(None, stream)[0]
        parts = subject._split_around_objects((0, len(stream.text)), [table])
        text = "\n".join(
            stream.text[start:end]
            for kind, start, end, _ in parts
            if kind == "text"
        )
        self.assertIn("Unrelated left-column prose", text)
        self.assertNotIn("Left cell", text)
        self.assertNotIn("Right cell", text)
        self.assertEqual(1, sum(kind == "table" for kind, *_ in parts))
        blocked_only = subject._split_around_objects(
            (0, len(stream.text)),
            [table],
            emit_tables=False,
        )
        self.assertEqual(0, sum(kind == "table" for kind, *_ in blocked_only))
        blocked_text = "\n".join(
            stream.text[start:end]
            for kind, start, end, _ in blocked_only
            if kind == "text"
        )
        self.assertIn("Unrelated left-column prose", blocked_text)
        self.assertNotIn("Left cell", blocked_text)

    def test_table_caption_preserves_parenthetical_suffix(self) -> None:
        match = subject.TABLE_CAPTION_RE.match("Table 10.2.4.2.1(a) Protection Areas")
        self.assertIsNotNone(match)
        assert match
        self.assertEqual("10.2.4.2.1(a)", match.group("locator"))


class RelationTests(unittest.TestCase):
    def test_resolves_internal_and_preserves_unresolved_references(self) -> None:
        text = "See Section 20.3, Table 21.2.2.1, Figure A.3.3.4, and Section 99.9."
        relations = subject.extract_relations(
            source_node_locator="21.1#p1",
            text=text,
            base_offset=100,
            known_locators={"20.3", "table:21.2.2.1", "figure:A.3.3.4"},
        )
        self.assertEqual(4, len(relations))
        self.assertEqual([True, True, True, False], [item["resolved"] for item in relations])
        self.assertEqual("20.3", relations[0]["target_locator"])
        self.assertEqual("99.9", relations[-1]["target_locator"])
        evidence = relations[0]["evidence"]
        self.assertEqual(
            "Section 20.3",
            text[evidence["start"] - 100 : evidence["end"] - 100],
        )

    def test_does_not_join_reference_keywords_to_numbers_on_later_lines(self) -> None:
        relations = subject.extract_relations(
            source_node_locator="x",
            text="Chapter\n0\nTable\n25.1",
            base_offset=0,
            known_locators=set(),
        )
        self.assertEqual([], relations)

    def test_annex_a_relation_is_deterministic(self) -> None:
        relation = subject.annex_a_relation("A.10.2.4.2.1", {"10.2.4.2.1"})
        self.assertEqual("explains", relation["type"])
        self.assertTrue(relation["resolved"])
        self.assertEqual("10.2.4.2.1", relation["target_locator"])


class SemanticTests(unittest.TestCase):
    def test_classifies_modalities_and_bounded_roles(self) -> None:
        cases = {
            "Sprinklers shall be installed.": "requirement",
            "Sprinklers shall not be omitted.": "prohibition",
            "Sprinklers may be omitted.": "permission",
            "Sprinklers should be inspected.": "recommendation",
            "Exception: Sprinklers may be omitted.": "exception",
            "Where storage exceeds 20 ft, sprinklers shall be installed.": "condition",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                annotations = subject.classify_semantics(
                    source_node_locator="x",
                    text=text,
                    base_offset=0,
                    attributes={},
                )
                self.assertIn(expected, {item["type"] for item in annotations})

    def test_annex_and_definition_context_adds_annotations(self) -> None:
        informative = subject.classify_semantics(
            source_node_locator="A.1#p1",
            text="This material explains the requirement.",
            base_offset=0,
            attributes={"annex": "A"},
        )
        definition = subject.classify_semantics(
            source_node_locator="3.3.1#definition",
            text="Approved. Acceptable to the authority having jurisdiction.",
            base_offset=0,
            attributes={"kind": "definition"},
        )
        self.assertIn("informative", {item["type"] for item in informative})
        self.assertIn("definition", {item["type"] for item in definition})


class DiagnosticTests(unittest.TestCase):
    def test_reports_unresolved_references_and_unsupported_visual_objects(self) -> None:
        nodes = [
            {
                "locator": "1#figure",
                "type": "unsupported",
                "span": {"start": 0, "end": 6, "text": "Figure"},
                "attributes": {"kind": "figure"},
            },
            {
                "locator": "1#caption",
                "type": "table_heading",
                "span": {"start": 7, "end": 12, "text": "Table"},
                "attributes": {"kind": "table_caption"},
            },
        ]
        relations = [
            {
                "source_locator": "1#p1",
                "target_locator": "9.9",
                "resolved": False,
                "evidence": {"start": 13, "end": 20, "text": "Section"},
            }
        ]
        codes = {item["code"] for item in subject.build_diagnostics(relations, nodes)}
        self.assertEqual(
            {
                "unresolved-reference",
                "unsupported-figure-interpretation",
                "unsupported-table-layout",
            },
            codes,
        )


class OverlayTests(unittest.TestCase):
    def test_collects_owned_source_locations_for_one_page(self) -> None:
        bundle = subject.synthetic_bundle("Clause text")
        leaf = bundle["document_ast"]["root"]["children"][0]
        leaf["attributes"]["source_locations"] = json.dumps(
            [
                {"pdf_page": 21, "printed_page": "13-1", "column": 0, "bbox": [54, 100, 200, 110]},
                {"pdf_page": 22, "printed_page": "13-2", "column": 0, "bbox": [54, 100, 200, 110]},
            ]
        )
        self.assertEqual(
            [(54.0, 100.0, 200.0, 110.0)],
            subject.overlay_rectangles_for_page(bundle, 21),
        )


class ValidationTests(unittest.TestCase):
    def test_validates_minimal_bundle_and_deterministic_bytes(self) -> None:
        bundle = subject.synthetic_bundle("Clause text")
        report = subject.validate_bundle(bundle)
        self.assertTrue(report["passed"], report)
        first = subject.canonical_json_bytes(bundle)
        second = subject.canonical_json_bytes(json.loads(first))
        self.assertEqual(first, second)

    def test_accepts_resolved_relation_to_declared_target_alias(self) -> None:
        bundle = subject.synthetic_bundle("Figure caption")
        leaf = bundle["document_ast"]["root"]["children"][0]
        leaf["attributes"]["target_locator"] = "figure:1.1"
        bundle["relations"] = [
            {
                "source_locator": leaf["locator"],
                "type": "references",
                "target_locator": "figure:1.1",
                "resolved": True,
                "evidence": leaf["span"],
            }
        ]
        report = subject.validate_bundle(bundle)
        self.assertTrue(report["passed"], report)

    def test_rejects_invalid_relation_semantic_and_diagnostic_evidence(self) -> None:
        relation_bundle = subject.synthetic_bundle("Clause text")
        relation_bundle["relations"] = [
            {
                "source_locator": "1.1#p1",
                "type": "references_clause",
                "target_locator": "9.9",
                "resolved": False,
                "evidence": {"start": 0, "end": 999, "text": "Clause text"},
            }
        ]
        self.assertTrue(subject.validate_bundle(relation_bundle)["invalid_relation_evidence"])

        semantic_bundle = subject.synthetic_bundle("Clause text")
        semantic_bundle["semantic_annotations"] = [
            {
                "source_locator": "1.1#p1",
                "type": "requirement",
                "confidence": "deterministic",
                "evidence": {"start": 0, "end": 6, "text": "wrong"},
            }
        ]
        self.assertTrue(subject.validate_bundle(semantic_bundle)["invalid_semantic_evidence"])

        diagnostic_bundle = subject.synthetic_bundle("Clause text")
        diagnostic_bundle["document_ast"]["diagnostics"] = [
            {
                "code": "example",
                "severity": "warning",
                "message": "Example diagnostic",
                "span": {"start": -1, "end": 1, "text": "C"},
            }
        ]
        self.assertTrue(subject.validate_bundle(diagnostic_bundle)["invalid_diagnostic_spans"])

    def test_rejects_duplicate_locator_and_invalid_span(self) -> None:
        bundle = subject.synthetic_bundle("Clause text")
        duplicate = json.loads(json.dumps(bundle))
        duplicate["document_ast"]["root"]["children"].append(
            duplicate["document_ast"]["root"]["children"][0]
        )
        report = subject.validate_bundle(duplicate)
        self.assertFalse(report["passed"])
        self.assertTrue(report["duplicate_locators"])

        invalid = subject.synthetic_bundle("Clause text")
        invalid["document_ast"]["root"]["children"][0]["span"]["end"] = 999
        report = subject.validate_bundle(invalid)
        self.assertFalse(report["passed"])
        self.assertTrue(report["invalid_spans"])


if __name__ == "__main__":
    unittest.main()
