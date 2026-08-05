from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import unittest

from building_code_ast.nfpa13_bundle import (
    BUNDLE_SCHEMA,
    PRODUCER_SCHEMA,
    finalize_raw_nfpa13_bundle,
    read_nfpa13_bundle,
    validate_review_registry,
)


def node_id(locator: str, node_type: str) -> str:
    canonical = json.dumps(
        {
            "artifact_id": "nfpa:13",
            "edition_id": "2019",
            "locator": locator,
            "node_type": node_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "docnode:" + hashlib.sha256(canonical.encode()).hexdigest()


def node(
    locator: str,
    node_type: str,
    source: str,
    *,
    start: int = 0,
    end: int | None = None,
    attributes: dict[str, str] | None = None,
    children: list[dict] | None = None,
) -> dict:
    if end is None:
        end = len(source)
    return {
        "node_id": node_id(locator, node_type),
        "type": node_type,
        "locator": locator,
        "span": {"start": start, "end": end, "text": source[start:end]},
        "label": None,
        "attributes": attributes or {},
        "children": children or [],
    }


def raw_bundle() -> dict:
    source = "ASTM A53 and Section 300.22."
    leaf = node(
        "A.1.1#p1",
        "paragraph",
        source,
        attributes={"owns_source": "true", "annex": "A"},
    )
    explicit = node(
        "A.1.1",
        "subsection",
        source,
        attributes={
            "owns_source": "false",
            "annex": "A",
            "explicit": "true",
            "corresponds_to": "1.1",
        },
        children=[leaf],
    )
    implicit = node(
        "A.1",
        "section",
        source,
        attributes={
            "owns_source": "false",
            "annex": "A",
            "implicit": "true",
            "corresponds_to": "1",
        },
        children=[explicit],
    )
    target_1 = node("1", "chapter", source, start=0, end=0)
    target_11 = node("1.1", "section", source, start=0, end=0)
    root = node(
        "document",
        "document",
        source,
        attributes={"owns_source": "false"},
        children=[target_1, target_11, implicit],
    )
    return {
        "schema": "nfpa13-ast-bundle/0.1.0",
        "source": {
            "artifact_id": "nfpa:13",
            "edition_id": "2019",
            "title": "NFPA 13",
            "file_name": "nfpa-2019.pdf",
            "source_pdf_sha256": "0" * 64,
            "source_pdf_pages": 1,
            "nfpa13_first_pdf_page": 1,
            "nfpa13_last_clause_pdf_page": 1,
        },
        "document_ast": {
            "ast_version": "0.1.0",
            "type": "document_tree",
            "source_text": source,
            "source_artifact": {"artifact_id": "nfpa:13", "edition_id": "2019"},
            "root": root,
            "diagnostics": [],
        },
        "relations": [
            {
                "type": "explains",
                "source_locator": "A.1",
                "target_locator": "1",
                "resolved": True,
                "evidence": None,
            },
            {
                "type": "explains",
                "source_locator": "A.1.1",
                "target_locator": "1.1",
                "resolved": True,
                "evidence": None,
            },
            {
                "type": "references_clause",
                "source_locator": "A.1.1#p1",
                "target_locator": "300.22",
                "resolved": False,
                "evidence": {"start": 13, "end": 27, "text": "Section 300.22"},
            },
        ],
        "semantic_annotations": [
            {
                "type": "informative",
                "source_locator": "A.1.1#p1",
                "confidence": "deterministic",
                "evidence": {"start": 0, "end": len(source), "text": source},
            }
        ],
        "tables": [],
        "source_map": [],
        "statistics": {},
        "validation": {"passed": True},
    }


def producer() -> dict:
    return {
        "schema": PRODUCER_SCHEMA,
        "repository": "laurajoyhutchins/building-code-ast",
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",
        "engine_path": "tools/extract_nfpa13_2019_ast.py",
        "engine_sha256": "a" * 64,
        "wrapper_path": "tools/build_nfpa13_2019_bundle.py",
        "wrapper_sha256": "b" * 64,
        "python_version": platform.python_version(),
        "pymupdf_version": "test",
        "command_options": {"expected_sha256": "0" * 64},
    }


class BundleCanonicalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = finalize_raw_nfpa13_bundle(
            raw_bundle(),
            producer=producer(),
            document_validator=lambda value: value,
            engine_validator=lambda value: {"passed": True},
        )

    def test_filters_implicit_annex_a_explains_relationship(self) -> None:
        explains = [item for item in self.bundle["relations"] if item["type"] == "explains"]
        self.assertEqual(["A.1.1"], [item["source_locator"] for item in explains])
        self.assertEqual(1, self.bundle["statistics"]["explicit_annex_a_explains"])

    def test_unresolved_reference_does_not_guess_target_artifact(self) -> None:
        relation = next(
            item for item in self.bundle["relations"] if item["target_locator"] == "300.22"
        )
        self.assertEqual("unspecified_document", relation["target_domain"])
        self.assertIsNone(relation["target_artifact_id"])
        self.assertFalse(relation["resolved"])

    def test_extracts_non_nfpa_external_standard_identity(self) -> None:
        relation = next(
            item
            for item in self.bundle["relations"]
            if item["target_artifact_id"] == "standard:ASTM:A53"
        )
        self.assertEqual("external_standard", relation["target_domain"])
        self.assertEqual("ASTM A53", relation["evidence"]["text"])

    def test_semantics_record_method_revision_and_review_state(self) -> None:
        annotation = self.bundle["semantic_annotations"][0]
        self.assertNotIn("confidence", annotation)
        self.assertEqual("lexical-deterministic", annotation["method"])
        self.assertEqual("b" * 64, annotation["parser_revision"])
        self.assertEqual("unreviewed", annotation["review_status"])

    def test_emits_strict_versioned_contract_and_producer(self) -> None:
        self.assertEqual(BUNDLE_SCHEMA, self.bundle["schema"])
        self.assertEqual(PRODUCER_SCHEMA, self.bundle["producer"]["schema"])
        self.assertTrue(self.bundle["validation"]["passed"])

    def test_reader_rejects_unknown_top_level_fields(self) -> None:
        invalid = deepcopy(self.bundle)
        invalid["surprise"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            read_nfpa13_bundle(invalid, document_validator=lambda value: value)

    def test_reader_rejects_guessed_artifact_for_unresolved_relation(self) -> None:
        invalid = deepcopy(self.bundle)
        relation = next(
            item for item in invalid["relations"] if item["target_locator"] == "300.22"
        )
        relation["target_artifact_id"] = "nfpa:13"
        with self.assertRaisesRegex(ValueError, "must not guess an artifact"):
            read_nfpa13_bundle(invalid, document_validator=lambda value: value)

    @unittest.skipUnless(
        importlib.util.find_spec("building_code_ast.document_io") is not None,
        "repository Document AST reader is not available in the isolated staging tree",
    )
    def test_default_reader_accepts_existing_document_ast_contract(self) -> None:
        # This call intentionally uses the repository's strict Document AST reader.
        read_nfpa13_bundle(self.bundle)


class ReviewRegistryTests(unittest.TestCase):
    def test_reviewed_registry_is_stratified_and_nonduplicative(self) -> None:
        path = (
            Path(__file__).parents[1]
            / "fixtures"
            / "reviewed"
            / "nfpa13-2019-golden-cases.json"
        )
        report = validate_review_registry(json.loads(path.read_text(encoding="utf-8")))
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["case_count"], 12)
        self.assertIn("table", report["categories"])
        self.assertIn("external-standard", report["categories"])


if __name__ == "__main__":
    unittest.main()
