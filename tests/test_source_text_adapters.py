from __future__ import annotations

from types import SimpleNamespace
import unittest

from building_code_ast.source_text_adapters import (
    IBC_SOURCE_TEXT_PROJECTION_ID,
    NEC_SOURCE_TEXT_PROJECTION_ID,
    source_text_from_ibc_source_map,
    source_text_from_nec_source_map,
)


class SourceTextAdapterTests(unittest.TestCase):
    def manifest(self, *, extractor: str) -> SimpleNamespace:
        return SimpleNamespace(
            artifact_id="source-artifact",
            edition_id="edition-1",
            sha256="c" * 64,
            size_bytes=999,
            extractor_id=extractor,
            extractor_version="7",
        )

    def test_nec_source_map_projects_without_pdf_reconstruction(self) -> None:
        text = "110.1 Scope."
        entry = SimpleNamespace(
            normalized_start=0,
            normalized_end=len(text),
            normalized_text=text,
            page_number=8,
            bbox=(1.0, 2.0, 3.0, 4.0),
            block_number=9,
        )
        bundle = source_text_from_nec_source_map(
            source_manifest=self.manifest(extractor="nec-extractor"),
            canonical_text=text,
            source_map=(entry,),
        )
        self.assertEqual(bundle.projection_id, NEC_SOURCE_TEXT_PROJECTION_ID)
        self.assertEqual(bundle.fragments[0].provenance[0].page_number, 8)
        self.assertEqual(bundle.fragments[0].provenance[0].observation_id, "pdf-block:9")

    def test_ibc_logical_block_projects_multiple_source_fragments(self) -> None:
        text = "101.1 Title."
        source_fragments = (
            SimpleNamespace(page_number=28, bbox=(1.0, 2.0, 3.0, 4.0), block_number=1),
            SimpleNamespace(page_number=28, bbox=(4.0, 2.0, 8.0, 4.0), block_number=2),
        )
        entry = SimpleNamespace(
            normalized_start=0,
            normalized_end=len(text),
            normalized_text=text,
            fragments=source_fragments,
        )
        bundle = source_text_from_ibc_source_map(
            source_manifest=self.manifest(extractor="ibc-extractor"),
            canonical_text=text,
            source_map=(entry,),
        )
        self.assertEqual(bundle.projection_id, IBC_SOURCE_TEXT_PROJECTION_ID)
        self.assertEqual(len(bundle.fragments[0].provenance), 2)
        self.assertEqual(
            [item.observation_id for item in bundle.fragments[0].provenance],
            ["pdf-block:1", "pdf-block:2"],
        )


if __name__ == "__main__":
    unittest.main()
