from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import unittest

from building_code_ast.document_model import (
    DocumentAst,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from building_code_ast.model import SourceSpan
from building_code_ast.source_text import (
    SourceTextBundle,
    bundle_from_document_seed,
)


@dataclass(frozen=True)
class FakeManifest:
    artifact_id: str = "example:code"
    edition_id: str = "2026:synthetic"
    sha256: str = "a" * 64
    size_bytes: int = 1234
    extractor_id: str = "synthetic-extractor"
    extractor_version: str = "1"


@dataclass(frozen=True)
class FakeMapEntry:
    normalized_start: int
    normalized_end: int
    normalized_text: str
    page_number: int

    def to_dict(self) -> dict[str, object]:
        return {
            "normalized_span": {
                "start": self.normalized_start,
                "end": self.normalized_end,
                "text": self.normalized_text,
            },
            "page_number": self.page_number,
            "source_kind": "synthetic",
        }


@dataclass(frozen=True)
class FakeSeed:
    source_manifest: FakeManifest
    source_map: tuple[FakeMapEntry, ...]
    document_ast: DocumentAst


def _seed() -> FakeSeed:
    text = "101.1 Scope.\n\nSynthetic requirement."
    artifact = DocumentSourceArtifact("example:code", "2026:synthetic")
    heading_end = len("101.1 Scope.")
    section = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.SECTION,
        locator="101.1",
        span=SourceSpan(0, len(text), text),
        label="101.1 Scope.",
        children=(
            make_document_node(
                source_artifact=artifact,
                node_type=DocumentNodeType.PARAGRAPH,
                locator="101.1/p1",
                span=SourceSpan(
                    heading_end + 2,
                    len(text),
                    text[heading_end + 2 :],
                ),
            ),
        ),
    )
    root = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator="document",
        span=SourceSpan(0, len(text), text),
        children=(section,),
    )
    ast = DocumentAst(source_text=text, source_artifact=artifact, root=root)
    return FakeSeed(
        source_manifest=FakeManifest(),
        source_map=(
            FakeMapEntry(0, heading_end, text[:heading_end], 1),
            FakeMapEntry(heading_end + 2, len(text), text[heading_end + 2 :], 1),
        ),
        document_ast=ast,
    )


class SourceTextTests(unittest.TestCase):
    def test_seed_projection_round_trips_text_index_and_provenance(self) -> None:
        bundle = bundle_from_document_seed(_seed())

        self.assertEqual(bundle.schema, "source-text/v1")
        self.assertNotEqual(bundle.text_sha256, bundle.bundle_sha256)
        self.assertEqual(bundle.get("101.1").text, bundle.canonical_text)
        paragraph = bundle.get("101.1/p1")
        self.assertEqual(paragraph.text, "Synthetic requirement.")
        self.assertEqual(paragraph.fragments[0].provenance["page_number"], 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source-text.json"
            bundle.save(path)
            loaded = SourceTextBundle.load(path)
        self.assertEqual(loaded, bundle)
        self.assertEqual(loaded.get("101.1/p1").text, "Synthetic requirement.")

    def test_bundle_load_fails_closed_on_text_tampering(self) -> None:
        bundle = bundle_from_document_seed(_seed())
        payload = bundle.to_dict()
        payload["canonical_text"] = "tampered"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical text hash mismatch"):
                SourceTextBundle.load(path)

    def test_bundle_load_fails_closed_on_provenance_tampering(self) -> None:
        bundle = bundle_from_document_seed(_seed())
        payload = bundle.to_dict()
        payload["fragments"][0]["provenance"]["page_number"] = 99
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered-provenance.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bundle hash mismatch"):
                SourceTextBundle.load(path)

    def test_bundle_load_fails_closed_on_source_identity_tampering(self) -> None:
        bundle = bundle_from_document_seed(_seed())
        payload = bundle.to_dict()
        payload["identity"]["source_sha256"] = "b" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered-identity.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bundle hash mismatch"):
                SourceTextBundle.load(path)


if __name__ == "__main__":
    unittest.main()
