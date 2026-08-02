#!/usr/bin/env python3
"""Verify non-source-bearing reviewed expectations against a local NFPA 13 bundle."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


def _walk(node: Mapping[str, Any]):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _matches(relation: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(relation.get(key) == value for key, value in expected.items())


def verify(bundle: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    from building_code_ast.nfpa13_bundle import (
        read_nfpa13_bundle,
        validate_review_registry,
    )

    read_nfpa13_bundle(bundle)
    validate_review_registry(registry)
    source_sha = bundle["source"]["source_pdf_sha256"]
    if source_sha != registry["source_pdf_sha256"]:
        raise ValueError("review registry source hash does not match the local bundle")

    nodes = {
        str(node["locator"]): node
        for node in _walk(bundle["document_ast"]["root"])
    }
    relations = list(bundle["relations"])
    tables = {str(item["locator"]): item for item in bundle["tables"]}
    failures: list[dict[str, Any]] = []

    for case in registry["cases"]:
        locator = case["locator"]
        assertion = case["assertion"]
        expected = case["expected"]
        try:
            if assertion == "node_label":
                actual = nodes[locator].get("label")
                if actual != expected:
                    raise AssertionError(f"expected label {expected!r}, got {actual!r}")
            elif assertion == "direct_child_type_counts":
                counts = Counter(child["type"] for child in nodes[locator]["children"])
                for node_type, count in expected.items():
                    if counts[node_type] != count:
                        raise AssertionError(
                            f"expected {count} direct {node_type} children, got {counts[node_type]}"
                        )
            elif assertion == "no_standalone_revision_marker":
                text = nodes[locator]["span"]["text"]
                if re.search(r"(?:^|\n)\s*[NΔ]\s*(?:\n|$)", text):
                    raise AssertionError("standalone revision marker leaked into node source")
            elif assertion in {"relation_present", "relation_absent"}:
                candidates = [
                    relation
                    for relation in relations
                    if relation.get("source_locator") == locator
                    and _matches(relation, expected)
                ]
                if assertion == "relation_present" and not candidates:
                    raise AssertionError(f"expected relation not found: {expected}")
                if assertion == "relation_absent" and candidates:
                    raise AssertionError(f"forbidden relation found: {expected}")
            elif assertion == "json_attribute_contains":
                raw = nodes[locator]["attributes"].get(expected["attribute"])
                values = json.loads(raw)
                if expected["value"] not in values:
                    raise AssertionError(
                        f"attribute {expected['attribute']} lacks {expected['value']}"
                    )
            elif assertion == "table_shape":
                matrix = tables[locator]["matrix"]
                widths = [len(row) for row in matrix[: len(expected["first_row_widths"])]]
                if len(matrix) != expected["rows"] or widths != expected["first_row_widths"]:
                    raise AssertionError(
                        f"expected rows/widths {expected}, got rows={len(matrix)} widths={widths}"
                    )
            elif assertion == "external_standard_min_count":
                prefix = f"standard:{expected['issuer']}:"
                count = sum(
                    relation.get("target_domain") == "external_standard"
                    and str(relation.get("target_artifact_id", "")).startswith(prefix)
                    for relation in relations
                )
                if count < expected["minimum"]:
                    raise AssertionError(
                        "expected at least "
                        f"{expected['minimum']} {expected['issuer']} relations, "
                        f"got {count}"
                    )
            else:
                raise AssertionError(f"unsupported assertion: {assertion}")
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            failures.append({"id": case["id"], "error": str(exc)})

    return {
        "passed": not failures,
        "case_count": len(registry["cases"]),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("fixtures/reviewed/nfpa13-2019-golden-cases.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    report = verify(bundle, registry)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
