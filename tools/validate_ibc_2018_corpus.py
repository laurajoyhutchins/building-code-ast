#!/usr/bin/env python3
"""Validate the source-safe 2018 IBC corpus without the copyrighted PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from building_code_ast.evidence import load_source_package
from building_code_ast.ibc2018_corpus import SOURCE_PAGE_COUNT, SOURCE_SHA256

EXPECTED_FILES = {
    "README.md",
    "ibc-2018-source-manifest.json",
    "source-package.json",
    "ibc-2018-corpus-manifest.json",
    "ibc-2018-table-inventory.csv",
    "ibc-2018-table-inventory.json",
    "ibc-2018-table-inventory.md",
    "ibc-2018-incidental-layout-inventory.csv",
    "ibc-2018-incidental-layout-inventory.json",
    "ibc-2018-incidental-layout-broad-inventory.json",
    "ibc-2018-incidental-layout-strict-inventory.json",
    "ibc-2018-figure-inventory.csv",
    "ibc-2018-figure-inventory.json",
    "ibc-2018-figure-inventory.md",
    "ibc-2018-diagram-inventory.csv",
    "ibc-2018-diagram-inventory.json",
    "ibc-2018-vector-region-inventory.csv",
    "ibc-2018-vector-region-inventory.json",
    "ibc-2018-vector-region-summary.json",
    "ibc-2018-equation-inventory.csv",
    "ibc-2018-equation-inventory.json",
    "ibc-2018-definition-inventory.csv",
    "ibc-2018-definition-inventory.json",
    "ibc-2018-exception-inventory.csv",
    "ibc-2018-exception-inventory.json",
    "ibc-2018-chapter-35-inventory.csv",
    "ibc-2018-chapter-35-inventory.json",
    "ibc-2018-external-reference-inventory.csv",
    "ibc-2018-external-reference-inventory.json",
    "ibc-2018-external-citation-inventory.csv",
    "ibc-2018-external-citation-inventory.json",
    "ibc-2018-reference-map.md",
    "ibc-2018-reference-crosschecks.json",
    "ibc-2018-cross-reference-inventory.json",
    "ibc-2018-cross-reference-summary.json",
    "ibc-2018-detection-inventory.json",
    "ibc-2018-attachment-inventory.json",
    "ibc-2018-semantic-pilot.json",
    "ibc-2018-semantic-pilot-report.md",
    "ibc-2018-coverage-report.json",
    "ibc-2018-coverage-report.md",
    "ibc-2018-discrepancies.md",
    "ibc-2018-review-queue.csv",
    "ibc-2018-schema-validation-report.json",
    "ibc-2018-semantic-review-packet.md",
    "ibc-2018-semantic-review-packet.csv",
    "ibc-2018-review-summary.md",
    "ibc-2018-review-summary.json",
    "ibc-2018-counting-policy.md",
    "ibc-2018-corrections.md",
    "ibc-2018-unresolved-borderline-cases.md",
    "ibc-2018-page-map.json",
    "ibc-2018-page-evidence-index.json",
}


INVENTORY_FILES = {
    "tables": "ibc-2018-table-inventory.json",
    "incidental_layouts": "ibc-2018-incidental-layout-inventory.json",
    "figures": "ibc-2018-figure-inventory.json",
    "diagrams": "ibc-2018-diagram-inventory.json",
    "vector_regions": "ibc-2018-vector-region-inventory.json",
    "equations": "ibc-2018-equation-inventory.json",
    "definitions": "ibc-2018-definition-inventory.json",
    "exceptions": "ibc-2018-exception-inventory.json",
    "chapter35_rows": "ibc-2018-chapter-35-inventory.json",
    "external_families": "ibc-2018-external-reference-inventory.json",
    "external_citations": "ibc-2018-external-citation-inventory.json",
    "cross_references": "ibc-2018-cross-reference-inventory.json",
    "semantic_pilot": "ibc-2018-semantic-pilot.json",
    "detections": "ibc-2018-detection-inventory.json",
    "attachments": "ibc-2018-attachment-inventory.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def anchor_errors(record_id: str, anchor: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    page = anchor.get("pdf_page")
    if not isinstance(page, int) or not 1 <= page <= SOURCE_PAGE_COUNT:
        errors.append({"code": "page-anchor-mismatch", "record_id": record_id})
    bbox = anchor.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4 or bbox[2] < bbox[0] or bbox[3] < bbox[1]:
        errors.append({"code": "invalid-bounding-box", "record_id": record_id})
    digest = anchor.get("observed_text_sha256")
    if digest is not None and (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        errors.append({"code": "invalid-observed-text-digest", "record_id": record_id})
    return errors


def validate(corpus_dir: Path) -> dict[str, Any]:
    discrepancies: list[dict[str, Any]] = []
    missing = sorted(name for name in EXPECTED_FILES if not (corpus_dir / name).is_file())
    discrepancies.extend({"code": "missing-artifact", "file": name} for name in missing)
    if missing:
        return {"valid": False, "discrepancies": discrepancies}

    source_manifest = load(corpus_dir / "ibc-2018-source-manifest.json")
    if source_manifest.get("sha256") != SOURCE_SHA256:
        discrepancies.append({"code": "source-hash-mismatch"})
    if source_manifest.get("pdf_page_count") != SOURCE_PAGE_COUNT:
        discrepancies.append({"code": "page-count-mismatch"})

    source_package = load_source_package(corpus_dir / "source-package.json")
    source_binding = source_package.binding_for_source("source:icc:ibc:2018:pdf:c8f0b755")
    source_artifact = source_package.artifact(source_binding.artifact_id)
    if source_artifact.sha256 != SOURCE_SHA256:
        discrepancies.append({"code": "source-package-hash-mismatch"})

    manifest = load(corpus_dir / "ibc-2018-corpus-manifest.json")
    coverage = load(corpus_dir / "ibc-2018-coverage-report.json")
    expected_counts = manifest["expected_artifact_counts"]
    actual_counts: dict[str, int] = {}
    all_ids: set[str] = set()
    for name, filename in INVENTORY_FILES.items():
        records: Sequence[Mapping[str, Any]] = load(corpus_dir / filename)
        actual_counts[name] = len(records)
        ids = [str(record.get("id", "")) for record in records]
        duplicates = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
        discrepancies.extend(
            {"code": "duplicate-logical-structure", "inventory": name, "record_id": record_id}
            for record_id in duplicates
        )
        for record in records:
            record_id = str(record.get("id", ""))
            if not record_id.startswith("ibc2018:"):
                discrepancies.append({"code": "invalid-record-id", "inventory": name, "record_id": record_id})
            all_ids.add(record_id)
            anchors = list(record.get("anchors", ()))
            if record.get("source_anchor"):
                anchors.append(record["source_anchor"])
            for anchor in anchors:
                discrepancies.extend(anchor_errors(record_id, anchor))
        asserted = expected_counts.get(name, {}).get("value")
        if asserted != len(records):
            discrepancies.append(
                {"code": "aggregate-count-mismatch", "inventory": name, "expected": asserted, "actual": len(records)}
            )
        if coverage["counts"].get(name) != len(records):
            discrepancies.append(
                {"code": "coverage-count-mismatch", "inventory": name, "actual": len(records)}
            )

    tables = load(corpus_dir / "ibc-2018-table-inventory.json")
    for table in tables:
        page_range = table["pdf_page_range"]
        pages = [anchor["pdf_page"] for anchor in table["anchors"]]
        if page_range != [min(pages), max(pages)]:
            discrepancies.append({"code": "split-continuation", "record_id": table["id"]})
    figures = load(corpus_dir / "ibc-2018-figure-inventory.json")
    discrepancies.extend(
        {"code": "figure-caption-detachment", "record_id": item["id"]}
        for item in figures
        if not item.get("caption")
    )
    exceptions = load(corpus_dir / "ibc-2018-exception-inventory.json")
    discrepancies.extend(
        {"code": "exception-detachment", "record_id": item["id"]}
        for item in exceptions
        if not item.get("parent_locator")
    )
    references = load(corpus_dir / "ibc-2018-cross-reference-inventory.json")
    allowed_states = {"resolved", "ambiguous", "unresolved", "nonexistent"}
    discrepancies.extend(
        {"code": "invalid-reference-resolution-state", "record_id": item["id"]}
        for item in references
        if item.get("resolution_state") not in allowed_states
    )

    projection_digest = hashlib.sha256(
        json.dumps(actual_counts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "0.1.0",
        "record_type": "ibc_2018_corpus_validation",
        "source_sha256": SOURCE_SHA256,
        "valid": not discrepancies,
        "actual_counts": actual_counts,
        "count_projection_sha256": projection_digest,
        "discrepancy_count": len(discrepancies),
        "discrepancies": discrepancies,
    }


def main() -> int:
    args = parse_args()
    report = validate(args.corpus_dir)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
