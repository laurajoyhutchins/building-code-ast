#!/usr/bin/env python3
"""Reconcile source-safe IBC 2018 internal-reference records."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from building_code_ast.ibc2018_reconciliation import (
    collect_known_section_targets,
    reconcile_internal_references,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    return parser.parse_args()


def _load(root: Path, name: str) -> Any:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    references = _load(corpus_dir, "ibc-2018-cross-reference-inventory.json")
    tables = _load(corpus_dir, "ibc-2018-table-inventory.json")
    figures = _load(corpus_dir, "ibc-2018-figure-inventory.json")
    equations = _load(corpus_dir, "ibc-2018-equation-inventory.json")
    exceptions = _load(corpus_dir, "ibc-2018-exception-inventory.json")
    known = collect_known_section_targets(
        cross_references=references,
        tables=tables,
        figures=figures,
        equations=equations,
        exceptions=exceptions,
    )
    reconciled = reconcile_internal_references(references, known_section_targets=known)
    changed = sum(
        before.get("resolution_state") != after.get("resolution_state")
        or before.get("resolution_reason") != after.get("resolution_reason")
        for before, after in zip(references, reconciled, strict=True)
    )
    _write_json(corpus_dir / "ibc-2018-cross-reference-inventory.json", reconciled)
    _write_csv(corpus_dir / "ibc-2018-cross-reference-inventory.csv", reconciled)

    resolution_counts = Counter(str(item["resolution_state"]) for item in reconciled)
    reason_counts = Counter(str(item["resolution_reason"]) for item in reconciled)
    summary_path = corpus_dir / "ibc-2018-cross-reference-summary.json"
    summary = _load(corpus_dir, summary_path.name)
    summary["resolution_counts"] = dict(sorted(resolution_counts.items()))
    summary["resolution_reason_counts"] = dict(sorted(reason_counts.items()))
    summary["reconciliation"] = {
        "known_section_target_count": len(known),
        "changed_record_count": changed,
        "policy": "exact known targets and digit-only section-heading prefixes only",
    }
    _write_json(summary_path, summary)

    coverage_path = corpus_dir / "ibc-2018-coverage-report.json"
    coverage = _load(corpus_dir, coverage_path.name)
    coverage["internal_reference_resolution"] = dict(sorted(resolution_counts.items()))
    coverage["internal_reference_resolution_reasons"] = dict(sorted(reason_counts.items()))
    _write_json(coverage_path, coverage)

    return {
        "record_count": len(reconciled),
        "known_section_target_count": len(known),
        "changed_record_count": changed,
        "resolution_counts": dict(sorted(resolution_counts.items())),
        "resolution_reason_counts": dict(sorted(reason_counts.items())),
    }


def main() -> int:
    args = parse_args()
    print(json.dumps(reconcile_corpus(args.corpus_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
