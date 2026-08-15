from __future__ import annotations

import unittest

from building_code_ast.evidence import AstSourceIdentity
from building_code_ast.ingest.nds2018_layout import (
    NDS_2018_ARTIFACT_ID,
    NDS_2018_EDITION_ID,
    NdsPageRole,
    analyze_nds2018_pages,
    build_nds2018_layout_evidence,
    nds2018_page_role,
    nds2018_printed_page,
)
from building_code_ast.ingest.pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfLine,
    PdfOutlineItem,
    PdfPage,
    PdfSpan,
)


def _block(page: int, bbox: tuple[float, float, float, float], text: str, number: int) -> PdfBlock:
    return PdfBlock(page_number=page, bbox=bbox, text=text, block_number=number)


def _mixed_page(page: int, *, reverse: bool = False) -> PdfPage:
    blocks = [
        _block(page, (170.0, 6.0, 442.0, 18.0), "SYNTHETIC RUNNING HEADER", 1),
        _block(page, (580.0, 120.0, 598.0, 300.0), "SIDE LABEL", 2),
        _block(page, (45.0, 100.0, 270.0, 120.0), "left upper", 3),
        _block(page, (330.0, 100.0, 555.0, 120.0), "right upper", 4),
        _block(page, (80.0, 245.0, 530.0, 265.0), "full width interruption", 5),
        _block(page, (45.0, 300.0, 270.0, 320.0), "left lower", 6),
        _block(page, (330.0, 300.0, 555.0, 320.0), "right lower", 7),
        _block(page, (72.0, 736.0, 533.0, 751.0), "SYNTHETIC ARTIFACT FOOTER", 8),
    ]
    if reverse:
        blocks.reverse()
    return PdfPage(page_number=page, width=612.0, height=783.0, blocks=tuple(blocks))


class Nds2018LayoutTests(unittest.TestCase):
    def test_printed_page_mapping_and_page_roles_are_exact_at_boundaries(self) -> None:
        expected = {
            1: (None, NdsPageRole.FRONT_UNNUMBERED),
            3: (None, NdsPageRole.FRONT_UNNUMBERED),
            4: ("ii", NdsPageRole.FRONT_MATTER),
            12: ("x", NdsPageRole.FRONT_MATTER),
            13: ("1", NdsPageRole.NUMBERED_BODY),
            204: ("192", NdsPageRole.NUMBERED_BODY),
            205: (None, NdsPageRole.TRAILING_MATTER),
            206: (None, NdsPageRole.TRAILING_MATTER),
        }
        for page, (printed, role) in expected.items():
            with self.subTest(page=page):
                self.assertEqual(nds2018_printed_page(page), printed)
                self.assertEqual(nds2018_page_role(page), role)

        for invalid in (0, 207):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "outside NDS 2018"):
                    nds2018_page_role(invalid)

    def test_recurring_furniture_is_removed_with_provenance_and_mixed_order_is_stable(self) -> None:
        pages = tuple(_mixed_page(page) for page in range(13, 17))
        reversed_pages = tuple(_mixed_page(page, reverse=True) for page in range(13, 17))

        first = analyze_nds2018_pages(pages)
        repeated = analyze_nds2018_pages(reversed_pages)

        self.assertEqual(
            [page.to_dict() for page in first],
            [page.to_dict() for page in repeated],
        )
        for page in first:
            self.assertEqual(page.printed_page, str(page.page_number - 12))
            self.assertEqual(page.page_role, NdsPageRole.NUMBERED_BODY)
            self.assertEqual(
                [block.text for block in page.ordered_blocks],
                [
                    "left upper",
                    "right upper",
                    "full width interruption",
                    "left lower",
                    "right lower",
                ],
            )
            self.assertEqual(
                {removed.reason for removed in page.removed_blocks},
                {
                    "recurring_top_furniture",
                    "recurring_right_furniture",
                    "recurring_bottom_furniture",
                },
            )
            for removed in page.removed_blocks:
                self.assertEqual(removed.block.page_number, page.page_number)
                self.assertEqual(len(removed.block.bbox), 4)

    def test_exact_duplicate_blocks_are_removed_without_collapsing_distinct_line_evidence(self) -> None:
        bbox = (100.0, 100.0, 200.0, 120.0)
        exact_line = PdfLine(
            bbox=bbox,
            spans=(PdfSpan(bbox=bbox, text="Exact duplicate", font="Font A", size=10.0, flags=0),),
        )
        distinct_line = PdfLine(
            bbox=bbox,
            spans=(PdfSpan(bbox=bbox, text="Exact duplicate", font="Font B", size=10.0, flags=0),),
        )
        page = PdfPage(
            page_number=13,
            width=612.0,
            height=783.0,
            blocks=(
                PdfBlock(13, bbox, "Exact duplicate", 9, lines=(exact_line,)),
                PdfBlock(13, bbox, "Exact duplicate", 4, lines=(exact_line,)),
                PdfBlock(13, bbox, "Exact duplicate", 11, lines=(distinct_line,)),
                PdfBlock(13, bbox, "Distinct evidence", 12),
            ),
        )

        analyzed = analyze_nds2018_pages((page,))[0]

        self.assertEqual(
            [(removed.block.block_number, removed.reason) for removed in analyzed.removed_blocks],
            [(9, "exact_duplicate_extraction")],
        )
        self.assertEqual(
            {(block.block_number, block.text) for block in analyzed.ordered_blocks},
            {
                (4, "Exact duplicate"),
                (11, "Exact duplicate"),
                (12, "Distinct evidence"),
            },
        )

    def test_complete_layout_evidence_is_exact_identity_and_geometry_gated(self) -> None:
        pages = tuple(
            PdfPage(
                page_number=page,
                width=612.0,
                height=783.0,
                blocks=(
                    _block(page, (60.0, 100.0, 250.0, 120.0), f"synthetic page {page}", 1),
                ),
            )
            for page in range(1, 207)
        )
        document = PdfLayoutDocument(
            file_name="any-local-name.pdf",
            pages=pages,
            outline=(PdfOutlineItem(level=3, title="Broken synthetic bookmark", page_number=-1),),
        )
        source = AstSourceIdentity(
            artifact_id=NDS_2018_ARTIFACT_ID,
            edition_id=NDS_2018_EDITION_ID,
        )

        evidence = build_nds2018_layout_evidence(document, ast_source=source)

        self.assertEqual(evidence.page_count, 206)
        self.assertEqual(evidence.ast_source, source)
        self.assertEqual(
            [diagnostic.code for diagnostic in evidence.diagnostics],
            ["nds-outline-target-invalid"],
        )
        self.assertNotIn("chapter", evidence.to_dict())
        self.assertNotIn("section", evidence.to_dict())

        with self.assertRaisesRegex(ValueError, "exact registered source identity"):
            build_nds2018_layout_evidence(
                document,
                ast_source=AstSourceIdentity(
                    artifact_id="awc:nds",
                    edition_id="2018:wrong-copy",
                ),
            )

        bad_geometry = PdfLayoutDocument(
            file_name=document.file_name,
            pages=(PdfPage(1, 611.0, 783.0, pages[0].blocks),) + pages[1:],
            outline=(),
        )
        with self.assertRaisesRegex(ValueError, "612 x 783"):
            build_nds2018_layout_evidence(bad_geometry, ast_source=source)


if __name__ == "__main__":
    unittest.main()
