from __future__ import annotations

import unittest

from building_code_ast import DocumentSourceArtifact
from building_code_ast.ingest.pdf_layout import PdfBlock
from building_code_ast.ingest.tms402_16_source_roles import (
    TMS402_AUTHORITY_POLICY,
    Tms402AuthorityPolicy,
    Tms402PageLayout,
    Tms402RecoveredRegion,
    Tms402SourceRole,
    produce_tms402_16_observations,
)


ARTIFACT = DocumentSourceArtifact(
    artifact_id="sha256:947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d",
    edition_id="2016-second-printing-errata-2018-10-22",
    publication_component_id="tms-402-16",
)


def _region(
    *,
    page: int = 67,
    x0: float = 72.0,
    x1: float = 280.0,
    y0: float = 100.0,
    y1: float = 118.0,
    layout: Tms402PageLayout = Tms402PageLayout.PARALLEL_CODE_COMMENTARY,
    recovery_origin: str = "ocr:test-fixture",
) -> Tms402RecoveredRegion:
    return Tms402RecoveredRegion(
        block=PdfBlock(
            page_number=page,
            bbox=(x0, y0, x1, y1),
            text="Synthetic source-safe observation.",
            block_number=1,
        ),
        printed_page="C-1" if page == 67 else None,
        text_origin="ocr",
        recovery_origin=recovery_origin,
        page_layout=layout,
    )


class Tms402SourceRoleProducerTests(unittest.TestCase):
    def test_parallel_regions_produce_normative_and_commentary_observations(self) -> None:
        production = produce_tms402_16_observations(
            [
                _region(x0=72.0, x1=280.0),
                _region(x0=332.0, x1=540.0),
            ],
            source_artifact=ARTIFACT,
        )

        self.assertEqual(
            [item.source_role for item in production.classified_regions],
            [Tms402SourceRole.NORMATIVE, Tms402SourceRole.COMMENTARY],
        )
        self.assertEqual(
            [item.recovery_origin for item in production.classified_regions],
            ["ocr:test-fixture", "ocr:test-fixture"],
        )
        self.assertEqual(
            [observation.source_role for observation in production.observations],
            ["normative", "commentary"],
        )
        self.assertEqual(production.observations[0].text_origin, "ocr")
        self.assertEqual(production.observations[0].block.bbox, (72.0, 100.0, 280.0, 118.0))
        self.assertEqual(production.observations[0].block.page_number, 67)

    def test_authority_boundary_is_publication_policy_not_recovery_semantics(self) -> None:
        policy = Tms402AuthorityPolicy(
            first_component_page=TMS402_AUTHORITY_POLICY.first_component_page,
            first_code_page=TMS402_AUTHORITY_POLICY.first_code_page,
            last_component_page=TMS402_AUTHORITY_POLICY.last_component_page,
            top_content_y=TMS402_AUTHORITY_POLICY.top_content_y,
            bottom_content_y=TMS402_AUTHORITY_POLICY.bottom_content_y,
            code_commentary_boundary_x=250.0,
        )
        production = produce_tms402_16_observations(
            [_region(x0=240.0, x1=260.0)],
            source_artifact=ARTIFACT,
            authority_policy=policy,
        )

        self.assertEqual(
            production.classified_regions[0].source_role,
            Tms402SourceRole.AMBIGUOUS,
        )
        self.assertIn("publication policy", production.classified_regions[0].role_evidence)

    def test_crossing_authority_boundary_remains_explicitly_ambiguous(self) -> None:
        production = produce_tms402_16_observations(
            [_region(x0=280.0, x1=332.0)],
            source_artifact=ARTIFACT,
        )

        self.assertEqual(
            production.classified_regions[0].source_role,
            Tms402SourceRole.AMBIGUOUS,
        )
        self.assertIn("boundary", production.classified_regions[0].role_evidence)
        self.assertEqual(production.observations, ())
        self.assertEqual(len(production.ambiguous_regions), 1)

    def test_front_matter_and_unsupported_layout_fail_closed(self) -> None:
        production = produce_tms402_16_observations(
            [
                _region(page=60, x0=72.0, x1=280.0),
                _region(
                    page=310,
                    x0=72.0,
                    x1=280.0,
                    layout=Tms402PageLayout.UNSUPPORTED,
                ),
            ],
            source_artifact=ARTIFACT,
        )

        self.assertEqual(
            [item.source_role for item in production.classified_regions],
            [Tms402SourceRole.AMBIGUOUS, Tms402SourceRole.AMBIGUOUS],
        )
        self.assertEqual(production.observations, ())

    def test_header_and_footer_regions_fail_closed(self) -> None:
        production = produce_tms402_16_observations(
            [
                _region(y0=20.0, y1=40.0),
                _region(y0=760.0, y1=780.0),
            ],
            source_artifact=ARTIFACT,
        )

        self.assertEqual(
            [item.source_role for item in production.classified_regions],
            [Tms402SourceRole.AMBIGUOUS, Tms402SourceRole.AMBIGUOUS],
        )
        self.assertTrue(
            all("body" in item.role_evidence for item in production.classified_regions)
        )
        self.assertEqual(production.observations, ())

    def test_rejects_regions_outside_canonical_tms402_extent(self) -> None:
        for page in (56, 321):
            with self.subTest(page=page):
                with self.assertRaisesRegex(ValueError, "pages 57-320"):
                    produce_tms402_16_observations(
                        [_region(page=page)],
                        source_artifact=ARTIFACT,
                    )

    def test_rejects_wrong_exact_source_identity(self) -> None:
        wrong = DocumentSourceArtifact(
            artifact_id="sha256:" + "0" * 64,
            edition_id=ARTIFACT.edition_id,
            publication_component_id="tms-402-16",
        )
        with self.assertRaisesRegex(ValueError, "exact retained TMS 402/602-16 artifact"):
            produce_tms402_16_observations(
                [_region()],
                source_artifact=wrong,
            )

    def test_requires_explicit_recovery_origin(self) -> None:
        with self.assertRaisesRegex(ValueError, "recovery origin"):
            _region(recovery_origin="  ")


if __name__ == "__main__":
    unittest.main()
