#!/usr/bin/env python3
"""Build the strict, source-local NFPA 13 (2019) AST bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any

REPOSITORY = "laurajoyhutchins/building-code-ast"
ENGINE_PATH = "tools/extract_nfpa13_2019_ast.py"
WRAPPER_PATH = "tools/build_nfpa13_2019_bundle.py"


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pymupdf_version(engine: Any) -> str:
    fitz = getattr(engine, "fitz", None)
    if fitz is None:
        return "not-loaded"
    for name in ("__version__", "VersionBind", "version"):
        value = getattr(fitz, name, None)
        if value:
            return str(value)
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("nfpa13-2019-source-linked-ast.json")
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("nfpa13-2019-source-linked-ast-validation.md"),
    )
    parser.add_argument("--expected-sha256")
    parser.add_argument("--producer-commit", default=os.getenv("BUILDING_CODE_AST_COMMIT"))
    parser.add_argument("--overlays-dir", type=Path)
    parser.add_argument("--overlay-pages", default="22,181,182,323,489,513")
    args = parser.parse_args()

    if not args.producer_commit:
        parser.error(
            "--producer-commit is required so generated bundles retain exact parser provenance"
        )

    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    engine_path = root / ENGINE_PATH
    engine = _load_module(engine_path, "extract_nfpa13_2019_ast")
    from building_code_ast.nfpa13_bundle import (
        BUNDLE_SCHEMA,
        PRODUCER_SCHEMA,
        canonical_json_bytes,
        finalize_raw_nfpa13_bundle,
        sha256_bytes,
    )

    expected = args.expected_sha256
    if expected is None:
        expected = engine.EXPECTED_SOURCE_SHA256
    raw = engine.build_bundle(args.pdf, expected_sha256=expected or None)
    producer = {
        "schema": PRODUCER_SCHEMA,
        "repository": REPOSITORY,
        "commit_sha": args.producer_commit,
        "engine_path": ENGINE_PATH,
        "engine_sha256": _sha256(engine_path),
        "wrapper_path": WRAPPER_PATH,
        "wrapper_sha256": _sha256(Path(__file__)),
        "python_version": platform.python_version(),
        "pymupdf_version": _pymupdf_version(engine),
        "command_options": {
            "expected_sha256": expected,
            "overlay_pages": args.overlay_pages,
        },
    }
    bundle = finalize_raw_nfpa13_bundle(
        raw,
        producer=producer,
        engine_validator=engine.validate_bundle,
    )
    payload = canonical_json_bytes(bundle) + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)

    validation = bundle["validation"]
    statistics = bundle["statistics"]
    lines = [
        "# NFPA 13 (2019) Strict AST Bundle Validation",
        "",
        f"**Result:** {'PASS' if validation['passed'] else 'FAIL'}",
        f"**Bundle schema:** `{BUNDLE_SCHEMA}`",
        f"**Producer commit:** `{args.producer_commit}`",
        f"**Output SHA-256:** `{sha256_bytes(payload)}`",
        "",
        "## Contract proof",
        "",
    ]
    for key, value in sorted(validation["contract"].items()):
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.extend(["", "## Statistics", ""])
    for key, value in sorted(statistics.items()):
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.overlays_dir:
        engine.write_overlay_pages(
            args.pdf,
            bundle,
            args.overlays_dir,
            engine._parse_pages(args.overlay_pages),
        )

    print(json.dumps(bundle["statistics"], indent=2, sort_keys=True))
    print(args.output)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
