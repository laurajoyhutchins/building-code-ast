from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
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
    SOURCE_TEXT_VERSION,
    SourceTextFragment,
    SourceTextProvenance,
    load_source_text_bundle,
    lookup_source_text,
    make_source_text_bundle,
    validate_source_text_bundle,
    write_source_text_bundle,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle():
    first = "110.1 Scope."
    second = "Equipment shall be installed."
    text = first + "\n\n" + second
    artifact = DocumentSourceArtifact("synthetic-nec", "2017-test")
    first_span = SourceSpan(0, len(first), first)
    second_start = len(first) + 2
    second_span = SourceSpan(second_start, len(text), second)
    first_node = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.SECTION,
        locator="110.1",
        span=first_span,
        label="110.1 Scope.",
    )
    second_node = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.PARAGRAPH,
        locator="110.1/p:1",
        span=second_span,
    )
    root = make_document_node(
        source_artifact=artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator="document:test",
        span=SourceSpan(0, len(text), text),
        children=(first_node, second_node),
    )
    document = DocumentAst(source_text=text, source_artifact=artifact, root=root)
    fragments = (
        SourceTextFragment(
            start=0,
            end=len(first),
            text_sha256=_sha(first),
            provenance=(SourceTextProvenance(4, (10.0, 20.0, 200.0, 40.0), "block:1"),),
        ),
        SourceTextFragment(
            start=second_start,
            end=len(text),
            text_sha256=_sha(second),
            provenance=(SourceTextProvenance(5, (10.0, 50.0, 300.0, 70.0), "block:2"),),
        ),
    )
    return make_source_text_bundle(
        source_artifact=artifact,
        source_sha256="a" * 64,
        source_size=1234,
        extractor_id="synthetic-extractor",
        extractor_version="1",
        projection_id="synthetic-projection",
        projection_version="1",
        canonical_text=text,
        fragments=fragments,
        document_ast=document,
    )


class SourceTextBundleTests(unittest.TestCase):
    def test_contract_round_trips_and_resolves_structural_locator(self) -> None:
        bundle = _bundle()
        self.assertEqual(bundle.version, SOURCE_TEXT_VERSION)
        self.assertEqual(bundle.text_sha256, _sha(bundle.canonical_text))
        self.assertEqual([item.locator for item in bundle.sections], ["document:test", "110.1", "110.1/p:1"])
        result = lookup_source_text(bundle, "110.1")
        self.assertEqual(result.text, "110.1 Scope.")
        self.assertEqual(result.section.first_page, 4)
        self.assertEqual(result.section.last_page, 4)
        self.assertEqual(result.section.parent_locator, "document:test")
        self.assertEqual(result.provenance[0].observation_id, "block:1")

    def test_private_serialization_is_deterministic_and_pdf_free(self) -> None:
        bundle = _bundle()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = write_source_text_bundle(root / "left", bundle)
            right = write_source_text_bundle(root / "right", bundle)
            names = ("manifest.json", "document.txt", "fragments.jsonl", "sections.jsonl", "diagnostics.jsonl")
            for name in names:
                self.assertEqual((left / name).read_bytes(), (right / name).read_bytes())
            loaded = load_source_text_bundle(
                left,
                expected_source_sha256="a" * 64,
                expected_source_size=1234,
                expected_artifact_id="synthetic-nec",
                expected_edition_id="2017-test",
            )
            self.assertEqual(loaded, bundle)

    def test_component_tampering_fails_before_lookup(self) -> None:
        bundle = _bundle()
        with tempfile.TemporaryDirectory() as temporary:
            path = write_source_text_bundle(Path(temporary) / "bundle", bundle)
            (path / "document.txt").write_text(bundle.canonical_text + "x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "component hash/size mismatch"):
                load_source_text_bundle(path)

    def test_fragment_metadata_tampering_fails_closed(self) -> None:
        bundle = _bundle()
        with tempfile.TemporaryDirectory() as temporary:
            path = write_source_text_bundle(Path(temporary) / "bundle", bundle)
            fragment_path = path / "fragments.jsonl"
            payloads = [json.loads(line) for line in fragment_path.read_text(encoding="utf-8").splitlines()]
            payloads[0]["fragment_id"] = "sourcefrag:" + "0" * 64
            replacement = "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in payloads) + "\n"
            fragment_path.write_text(replacement, encoding="utf-8")
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            manifest["components"]["fragments.jsonl"]["sha256"] = hashlib.sha256(replacement.encode()).hexdigest()
            manifest["components"]["fragments.jsonl"]["size"] = len(replacement.encode())
            manifest_without_hash = dict(manifest)
            manifest_without_hash.pop("bundle_sha256")
            manifest["bundle_sha256"] = hashlib.sha256(
                json.dumps(manifest_without_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            (path / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fragment ID"):
                load_source_text_bundle(path)

    def test_lookup_cli_import_does_not_pull_pdf_stack(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import building_code_ast.source_text_cli; "
                "assert 'fitz' not in sys.modules; assert 'pymupdf' not in sys.modules",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_wrong_source_identity_fails_closed(self) -> None:
        bundle = _bundle()
        validate_source_text_bundle(bundle)
        with tempfile.TemporaryDirectory() as temporary:
            path = write_source_text_bundle(Path(temporary) / "bundle", bundle)
            with self.assertRaisesRegex(ValueError, "source SHA-256"):
                load_source_text_bundle(path, expected_source_sha256="b" * 64)


if __name__ == "__main__":
    unittest.main()
