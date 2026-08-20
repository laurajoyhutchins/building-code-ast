"""Computed source-provenance audit command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evidence.io import source_register_from_dict
from .evidence.source_objects import source_object_catalog_from_dict
from .evidence.source_packages import legacy_source_package, source_audit


def _read_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="building-code-source-audit",
        description="Compute source readiness from retained provenance authority without storing status.",
    )
    parser.add_argument("--catalog", required=True, help="legacy source-object catalog during v0.2 migration")
    parser.add_argument(
        "--register", action="append", required=True,
        help="source register to normalize and audit; repeat for multiple publication lanes",
    )
    parser.add_argument(
        "--retrievable-object-key", action="append", default=[],
        help="logical private object key proven retrievable in the current environment; repeat as needed",
    )
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = source_object_catalog_from_dict(_read_json(args.catalog))
    retrievable_keys = set(args.retrievable_object_key)
    packages: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for register_path in args.register:
        register = source_register_from_dict(_read_json(register_path))
        package = legacy_source_package(register, catalog)
        retrievable_ids = {
            artifact.artifact_id
            for artifact in package.artifacts
            if artifact.object_key in retrievable_keys
        }
        audit = source_audit(package, retrievable_artifact_ids=retrievable_ids)
        packages.append({
            "register": register_path,
            "publication_count": len(package.publications),
            "artifact_count": len(package.artifacts),
            "binding_count": len(package.bindings),
            "derivation_count": len(package.derivations),
        })
        rows.extend(item.to_dict() for item in audit)
    payload = {
        "type": "computed_source_audit",
        "status_authority": "computed_not_stored",
        "packages": packages,
        "records": rows,
    }
    print(json.dumps(payload, sort_keys=True, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
