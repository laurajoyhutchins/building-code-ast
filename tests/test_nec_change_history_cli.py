from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


def _load_cli_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_nec_2020_expected_changelog.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_nec_2020_expected_changelog_cli",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load expected changelog CLI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bundle(*, unresolved: bool = False) -> dict[str, object]:
    affected = ["Table 210.999"] if unresolved else ["210.8"]
    targets = ["Table 210.999"] if unresolved else ["210.8(F)"]
    change_types = ["change_table"] if unresolved else ["add_subdivision"]
    return {
        "bundle_version": "0.1.0",
        "cycle": "2017-to-2020",
        "known_2017_locators": ["210", "210.8", "210.8(F)"],
        "sources": [
            {
                "source_id": "nfpa70-synthetic-council",
                "document_type": "standards_council_decision",
                "title": "Synthetic Council record",
                "cycle": "2017-to-2020",
                "source_url": "https://example.test/council.pdf",
                "retrieved_at": "2026-08-02T13:30:00Z",
                "sha256": "a" * 64,
                "media_type": "application/pdf",
                "access_scope": "private-reference",
                "panel": "CMP-02",
                "page_count": 3,
            }
        ],
        "development_records": [
            {
                "record_id": "SC-synthetic",
                "change_chain_id": "synthetic-change",
                "record_type": "standards_council_action",
                "stage": "standards_council",
                "disposition": "issued",
                "panel": "CMP-02",
                "affected_references_raw": affected,
                "target_references_raw": targets,
                "change_types": change_types,
                "summary": "Synthetic project-authored summary.",
                "source_locator": {
                    "source_id": "nfpa70-synthetic-council",
                    "page": 2,
                    "anchor": "SC-synthetic",
                },
                "related_record_ids": [],
            }
        ],
        "observed_changes": [
            {
                "observed_change_id": "obs-synthetic",
                "from_locators": ["210.8"],
                "to_locators": ["210.8(F)"],
                "change_types": ["add_subdivision"],
                "summary": "Synthetic observed AST change.",
                "alignment_confidence": 0.98,
            }
        ]
        if not unresolved
        else [],
    }


class ExpectedChangelogCliTests(unittest.TestCase):
    def test_writes_deterministic_source_safe_dataset(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "private-input.json"
            output_path = root / "expected-changelog.json"
            input_path.write_text(json.dumps(_bundle()), encoding="utf-8")

            dataset = cli.write_dataset(input_path, output_path)

            self.assertEqual(dataset["dataset_version"], "0.1.0")
            self.assertEqual(dataset["cycle"], "2017-to-2020")
            self.assertEqual(
                dataset["expected_changes"][0]["disposition"],
                "change_expected",
            )
            self.assertEqual(
                dataset["reconciliations"][0]["outcome"],
                "confirmed",
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertNotIn(str(root), text)
            self.assertNotIn("source_text", text)
            self.assertEqual(text, json.dumps(dataset, indent=2, sort_keys=True) + "\n")

    def test_strict_mode_returns_nonzero_for_unresolved_reference(self) -> None:
        cli = _load_cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "private-input.json"
            output_path = root / "expected-changelog.json"
            input_path.write_text(json.dumps(_bundle(unresolved=True)), encoding="utf-8")

            exit_code = cli.main(
                [
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--strict",
                ]
            )

            self.assertEqual(exit_code, 1)
            dataset = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(dataset["diagnostics"][0]["code"], "unresolved-reference")

    def test_source_locator_must_reference_manifest_entry(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        records = bundle["development_records"]
        assert isinstance(records, list)
        record = records[0]
        assert isinstance(record, dict)
        locator = record["source_locator"]
        assert isinstance(locator, dict)
        locator["source_id"] = "missing-source"

        with self.assertRaisesRegex(ValueError, "unknown source_id"):
            cli.build_dataset(bundle)

    def test_source_locator_page_must_fit_manifest_page_count(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        records = bundle["development_records"]
        assert isinstance(records, list)
        record = records[0]
        assert isinstance(record, dict)
        locator = record["source_locator"]
        assert isinstance(locator, dict)
        locator["page"] = 4

        with self.assertRaisesRegex(ValueError, "exceeds manifest page_count"):
            cli.build_dataset(bundle)

    def test_related_record_ids_must_reference_known_records(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        records = bundle["development_records"]
        assert isinstance(records, list)
        record = records[0]
        assert isinstance(record, dict)
        record["related_record_ids"] = ["missing-record"]

        with self.assertRaisesRegex(ValueError, "unknown related record_id"):
            cli.build_dataset(bundle)

    def test_record_type_must_match_development_stage(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        records = bundle["development_records"]
        assert isinstance(records, list)
        record = records[0]
        assert isinstance(record, dict)
        record["record_type"] = "public_input"

        with self.assertRaisesRegex(ValueError, "does not match stage"):
            cli.build_dataset(bundle)

    def test_forbidden_source_bearing_fields_fail_closed(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        records = bundle["development_records"]
        assert isinstance(records, list)
        record = records[0]
        assert isinstance(record, dict)
        record["proposal_text"] = "Protected source expression must not enter output."

        with self.assertRaisesRegex(ValueError, "unsupported development record field"):
            cli.build_dataset(bundle)

    def test_forbidden_top_level_fields_fail_closed(self) -> None:
        cli = _load_cli_module()
        bundle = _bundle()
        bundle["source_text"] = "Protected source expression must not enter output."

        with self.assertRaisesRegex(ValueError, "unsupported bundle field"):
            cli.build_dataset(bundle)


if __name__ == "__main__":
    unittest.main()
