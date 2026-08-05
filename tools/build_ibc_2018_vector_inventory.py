#!/usr/bin/env python3
"""Build source-safe vector-region review artifacts from private evidence."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from building_code_ast.ibc2018_corpus import inventory_vector_graphic_regions

VECTOR_JSON = "ibc-2018-vector-region-inventory.json"
VECTOR_CSV = "ibc-2018-vector-region-inventory.csv"
VECTOR_SUMMARY = "ibc-2018-vector-region-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("vector_evidence", type=Path)
    parser.add_argument("corpus_dir", type=Path)
    return parser.parse_args()


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted({key for record in records for key in record})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: _scalar(record.get(field)) for field in fields})


def write_artifacts(
    output_dir: Path,
    evidence: Mapping[str, Any],
    *,
    figures: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = inventory_vector_graphic_regions(evidence, figures=figures)
    dispositions = Counter(str(record["disposition"]) for record in records)
    states = Counter(str(record["review_state"]) for record in records)
    pages = {int(record["source_anchor"]["pdf_page"]) for record in records}
    summary = {
        "schema_version": "0.1.0",
        "record_type": "ibc_2018_vector_region_summary",
        "source_sha256": evidence["source_sha256"],
        "record_count": len(records),
        "page_count_with_regions": len(pages),
        "disposition_counts": dict(sorted(dispositions.items())),
        "review_state_counts": dict(sorted(states.items())),
        "interpretation_state": "unreviewed",
        "source_safe": True,
    }
    _write_json(output_dir / VECTOR_JSON, records)
    _write_csv(output_dir / VECTOR_CSV, records)
    _write_json(output_dir / VECTOR_SUMMARY, summary)
    return records, summary



def _context_key(record: Mapping[str, Any]) -> str:
    if record.get("chapter"):
        return f"chapter:{record['chapter']}"
    if record.get("appendix"):
        return f"appendix:{record['appendix']}"
    return "other"


def _replace_vector_limitation(limitations: Sequence[str], summary: Mapping[str, Any]) -> list[str]:
    retained = [item for item in limitations if "vector-only" not in item.lower() and "vector-path" not in item.lower()]
    retained.append(
        "The completed vector-path scan identified "
        f"{summary['record_count']} source-backed regions on {summary['page_count_with_regions']} pages; "
        "automatic classification remains conservative and disputed regions require visual review."
    )
    return retained


def update_corpus_metadata(
    corpus_dir: Path,
    records: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    manifest_path = corpus_dir / "ibc-2018-corpus-manifest.json"
    coverage_path = corpus_dir / "ibc-2018-coverage-report.json"
    queue_path = corpus_dir / "ibc-2018-review-queue.csv"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("expected_artifact_counts", {})["vector_regions"] = {
        "status": "provisional",
        "value": len(records),
    }
    manifest["known_limitations"] = _replace_vector_limitation(
        manifest.get("known_limitations", ()), summary
    )
    inventory_files = set(manifest.get("inventory_files", ()))
    inventory_files.update({VECTOR_JSON, VECTOR_CSV, VECTOR_SUMMARY})
    manifest["inventory_files"] = sorted(inventory_files)
    _write_json(manifest_path, manifest)

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage.setdefault("counts", {})["vector_regions"] = len(records)
    context_counts = Counter(_context_key(record) for record in records)
    coverage.setdefault("counts_by_context", {})["vector_regions"] = dict(
        sorted(context_counts.items())
    )
    coverage["vector_regions"] = {
        "record_count": len(records),
        "page_count_with_regions": summary["page_count_with_regions"],
        "disposition_counts": summary["disposition_counts"],
        "review_state_counts": summary["review_state_counts"],
    }
    coverage["known_limitations"] = _replace_vector_limitation(
        coverage.get("known_limitations", ()), summary
    )
    _write_json(coverage_path, coverage)

    with queue_path.open(encoding="utf-8", newline="") as handle:
        queue_rows = list(csv.DictReader(handle))
    existing_ids = {row["record_id"] for row in queue_rows}
    for record in sorted(records, key=lambda item: str(item["id"])):
        if record.get("review_state") != "disputed" or record["id"] in existing_ids:
            continue
        queue_rows.append(
            {
                "reason": str(record["disposition"]),
                "record_id": str(record["id"]),
                "record_type": str(record["record_type"]),
                "review_state": str(record["review_state"]),
            }
        )
    with queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["reason", "record_id", "record_type", "review_state"]
        )
        writer.writeheader()
        writer.writerows(queue_rows)

def main() -> int:
    args = parse_args()
    evidence = json.loads(args.vector_evidence.read_text(encoding="utf-8"))
    figures = json.loads(
        (args.corpus_dir / "ibc-2018-figure-inventory.json").read_text(encoding="utf-8")
    )
    records, summary = write_artifacts(args.corpus_dir, evidence, figures=figures)
    update_corpus_metadata(args.corpus_dir, records, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
