from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from building_code_ast.ingest.ibc2018.models import (
    CHAPTER_SPECS,
    ChapterLayout,
    IbcLayoutDocument,
    LogicalBlock,
)
from building_code_ast.ingest.ibc2018.projection import build_chapter_seed
from building_code_ast.ingest.layout_analysis import SourceFragment
from building_code_ast.ingest.nec2017 import build_article_seed
from building_code_ast.ingest.pdf_layout import PdfBlock, PdfLayoutDocument, PdfOutlineItem, PdfPage
from building_code_ast.source_text import (
    document_ast_from_source_text,
    load_source_text_bundle,
    write_source_text_bundle,
)
from building_code_ast.source_text_adapters import (
    source_text_from_ibc_chapter_seed,
    source_text_from_nec_article_seed,
)


def _nec_layout() -> PdfLayoutDocument:
    return PdfLayoutDocument(
        file_name="synthetic-nec.pdf",
        outline=(
            PdfOutlineItem(2, "110 Requirements for Electrical Installations", 1),
            PdfOutlineItem(2, "200 Use and Identification", 2),
        ),
        pages=(
            PdfPage(
                page_number=1,
                width=612.0,
                height=792.0,
                blocks=(
                    PdfBlock(1, (54.0, 100.0, 303.0, 130.0), "ARTICLE 110\nRequirements for Electrical Installations"),
                    PdfBlock(1, (54.0, 150.0, 303.0, 190.0), "110.1 Scope. Synthetic retained-source meaning."),
                    PdfBlock(1, (54.0, 200.0, 303.0, 230.0), "Informational Note: Synthetic note."),
                ),
            ),
            PdfPage(
                page_number=2,
                width=612.0,
                height=792.0,
                blocks=(PdfBlock(2, (54.0, 100.0, 303.0, 130.0), "ARTICLE 200\nUse and Identification"),),
            ),
        ),
    )


def _ibc_layout() -> IbcLayoutDocument:
    blocks = (
        LogicalBlock(
            "CHAPTER 1 SCOPE AND ADMINISTRATION",
            (SourceFragment(28, (54.0, 90.0, 400.0, 112.0), 1, "CHAPTER 1 SCOPE AND ADMINISTRATION"),),
        ),
        LogicalBlock(
            "SECTION 101 GENERAL",
            (SourceFragment(28, (54.0, 130.0, 300.0, 150.0), 2, "SECTION 101 GENERAL"),),
        ),
        LogicalBlock(
            "101.1 Title. Synthetic IBC text.",
            (SourceFragment(28, (54.0, 160.0, 400.0, 184.0), 3, "101.1 Title. Synthetic IBC text."),),
        ),
    )
    return IbcLayoutDocument(
        file_name="synthetic-ibc.pdf",
        page_count=100,
        chapters=(ChapterLayout(CHAPTER_SPECS["1"], blocks),),
    )


class SourceTextProducerEquivalenceTests(unittest.TestCase):
    def _round_trip(self, bundle, expected_document) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            written = write_source_text_bundle(Path(temporary) / "source-text", bundle)
            loaded = load_source_text_bundle(written)
            rebuilt = document_ast_from_source_text(loaded)
        self.assertEqual(rebuilt.to_dict(), expected_document.to_dict())

    def test_nec_document_ast_is_recoverable_from_persisted_generic_ir(self) -> None:
        seed = build_article_seed(_nec_layout(), "110", source_sha256="a" * 64, source_size=1234)
        bundle = source_text_from_nec_article_seed(seed)
        self._round_trip(bundle, seed.document_ast)

    def test_ibc_document_ast_is_recoverable_from_same_persisted_contract(self) -> None:
        seed = build_chapter_seed(_ibc_layout(), "1", source_sha256="b" * 64, source_size=5678)
        bundle = source_text_from_ibc_chapter_seed(seed)
        self._round_trip(bundle, seed.document_ast)


if __name__ == "__main__":
    unittest.main()
