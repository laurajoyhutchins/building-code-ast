"""Computed source-provenance audit command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .evidence.source_packages import load_source_package, source_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="building-code-source-audit", description="Compute source readiness from canonical provenance without storing status.")
    parser.add_argument("--package", action="append", required=True, help="canonical source-package.json; repeat for multiple publication lanes")
    parser.add_argument("--retrievable-artifact-id", action="append", default=[], help="exact artifact ID proven retrievable in the current environment; repeat as needed")
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    retrievable_ids = set(args.retrievable_artifact_id)
    packages: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for package_path in args.package:
        package = load_source_package(Path(package_path))
        audit = source_audit(package, retrievable_artifact_ids=retrievable_ids)
        packages.append({"package": package_path, "package_id": package.package_id, "publication_count": len(package.publications), "artifact_count": len(package.artifacts), "binding_count": len(package.bindings), "derivation_count": len(package.derivations)})
        rows.extend(item.to_dict() for item in audit)
    payload = {"type": "computed_source_audit", "status_authority": "computed_not_stored", "packages": packages, "records": rows}
    print(json.dumps(payload, sort_keys=True, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
