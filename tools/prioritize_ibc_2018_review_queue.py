#!/usr/bin/env python3
"""Prioritize the source-safe IBC 2018 review queue and emit review packets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from building_code_ast.ibc2018_review import prioritize_review_queue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    return parser.parse_args()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str] | None = None) -> None:
    fieldnames = list(fields or sorted({key for row in rows for key in row}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized: dict[str, str] = {}
            for field in fieldnames:
                value = row.get(field)
                if value is None:
                    serialized[field] = ""
                elif isinstance(value, (str, int, float, bool)):
                    serialized[field] = str(value)
                else:
                    serialized[field] = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            writer.writerow(serialized)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_record_index(root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("ibc-2018-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if isinstance(item, dict) and item.get("id"):
                index[str(item["id"])] = item
    return index


def _semantic_packet(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    packet: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: (str(item.get("chapter")), str(item.get("id")))):
        verification = record.get("structural_verification") or {}
        packet.append(
            {
                "record_id": record.get("id"),
                "chapter": record.get("chapter"),
                "source_record_id": record.get("source_record_id"),
                "source_record_type": record.get("source_record_type"),
                "features": verification.get("features", []),
                "qualifications": verification.get("qualifications", []),
                "source_anchor_verified": verification.get("source_anchor_verified"),
                "record_shape_verified": verification.get("record_shape_verified"),
                "semantic_interpretation_verified": verification.get("semantic_interpretation_verified"),
                "review_state": record.get("review_state"),
                "reviewer_action": "confirm applicability, units, formula/exception/reference relationships, and normative context; record reviewer identity and notes",
            }
        )
    return packet


def _summary_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# IBC 2018 Review Queue Summary",
        "",
        "This report orders source-safe records for human review. Priority does not change evidentiary or semantic status.",
        "",
        "## Priority counts",
        "",
    ]
    for key, value in summary["priority_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Review-state counts", ""])
    for key, value in summary["review_state_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", f"Policy: {summary['policy']}", ""])
    return "\n".join(lines)


def _semantic_markdown(packet: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# IBC 2018 Semantic Pilot Review Packet",
        "",
        "These records are structurally anchored but their semantic interpretations remain unverified until a qualified reviewer signs them off.",
        "",
    ]
    for row in packet:
        lines.extend(
            [
                f"## {row['record_id']}",
                "",
                f"- Chapter: {row['chapter']}",
                f"- Source record: `{row['source_record_id']}` ({row['source_record_type']})",
                f"- Features: {', '.join(row['features'])}",
                f"- Qualifications: {'; '.join(row['qualifications'])}",
                f"- Semantic interpretation verified: {row['semantic_interpretation_verified']}",
                f"- Reviewer action: {row['reviewer_action']}",
                "",
            ]
        )
    return "\n".join(lines)


def prioritize_corpus(corpus_dir: Path) -> dict[str, Any]:
    queue_path = corpus_dir / "ibc-2018-review-queue.csv"
    queue = _read_csv(queue_path)
    records = _load_record_index(corpus_dir)
    prioritized, summary = prioritize_review_queue(queue, records)
    _write_csv(
        queue_path,
        prioritized,
        fields=[
            "priority_band",
            "evidence_category",
            "recommended_action",
            "reason",
            "record_id",
            "record_type",
            "review_state",
        ],
    )

    _write_json(corpus_dir / "ibc-2018-review-summary.json", summary)
    (corpus_dir / "ibc-2018-review-summary.md").write_text(_summary_markdown(summary), encoding="utf-8")

    semantic_records = [
        item for item in records.values() if item.get("record_type") == "semantic_pilot_record"
    ]
    packet = _semantic_packet(semantic_records)
    _write_csv(
        corpus_dir / "ibc-2018-semantic-review-packet.csv",
        packet,
        fields=[
            "record_id",
            "chapter",
            "source_record_id",
            "source_record_type",
            "features",
            "qualifications",
            "source_anchor_verified",
            "record_shape_verified",
            "semantic_interpretation_verified",
            "review_state",
            "reviewer_action",
        ],
    )
    (corpus_dir / "ibc-2018-semantic-review-packet.md").write_text(
        _semantic_markdown(packet), encoding="utf-8"
    )

    coverage_path = corpus_dir / "ibc-2018-coverage-report.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        coverage["review_queue"] = summary
        _write_json(coverage_path, coverage)

    manifest_path = corpus_dir / "ibc-2018-corpus-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = set(manifest.get("inventory_files", []))
        files.update(
            {
                "ibc-2018-review-summary.json",
                "ibc-2018-review-summary.md",
                "ibc-2018-semantic-review-packet.csv",
                "ibc-2018-semantic-review-packet.md",
            }
        )
        manifest["inventory_files"] = sorted(files)
        _write_json(manifest_path, manifest)

    return {**summary, "semantic_pilot_record_count": len(packet)}


def main() -> int:
    args = parse_args()
    print(json.dumps(prioritize_corpus(args.corpus_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
