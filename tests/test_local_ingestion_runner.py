from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from building_code_ast.ingest.local_runner import (
    prepare_output_dir,
    source_digest,
    write_json,
    write_manifest,
)


class LocalIngestionRunnerTests(unittest.TestCase):
    def test_source_digest_reports_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            source = Path(raw_temp) / "source.pdf"
            source.write_bytes(b"source-safe-fixture\n")

            digest, size = source_digest(source)

            self.assertEqual(
                digest,
                "1433c58a47321c1b7fef9d8be31a5f6f86276ffcf757e954c7e70f817f408603",
            )
            self.assertEqual(size, 20)

    def test_write_json_is_deterministic_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            output = Path(raw_temp) / "record.json"

            write_json(output, {"z": "café", "a": [2, 1]})

            self.assertEqual(
                output.read_bytes(),
                b'{\n  "a": [\n    2,\n    1\n  ],\n  "z": "caf\xc3\xa9"\n}\n',
            )

    def test_prepare_output_dir_replaces_only_recognized_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            output = Path(raw_temp) / "generated"
            output.mkdir()
            (output / "manifest.json").write_text("{}\n", encoding="utf-8")
            (output / "article-90.json").write_text("{}\n", encoding="utf-8")

            prepare_output_dir(
                output,
                force=True,
                generated_name_pattern=r"article-\d+\.json",
            )

            self.assertEqual(list(output.iterdir()), [])

    def test_prepare_output_dir_fails_closed_on_unexpected_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            output = Path(raw_temp) / "generated"
            output.mkdir()
            protected = output / "notes.txt"
            protected.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "unexpected entries"):
                prepare_output_dir(
                    output,
                    force=True,
                    generated_name_pattern=r"chapter-\d+\.json",
                )

            self.assertEqual(protected.read_text(encoding="utf-8"), "keep")

    def test_write_manifest_preserves_common_output_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp_root = Path(raw_temp)
            generated = temp_root / "article-90.json"
            write_json(generated, {"number": "90"})

            paths = write_manifest(
                temp_root,
                {
                    "publication_boundary": "private-local-output",
                    "articles": [{"file": generated.name}],
                },
                [generated],
            )

            self.assertEqual(paths, (temp_root / "manifest.json", generated))
            manifest = json.loads(paths[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["publication_boundary"], "private-local-output")


if __name__ == "__main__":
    unittest.main()
