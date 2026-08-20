from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

from building_code_ast.evidence import load_source_package
from building_code_ast.ibc2018_corpus import (
    BoundingBox,
    PageLine,
    SOURCE_PAGE_COUNT,
    SOURCE_SHA256,
    build_coverage_report,
    build_source_manifest,
    inventory_captions,
    inventory_chapter35,
    inventory_cross_references,
    inventory_equations,
    inventory_exceptions,
    inventory_incidental_layouts,
    inventory_vector_graphic_regions,
    normalize_external_families,
    normalize_locator,
    printed_page,
    publication_context,
    stable_id,
    validate_inventory,
    validate_private_evidence_identity,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpora/ibc-2018"


def line(page: int, text: str, y: float, x0: float = 60.0, x1: float = 280.0) -> PageLine:
    return PageLine(
        pdf_page=page,
        text=text,
        bbox=BoundingBox(x0, y, x1, y + 12.0),
        line_id=stable_id("synthetic-line", f"{page}|{text}|{y}|{x0}"),
    )


class Ibc2018CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_manifest = json.loads((CORPUS / "ibc-2018-source-manifest.json").read_text())
        cls.corpus_manifest = json.loads((CORPUS / "ibc-2018-corpus-manifest.json").read_text())
        cls.coverage = json.loads((CORPUS / "ibc-2018-coverage-report.json").read_text())
        cls.tables = json.loads((CORPUS / "ibc-2018-table-inventory.json").read_text())
        cls.figures = json.loads((CORPUS / "ibc-2018-figure-inventory.json").read_text())
        cls.equations = json.loads((CORPUS / "ibc-2018-equation-inventory.json").read_text())
        cls.exceptions = json.loads((CORPUS / "ibc-2018-exception-inventory.json").read_text())
        cls.definitions = json.loads((CORPUS / "ibc-2018-definition-inventory.json").read_text())
        cls.chapter35 = json.loads((CORPUS / "ibc-2018-chapter-35-inventory.json").read_text())
        cls.crossrefs = json.loads((CORPUS / "ibc-2018-cross-reference-inventory.json").read_text())
        cls.incidental = json.loads((CORPUS / "ibc-2018-incidental-layout-inventory.json").read_text())
        cls.pilot = json.loads((CORPUS / "ibc-2018-semantic-pilot.json").read_text())

    def test_exact_source_identity(self) -> None:
        self.assertEqual(self.source_manifest["sha256"], SOURCE_SHA256)
        self.assertEqual(self.source_manifest["file_size_bytes"], 32_608_171)
        self.assertEqual(self.source_manifest["pdf_page_count"], SOURCE_PAGE_COUNT)
        self.assertEqual(self.source_manifest["publication_title"], "2018 International Building Code")
        provenance = self.source_manifest["acquisition_provenance"]
        self.assertEqual(provenance["official_copy_comparison"]["status"], "not_performed")
        self.assertEqual(provenance["artifact_custody"]["raw_source_location"], "private_local_uncommitted")
        self.assertEqual(provenance["artifact_custody"]["replacement_policy"], "new source artifact record required")
        self.assertEqual(self.source_manifest["identity_assurance"]["exact_bytes"], "verified")
        self.assertEqual(self.source_manifest["identity_assurance"]["official_copy_equivalence"], "unverified")

    def test_private_evidence_identity_fails_closed_on_source_mismatch(self) -> None:
        pages = {page: () for page in range(1, SOURCE_PAGE_COUNT + 1)}
        seed = {
            "source_manifest": {
                "sha256": "0" * 64,
                "size_bytes": 32_608_171,
                "page_count": SOURCE_PAGE_COUNT,
                "edition": "2018",
            }
        }
        images = [{"pdf_page": page, "images": []} for page in range(1, SOURCE_PAGE_COUNT + 1)]
        with self.assertRaisesRegex(ValueError, "source SHA-256"):
            validate_private_evidence_identity(pages, seed, images)

    def test_source_package_is_canonical_and_restricted(self) -> None:
        package = load_source_package(CORPUS / "source-package.json")
        binding = package.binding_for_source("source:icc:ibc:2018:pdf:c8f0b755")
        artifact = package.artifact(binding.artifact_id)

        self.assertEqual(package.package_id, "ibc-2018")
        self.assertEqual(artifact.sha256, SOURCE_SHA256)
        self.assertEqual(artifact.access_scope.value, "private_local")
        self.assertEqual(artifact.rights_status.value, "uncertain_restricted")
        self.assertIsNotNone(artifact.rights_note)
        self.assertEqual(binding.evidence_role.value, "normative_text")

    def test_printed_page_mapping(self) -> None:
        self.assertEqual(printed_page(4), "iii")
        self.assertEqual(printed_page(27), "xxvi")
        self.assertEqual(printed_page(28), "1")
        self.assertEqual(printed_page(759), "732")
        self.assertIsNone(printed_page(760))

    def test_publication_context_uses_numeric_chapter_order(self) -> None:
        self.assertEqual(publication_context(284), ("10", None))
        self.assertEqual(publication_context(669), ("35", None))
        self.assertEqual(publication_context(700), (None, "J"))

    def test_manifest_counts_match_inventory_lengths(self) -> None:
        expected = self.corpus_manifest["expected_artifact_counts"]
        self.assertEqual(expected["tables"]["value"], len(self.tables))
        self.assertEqual(expected["figures"]["value"], len(self.figures))
        self.assertEqual(expected["equations"]["value"], len(self.equations))
        self.assertEqual(expected["exceptions"]["value"], len(self.exceptions))

    def test_table_identifier_normalization(self) -> None:
        self.assertEqual(normalize_locator("1 010.1.4.1(1)"), "1010.1.4.1(1)")
        appendix = next(item for item in self.tables if item["published_identifier"] == "C102.1")
        self.assertEqual(appendix["appendix"], "C")

    def test_table_continuations_are_consolidated(self) -> None:
        table = next(item for item in self.tables if item["published_identifier"] == "307.1(1)")
        self.assertEqual(table["pdf_page_range"], [75, 76])
        self.assertEqual(table["continuation_pages"], [76])
        self.assertEqual(len(table["anchors"]), 2)

    def test_embedded_table_labels_are_rejected_detections(self) -> None:
        detections = json.loads((CORPUS / "ibc-2018-detection-inventory.json").read_text())
        rejected = [item for item in detections if item["disposition"] == "rejected_embedded_in_figure"]
        self.assertEqual(len(rejected), 4)
        self.assertTrue(all(item["source_anchor"]["pdf_page"] == 556 for item in rejected))

    def test_figure_identifiers_and_captions_are_attached(self) -> None:
        self.assertEqual(len(self.figures), 56)
        self.assertTrue(all(item["caption"] for item in self.figures))
        self.assertTrue(all(item["published_identifier"] for item in self.figures))

    def test_vector_region_inventory_classifies_without_asserting_semantics(self) -> None:
        evidence = {
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 32_608_171,
            "source_page_count": SOURCE_PAGE_COUNT,
            "pages": [
                {
                    "pdf_page": page,
                    "regions": (
                        [
                            {
                                "pdf_page": page,
                                "bbox": [100.0, 100.0, 260.0, 260.0],
                                "drawing_count": 4,
                                "line_count": 3,
                                "curve_count": 8,
                                "rect_count": 0,
                                "fill_count": 1,
                                "stroke_count": 3,
                                "geometry_fingerprint": "a" * 64,
                            }
                        ]
                        if page == 100
                        else []
                    ),
                }
                for page in range(1, SOURCE_PAGE_COUNT + 1)
            ],
        }
        records = inventory_vector_graphic_regions(evidence, figures=())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["disposition"], "candidate_vector_technical_graphic")
        self.assertEqual(records[0]["review_state"], "disputed")
        self.assertEqual(records[0]["candidate_source"], "pdf_vector_paths")
        self.assertNotIn("observed_text", records[0])

    def test_vector_region_inventory_rejects_page_frames_and_captioned_figures(self) -> None:
        evidence = {
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 32_608_171,
            "source_page_count": SOURCE_PAGE_COUNT,
            "pages": [
                {
                    "pdf_page": page,
                    "regions": (
                        [
                            {
                                "pdf_page": page,
                                "bbox": [24.0, 24.0, 590.0, 770.0],
                                "drawing_count": 4,
                                "line_count": 0,
                                "curve_count": 0,
                                "rect_count": 4,
                                "fill_count": 4,
                                "stroke_count": 0,
                                "geometry_fingerprint": "b" * 64,
                            },
                            {
                                "pdf_page": page,
                                "bbox": [80.0, 200.0, 500.0, 450.0],
                                "drawing_count": 8,
                                "line_count": 2,
                                "curve_count": 20,
                                "rect_count": 0,
                                "fill_count": 2,
                                "stroke_count": 2,
                                "geometry_fingerprint": "c" * 64,
                            },
                        ]
                        if page == 200
                        else []
                    ),
                }
                for page in range(1, SOURCE_PAGE_COUNT + 1)
            ],
        }
        figures = (
            {
                "anchors": [
                    {"pdf_page": 200, "bbox": [90.0, 440.0, 300.0, 455.0]}
                ]
            },
        )
        records = inventory_vector_graphic_regions(evidence, figures=figures)
        by_disposition = {item["disposition"]: item for item in records}
        self.assertEqual(by_disposition["rejected_page_furniture"]["review_state"], "rejected")
        self.assertEqual(by_disposition["rejected_captioned_figure_region"]["review_state"], "rejected")

    def test_equation_blocks_keep_observed_and_normalized_forms_separate(self) -> None:
        self.assertEqual(len(self.equations), 90)
        self.assertTrue(all(item["observed_expression"] for item in self.equations))
        self.assertTrue(all(item["normalized_expression"] is None for item in self.equations))
        self.assertTrue(any(item["continuation_anchors"] for item in self.equations))
        self.assertTrue(any(item["nearby_variable_definitions"] for item in self.equations))

    def test_equation_detector_rejects_prose_measurement(self) -> None:
        pages = {
            page: () for page in range(1, SOURCE_PAGE_COUNT + 1)
        }
        pages[100] = (
            line(100, "loads exceeding 50 psf (2.40 kN/m2), such design live loads", 100),
            line(100, "R = 5.2(ds + dh)", 130),
        )
        result = inventory_equations(pages, (), ())
        self.assertEqual([item["observed_expression"] for item in result], ["R = 5.2(ds + dh)"])

    def test_exception_children_remain_nested(self) -> None:
        self.assertEqual(len(self.exceptions), 769)
        self.assertEqual(
            sum(len(item["nested_exception_numbers"]) for item in self.exceptions),
            881,
        )
        self.assertTrue(all(item["parent_locator"] for item in self.exceptions))

    def test_exception_attachment_from_synthetic_page(self) -> None:
        pages = {page: () for page in range(1, SOURCE_PAGE_COUNT + 1)}
        pages[28] = (
            line(28, "101.2 Scope.", 100),
            line(28, "Exceptions:", 130),
            line(28, "1. First synthetic child.", 150),
            line(28, "2. Second synthetic child.", 170),
        )
        result = inventory_exceptions(pages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["parent_locator"], "101.2")
        self.assertEqual(result[0]["nested_exception_numbers"], ["1", "2"])

    def test_definition_scope_is_preserved(self) -> None:
        chapter2 = [item for item in self.definitions if item["source_section"] == "202"]
        scoped = [item for item in self.definitions if item["source_section"] != "202"]
        self.assertEqual(len(chapter2), 666)
        self.assertEqual(len(scoped), 12)
        self.assertTrue(all(item["scope"] != "code_wide_unless_context_limits" for item in scoped))

    def test_chapter35_rows_preserve_designation_and_edition(self) -> None:
        self.assertEqual(len(self.chapter35), 555)
        first = self.chapter35[0]
        self.assertEqual(first["observed_designation"], "ADM1")
        self.assertEqual(first["observed_edition"], "2015")
        self.assertEqual(first["observed_designation_with_edition"], "ADM1—2015")

    def test_chapter35_parser_handles_referenced_sections(self) -> None:
        pages = {page: () for page in range(1, SOURCE_PAGE_COUNT + 1)}
        pages[640] = (
            line(640, "AA", 100, 60, 80),
            line(640, "ADM1—2015: Synthetic short title", 120, 60, 410),
            line(640, "1604.3.5, 2002.1", 140, 430, 550),
        )
        result = inventory_chapter35(pages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["referenced_ibc_sections"], ["1604.3.5", "2002.1"])
        self.assertEqual(result[0]["promulgating_agency"], "AA")

    def test_external_family_normalization_preserves_alias_inputs(self) -> None:
        rows = [dict(self.chapter35[0]), dict(self.chapter35[0])]
        rows[1]["id"] = stable_id("chapter35-row", "alias")
        rows[1]["observed_designation_with_edition"] = "ADM1—2015A"
        families = normalize_external_families(rows)
        self.assertEqual(len(families), 1)
        self.assertEqual(len(families[0]["observed_designations"]), 2)

    def test_internal_reference_resolution_states_are_explicit(self) -> None:
        states = {item["resolution_state"] for item in self.crossrefs}
        self.assertEqual(states, {"resolved", "ambiguous", "unresolved", "nonexistent"})
        self.assertEqual(
            sum(self.coverage["internal_reference_resolution"].values()),
            len(self.crossrefs),
        )

    def test_cross_reference_parser_preserves_raw_and_resolved_targets(self) -> None:
        pages = {page: () for page in range(1, SOURCE_PAGE_COUNT + 1)}
        pages[28] = (
            line(28, "101.2 Scope.", 100),
            line(28, "See Section 101.2 and Table 307.1(1).", 130),
        )
        tables = [{"published_identifier": "307.1(1)"}]
        records = inventory_cross_references(pages, tables, (), ())
        self.assertEqual(len(records), 2)
        self.assertEqual({item["resolution_state"] for item in records}, {"resolved"})
        self.assertTrue(all(item["raw_citation"] for item in records))

    def test_incidental_layout_broad_and_strict_counts(self) -> None:
        self.assertEqual(sum(item["broad_classification"] for item in self.incidental), 12)
        self.assertEqual(sum(item["strict_classification"] for item in self.incidental), 4)

    def test_incidental_layout_negative_page_columns(self) -> None:
        pages = {page: () for page in range(1, SOURCE_PAGE_COUNT + 1)}
        pages[100] = tuple(
            line(100, f"ordinary prose line {index}", 100 + index * 18, 60 if index % 2 == 0 else 330, 280 if index % 2 == 0 else 550)
            for index in range(12)
        )
        self.assertEqual(inventory_incidental_layouts(pages, (), ()), [])

    def test_geometry_fixtures_have_positive_negative_and_disputed_cases(self) -> None:
        fixtures = json.loads((ROOT / "fixtures/ibc2018/geometry-fixtures.json").read_text())
        self.assertGreaterEqual(len(fixtures["positive"]), 10)
        self.assertGreaterEqual(len(fixtures["negative"]), 9)
        self.assertEqual(len(fixtures["disputed"]), 1)
        rotated = next(item for item in fixtures["positive"] if item["fixture_id"] == "positive-rotated-content-table")
        self.assertIn("nonhorizontal", rotated["reason"])

    def test_semantic_pilot_covers_required_chapters_and_record_types(self) -> None:
        chapters = {item["chapter"] for item in self.pilot}
        self.assertTrue({"3", "5", "6", "7", "10", "11", "16", "17", "35"}.issubset(chapters))
        types = {item["source_record_type"] for item in self.pilot}
        self.assertTrue({"table", "figure", "equation", "chapter35_referenced_standard_entry"}.issubset(types))

    def test_semantic_pilot_reports_structural_feature_coverage_without_semantic_promotion(self) -> None:
        required = {
            "hierarchical_or_merged_headers",
            "multi_page_continuation",
            "dimensional_units",
            "footnotes_or_notes",
            "nearby_exception_relationship",
            "displayed_formula",
            "internal_cross_reference",
            "external_standard_relationship",
            "chapter_specific_terminology",
            "table_to_prose_applicability_anchor",
            "figure_to_prose_relationship",
        }
        observed = {feature for item in self.pilot for feature in item["structural_verification"]["features"]}
        self.assertTrue(required.issubset(observed))
        self.assertTrue(all(item["structural_verification"]["source_anchor_verified"] for item in self.pilot))
        self.assertTrue(all(not item["structural_verification"]["semantic_interpretation_verified"] for item in self.pilot))

    def test_correction_history_preserves_prior_assertions(self) -> None:
        corrections = self.corpus_manifest["correction_history"]
        self.assertEqual(len(corrections), 4)
        self.assertTrue(all("prior_assertion" in item and "corrected_value" in item for item in corrections))

    def test_source_and_corpus_schemas_parse(self) -> None:
        for name in (
            "ibc-2018-source-manifest.schema.json",
            "ibc-2018-corpus-manifest.schema.json",
            "ibc-2018-inventory-record.schema.json",
        ):
            payload = json.loads((ROOT / "schemas" / name).read_text())
            self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
        inventory_schema = json.loads((ROOT / "schemas" / "ibc-2018-inventory-record.schema.json").read_text())
        self.assertIn("vector_graphic_region_detection", inventory_schema["properties"]["record_type"]["enum"])

    def test_serialization_is_stable(self) -> None:
        path = CORPUS / "ibc-2018-table-inventory.json"
        payload = json.loads(path.read_text())
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.assertEqual(rendered, path.read_text())

    def test_validator_reports_zero_discrepancies(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "validate_ibc_2018_corpus", ROOT / "tools/validate_ibc_2018_corpus.py"
        )
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        report = module.validate(CORPUS)
        self.assertTrue(report["valid"])
        self.assertEqual(report["discrepancies"], [])
        self.assertEqual(report["actual_counts"]["vector_regions"], 705)

    def test_validate_inventory_reports_duplicate_item_level_error(self) -> None:
        manifest = build_source_manifest(
            pdf_metadata={}, ingestion_timestamp="2026-08-03T19:30:00Z", parser_version="test"
        )
        record = {"id": stable_id("table", "duplicate"), "record_type": "table"}
        errors = validate_inventory(manifest, {"tables": [record, dict(record)]})
        self.assertTrue(any(item["code"] == "duplicate-logical-structure" for item in errors))

    def test_table_footnote_attachment_is_source_anchored(self) -> None:
        table = next(item for item in self.tables if item["published_identifier"] == "307.1(1)")
        self.assertTrue(table["footnotes"])
        self.assertTrue(all(item["observed_text_sha256"] for item in table["footnotes"]))

    def test_reference_crosschecks_are_source_safe(self) -> None:
        checks = json.loads((CORPUS / "ibc-2018-reference-crosschecks.json").read_text())
        self.assertEqual(len(checks["chapter35_families_not_detected_elsewhere"]), 163)
        self.assertEqual(len(checks["citation_occurrences_without_chapter35_match"]), 53)
        self.assertEqual(checks["external_alias_reconciliation"]["newly_matched_count"], 581)
        self.assertEqual(checks["external_alias_reconciliation"]["policy"], "unique normalized aliases only; no fuzzy or semantic matching")
        self.assertNotIn("source_text", json.dumps(checks))


if __name__ == "__main__":
    unittest.main()
