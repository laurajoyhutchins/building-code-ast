from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_nec_definitions import _article_seed
from tests.test_nec_sections import _article_90, _article_110


def _load_cli_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_nec_2017_semantics.py"
    spec = importlib.util.spec_from_file_location("build_nec_2017_semantics_cli", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load semantic bundle CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_seed(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class SemanticBundleCliTests(unittest.TestCase):
    def test_writes_expected_bundle_without_absolute_paths(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "private-inputs"
            private.mkdir()
            article_90 = private / "article-90.json"
            article_100 = private / "article-100.json"
            article_110 = private / "article-110.json"
            _write_seed(article_90, _article_90())
            _write_seed(article_100, _article_seed())
            _write_seed(article_110, _article_110())
            output = root / "generated"

            written = cli.write_outputs(
                article_90,
                article_100,
                article_110,
                output,
                force=False,
            )

            self.assertEqual(
                {path.name for path in written},
                {
                    "manifest.json",
                    "definitions-article-100.json",
                    "language-policy-90.5.json",
                    "section-110.2.json",
                    "section-110.3.json",
                    "section-110.14.json",
                    "section-110.16.json",
                    "section-110.26.json",
                },
            )
            manifest_text = (output / "manifest.json").read_text(encoding="utf-8")
            self.assertNotIn(str(root), manifest_text)
            manifest = json.loads(manifest_text)
            self.assertEqual(manifest["definition_index"]["entry_count"], 2)
            self.assertEqual(
                [item["section_locator"] for item in manifest["section_reviews"]],
                ["110.2", "110.3", "110.14", "110.16", "110.26"],
            )

    def test_source_identity_mismatch_fails_closed(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            article_90 = root / "article-90.json"
            article_100 = root / "article-100.json"
            article_110 = root / "article-110.json"
            payload_110 = _article_110()
            payload_110["document_ast"]["source_artifact"]["edition_id"] = "other-edition"
            _write_seed(article_90, _article_90())
            _write_seed(article_100, _article_seed())
            _write_seed(article_110, payload_110)

            with self.assertRaisesRegex(ValueError, "source artifact identity"):
                cli.write_outputs(
                    article_90,
                    article_100,
                    article_110,
                    root / "generated",
                    force=False,
                )

    def test_force_refuses_unexpected_contents(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "generated"
            output.mkdir()
            (output / "owner-data.txt").write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "unexpected entries"):
                cli.prepare_output_dir(output, force=True)

            self.assertTrue((output / "owner-data.txt").exists())

    def test_force_replaces_only_known_bundle_files(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "generated"
            output.mkdir()
            (output / "manifest.json").write_text("{}", encoding="utf-8")
            (output / "section-110.2.json").write_text("{}", encoding="utf-8")

            cli.prepare_output_dir(output, force=True)

            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
