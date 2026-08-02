from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


def _load_cli_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check_nec_2017_hierarchy.py"
    spec = importlib.util.spec_from_file_location("check_nec_2017_hierarchy_cli", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load hierarchy conformance CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_seed() -> dict[str, object]:
    source = "110.1 Scope. Synthetic source prose.\n\n(A) Alpha. More synthetic source prose."
    child_start = source.index("(A)")
    source_hash = "e" * 64
    subsection = {
        "node_id": "synthetic-subsection",
        "type": "subsection",
        "locator": "nec:110.1(A)",
        "span": {
            "start": child_start,
            "end": len(source),
            "text": source[child_start:],
        },
        "label": "(A)",
        "attributes": {
            "nec_locator": "110.1(A)",
            "nec_parent": "110.1",
            "nec_depth": "2",
            "nec_title": "Alpha",
        },
        "children": [],
    }
    section = {
        "node_id": "synthetic-section",
        "type": "section",
        "locator": "nec:110.1",
        "span": {"start": 0, "end": len(source), "text": source},
        "label": "110.1 Scope.",
        "attributes": {
            "nec_locator": "110.1",
            "nec_parent": "110",
            "nec_depth": "1",
            "nec_title": "Scope",
        },
        "children": [subsection],
    }
    article = {
        "node_id": "synthetic-article",
        "type": "section",
        "locator": "article:110",
        "span": {"start": 0, "end": len(source), "text": source},
        "label": "Article 110 - Synthetic",
        "attributes": {"article_number": "110"},
        "children": [section],
    }
    root = {
        "node_id": "synthetic-root",
        "type": "document",
        "locator": "document:article:110",
        "span": {"start": 0, "end": len(source), "text": source},
        "label": "Synthetic document",
        "attributes": {},
        "children": [article],
    }
    return {
        "seed_version": "0.1.0",
        "source_manifest": {
            "artifact_id": "test:electrical-code",
            "edition_id": f"test:sha256:{source_hash}",
            "sha256": source_hash,
        },
        "article": {"number": "110", "title": "Synthetic"},
        "document_ast": {
            "source_text": source,
            "source_artifact": {
                "artifact_id": "test:electrical-code",
                "edition_id": f"test:sha256:{source_hash}",
            },
            "root": root,
        },
    }


class HierarchyConformanceCliTests(unittest.TestCase):
    def test_write_report_matches_oracle_without_source_disclosure(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed_path = root / "article-110.json"
            oracle_path = root / "nec-2017-clauses.csv"
            report_path = root / "report.json"
            seed_path.write_text(json.dumps(_synthetic_seed()), encoding="utf-8")
            oracle_path.write_text(
                "clause_id,clause_title,parent\n"
                "110.1,Scope,110\n"
                "110.1(A),Alpha,110.1\n",
                encoding="utf-8",
            )

            report = cli.write_report((seed_path,), oracle_path, report_path)

            self.assertTrue(report["conforms"])
            self.assertEqual(report["articles"], ["110"])
            text = report_path.read_text(encoding="utf-8")
            self.assertNotIn("source_text", text)
            self.assertNotIn("Synthetic source prose", text)
            self.assertNotIn("e" * 64, text)
            self.assertTrue(text.endswith("\n"))

    def test_strict_mode_returns_nonzero_for_mismatch(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed_path = root / "article-110.json"
            oracle_path = root / "nec-2017-clauses.csv"
            report_path = root / "report.json"
            seed_path.write_text(json.dumps(_synthetic_seed()), encoding="utf-8")
            oracle_path.write_text(
                "clause_id,clause_title,parent\n"
                "110.1,Different Title,110\n",
                encoding="utf-8",
            )

            exit_code = cli.main(
                [
                    "--article-seed",
                    str(seed_path),
                    "--oracle",
                    str(oracle_path),
                    "--report",
                    str(report_path),
                    "--strict",
                ]
            )

            self.assertEqual(exit_code, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["conforms"])
            self.assertIn("title-mismatch", report["mismatch_counts"])
            self.assertIn("missing-locator", report["mismatch_counts"])

    def test_duplicate_article_seed_is_rejected(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed_path = root / "article-110.json"
            oracle_path = root / "nec-2017-clauses.csv"
            report_path = root / "report.json"
            seed_path.write_text(json.dumps(_synthetic_seed()), encoding="utf-8")
            oracle_path.write_text(
                "clause_id,clause_title,parent\n110.1,Scope,110\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate ArticleSeed"):
                cli.write_report(
                    (seed_path, seed_path),
                    oracle_path,
                    report_path,
                )


if __name__ == "__main__":
    unittest.main()
