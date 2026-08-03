#!/usr/bin/env python3
"""Reconcile source-safe IBC 2018 external citations to Chapter 35 families."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from building_code_ast.ibc2018_external_reconciliation import reconcile_external_citations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    return parser.parse_args()


def _load(root: Path, name: str) -> Any:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted({key for record in records for key in record})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: _scalar(record.get(field)) for field in fields})


def reconcile_corpus(corpus_dir: Path) -> dict[str, Any]:
    families = _load(corpus_dir, "ibc-2018-external-reference-inventory.json")
    citations = _load(corpus_dir, "ibc-2018-external-citation-inventory.json")
    reconciled, summary = reconcile_external_citations(citations, families)

    _write_json(corpus_dir / "ibc-2018-external-citation-inventory.json", reconciled)
    _write_csv(corpus_dir / "ibc-2018-external-citation-inventory.csv", reconciled)

    matched_family_ids = {
        str(item["normalized_document_family_id"])
        for item in reconciled
        if item.get("normalized_document_family_id")
    }
    all_family_ids = {str(item["id"]) for item in families}
    unmatched_citation_ids = sorted(
        str(item["id"])
        for item in reconciled
        if item.get("normalized_document_family_id") is None
    )

    crosschecks_path = corpus_dir / "ibc-2018-reference-crosschecks.json"
    crosschecks = _load(corpus_dir, crosschecks_path.name)
    crosschecks["chapter35_families_not_detected_elsewhere"] = sorted(
        all_family_ids - matched_family_ids
    )
    crosschecks["citation_occurrences_without_chapter35_match"] = unmatched_citation_ids
    crosschecks["external_alias_reconciliation"] = summary
    _write_json(crosschecks_path, crosschecks)

    coverage_path = corpus_dir / "ibc-2018-coverage-report.json"
    coverage = _load(corpus_dir, coverage_path.name)
    coverage["chapter35"]["families_not_detected_elsewhere_count"] = len(
        all_family_ids - matched_family_ids
    )
    external = coverage["external_references"]
    external["matched_family_count"] = len(matched_family_ids)
    external["unmatched_occurrence_count"] = summary["unmatched_count"]
    external["newly_alias_matched_occurrence_count"] = summary["newly_matched_count"]
    external["normalization_reason_counts"] = summary["normalization_reason_counts"]
    external["alias_reconciliation_policy"] = summary["policy"]
    _write_json(coverage_path, coverage)

    return {
        **summary,
        "matched_family_count": len(matched_family_ids),
        "families_not_detected_elsewhere_count": len(all_family_ids - matched_family_ids),
    }


def main() -> int:
    args = parse_args()
    print(json.dumps(reconcile_corpus(args.corpus_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
