from __future__ import annotations

import json
from pathlib import Path

import pytest

from building_code_ast.ingest.local_runner import (
    prepare_output_dir,
    source_digest,
    write_json,
    write_manifest,
)


def test_source_digest_reports_exact_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"source-safe-fixture\n")

    digest, size = source_digest(source)

    assert digest == "1433c58a47321c1b7fef9d8be31a5f6f86276ffcf757e954c7e70f817f408603"
    assert size == 20


def test_write_json_is_deterministic_utf8(tmp_path: Path) -> None:
    output = tmp_path / "record.json"

    write_json(output, {"z": "caf\u00e9", "a": [2, 1]})

    assert output.read_bytes() == b'{\n  "a": [\n    2,\n    1\n  ],\n  "z": "caf\xc3\xa9"\n}\n'


def test_prepare_output_dir_replaces_only_recognized_generated_files(tmp_path: Path) -> None:
    output = tmp_path / "generated"
    output.mkdir()
    (output / "manifest.json").write_text("{}\n", encoding="utf-8")
    (output / "article-90.json").write_text("{}\n", encoding="utf-8")

    prepare_output_dir(
        output,
        force=True,
        generated_name_pattern=r"article-\d+\.json",
    )

    assert list(output.iterdir()) == []


def test_prepare_output_dir_fails_closed_on_unexpected_content(tmp_path: Path) -> None:
    output = tmp_path / "generated"
    output.mkdir()
    protected = output / "notes.txt"
    protected.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="unexpected entries"):
        prepare_output_dir(
            output,
            force=True,
            generated_name_pattern=r"chapter-\d+\.json",
        )

    assert protected.read_text(encoding="utf-8") == "keep"


def test_write_manifest_preserves_common_output_order(tmp_path: Path) -> None:
    generated = tmp_path / "article-90.json"
    write_json(generated, {"number": "90"})

    paths = write_manifest(
        tmp_path,
        {"publication_boundary": "private-local-output", "articles": [{"file": generated.name}]},
        [generated],
    )

    assert paths == (tmp_path / "manifest.json", generated)
    assert json.loads(paths[0].read_text(encoding="utf-8"))["publication_boundary"] == "private-local-output"
