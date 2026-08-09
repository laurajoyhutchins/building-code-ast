from __future__ import annotations

import unittest

from building_code_ast.retrieval import SourceArtifactIdentity, SourceEvidence
from building_code_ast.retrieval.structural import annotate_structural_metadata


class SourceStructuralMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = SourceArtifactIdentity(
            source_id="synthetic:standard:2026",
            publication_key="synthetic-2026",
            sha256="a" * 64,
            size=1234,
            page_count=1,
        )

    def _evidence(self, text: str, *, bbox=(72.0, 100.0, 540.0, 120.0)) -> SourceEvidence:
        return SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=1,
            block_index=2,
            text=text,
            bbox=bbox,
            extraction_method="synthetic/1",
            observed_metadata={"source.layer": "text"},
            derived_metadata={"existing.flag": True},
        )

    def test_geometry_and_font_observations_remain_separate_from_derived_features(self) -> None:
        evidence = self._evidence("SYNTHETIC HEADING")
        enriched = annotate_structural_metadata(
            evidence,
            page_width=612.0,
            page_height=792.0,
            font_size=14.0,
            body_font_size=10.0,
            font_name="SyntheticSans-Bold",
        )

        observed = dict(enriched.observed_metadata)
        derived = dict(enriched.derived_metadata)
        self.assertEqual(observed["source.layer"], "text")
        self.assertEqual(observed["layout.page_width"], 612.0)
        self.assertEqual(observed["layout.page_height"], 792.0)
        self.assertEqual(observed["layout.bbox_width"], 468.0)
        self.assertEqual(observed["font.size"], 14.0)
        self.assertEqual(observed["font.name"], "SyntheticSans-Bold")
        self.assertEqual(derived["font.relative_size"], 1.4)
        self.assertEqual(derived["candidate.heading"], True)
        self.assertEqual(derived["existing.flag"], True)
        self.assertNotIn("requirement", str(derived))
        self.assertEqual(enriched.evidence_id, evidence.evidence_id)

    def test_structural_candidates_are_publication_neutral_and_identity_neutral(self) -> None:
        cases = {
            "Table 8.2-1 Synthetic values": "candidate.table",
            "Figure 4-2 Synthetic diagram": "candidate.figure",
            "Equation 8.2-1 synthetic expression": "candidate.equation",
        }
        for text, key in cases.items():
            with self.subTest(text=text):
                evidence = self._evidence(text)
                enriched = annotate_structural_metadata(
                    evidence,
                    page_width=612.0,
                    page_height=792.0,
                )
                self.assertEqual(dict(enriched.derived_metadata)[key], True)
                self.assertEqual(enriched.evidence_id, evidence.evidence_id)

    def test_short_all_caps_text_can_be_heading_candidate_without_font_data(self) -> None:
        enriched = annotate_structural_metadata(
            self._evidence("GENERAL REQUIREMENTS"),
            page_width=612.0,
            page_height=792.0,
        )
        self.assertEqual(dict(enriched.derived_metadata)["candidate.heading"], True)

    def test_equation_candidate_requires_explicit_equation_shape_not_arbitrary_equals_prose(self) -> None:
        prose = annotate_structural_metadata(
            self._evidence("The synthetic comparison states a = b for discussion only."),
            page_width=612.0,
            page_height=792.0,
        )
        self.assertNotIn("candidate.equation", dict(prose.derived_metadata))

    def test_invalid_page_geometry_font_values_and_metadata_collisions_fail_closed(self) -> None:
        evidence = self._evidence("Synthetic text")
        with self.assertRaisesRegex(ValueError, "page_width"):
            annotate_structural_metadata(evidence, page_width=0.0, page_height=792.0)
        with self.assertRaisesRegex(ValueError, "font_size"):
            annotate_structural_metadata(
                evidence,
                page_width=612.0,
                page_height=792.0,
                font_size=-1.0,
            )
        conflicting = SourceEvidence.create(
            artifact=self.artifact,
            pdf_page=1,
            block_index=3,
            text="Synthetic text",
            bbox=(72.0, 100.0, 540.0, 120.0),
            extraction_method="synthetic/1",
            observed_metadata={"layout.page_width": 999.0},
        )
        with self.assertRaisesRegex(ValueError, "metadata conflict"):
            annotate_structural_metadata(
                conflicting,
                page_width=612.0,
                page_height=792.0,
            )


if __name__ == "__main__":
    unittest.main()
