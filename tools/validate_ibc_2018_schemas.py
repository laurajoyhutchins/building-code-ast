#!/usr/bin/env python3
"""Validate IBC 2018 source-safe artifacts against Draft 2020-12 schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from building_code_ast.json_schema_validation import validate_instances


INVENTORY_FILES = (
    "ibc-2018-table-inventory.json",
    "ibc-2018-incidental-layout-inventory.json",
    "ibc-2018-figure-inventory.json",
    "ibc-2018-diagram-inventory.json",
    "ibc-2018-vector-region-inventory.json",
    "ibc-2018-equation-inventory.json",
    "ibc-2018-definition-inventory.json",
    "ibc-2018-exception-inventory.json",
    "ibc-2018-chapter-35-inventory.json",
    "ibc-2018-external-reference-inventory.json",
    "ibc-2018-external-citation-inventory.json",
    "ibc-2018-cross-reference-inventory.json",
    "ibc-2018-semantic-pilot.json",
    "ibc-2018-detection-inventory.json",
    "ibc-2018-attachment-inventory.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus_dir", type=Path)
    parser.add_argument("schema_dir", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_corpus_schemas(corpus_dir: Path, schema_dir: Path) -> dict[str, Any]:
    source_schema = _load(schema_dir / "ibc-2018-source-manifest.schema.json")
    corpus_schema = _load(schema_dir / "ibc-2018-corpus-manifest.schema.json")
    inventory_schema = _load(schema_dir / "ibc-2018-inventory-record.schema.json")
    for schema in (source_schema, corpus_schema, inventory_schema):
        Draft202012Validator.check_schema(schema)

    errors: list[dict[str, Any]] = []
    for artifact_name, schema, instances in (
        (
            "ibc-2018-source-manifest.json",
            source_schema,
            [_load(corpus_dir / "ibc-2018-source-manifest.json")],
        ),
        (
            "ibc-2018-corpus-manifest.json",
            corpus_schema,
            [_load(corpus_dir / "ibc-2018-corpus-manifest.json")],
        ),
    ):
        for error in validate_instances(instances, schema):
            errors.append({"artifact": artifact_name, **error})

    inventory_record_count = 0
    for filename in INVENTORY_FILES:
        records = _load(corpus_dir / filename)
        inventory_record_count += len(records)
        for error in validate_instances(records, inventory_schema):
            errors.append({"artifact": filename, **error})

    return {
        "record_type": "ibc_2018_json_schema_validation",
        "draft": "2020-12",
        "inventory_file_count": len(INVENTORY_FILES),
        "inventory_record_count": inventory_record_count,
        "error_count": len(errors),
        "errors": errors,
        "valid": not errors,
    }


def main() -> int:
    args = parse_args()
    report = validate_corpus_schemas(args.corpus_dir, args.schema_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
