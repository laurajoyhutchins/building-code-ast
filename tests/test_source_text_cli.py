from __future__ import annotations

import json

from building_code_ast.source_text import (
    SourceTextFragment,
    SourceTextIdentity,
    SourceTextIndexEntry,
    build_source_text_bundle,
)
from building_code_ast.source_text_cli import main


def _write_bundle(tmp_path):
    text = "101.1 Scope.\n\nSynthetic requirement."
    identity = SourceTextIdentity(
        artifact_id="example:code",
        edition_id="2026:synthetic",
        source_sha256="a" * 64,
        source_size_bytes=1234,
        extractor_id="synthetic-extractor",
        extractor_version="1",
        projection_id="synthetic-projection",
        projection_version="1",
    )
    bundle = build_source_text_bundle(
        identity=identity,
        canonical_text=text,
        fragments=(
            SourceTextFragment(
                0,
                len(text),
                text,
                {"page_number": 1, "source_kind": "synthetic"},
            ),
        ),
        index=(
            SourceTextIndexEntry("101.1", "docnode:synthetic", 0, len(text)),
        ),
    )
    path = tmp_path / "source-text.json"
    bundle.save(path)
    return path, bundle


def test_text_get_loads_persisted_bundle_without_pdf_pipeline(tmp_path, capsys) -> None:
    path, bundle = _write_bundle(tmp_path)

    assert main(["get", str(path), "101.1", "--compact"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["command"] == "text.get"
    assert payload["text"] == bundle.canonical_text
    assert payload["provenance"][0]["provenance"]["page_number"] == 1
    assert payload["bundle_sha256"] == bundle.bundle_sha256


def test_text_status_validates_and_summarizes_bundle(tmp_path, capsys) -> None:
    path, bundle = _write_bundle(tmp_path)

    assert main(["status", str(path), "--compact"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "bundle_sha256": bundle.bundle_sha256,
        "canonical_text_bytes": len(bundle.canonical_text.encode("utf-8")),
        "command": "text.status",
        "diagnostic_count": 0,
        "fragment_count": 1,
        "identity": bundle.identity.to_dict(),
        "index_count": 1,
        "schema": "source-text/v1",
        "text_sha256": bundle.text_sha256,
    }
