from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.visual_memory.core import verify_private_package


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected_sha256: str | None = None) -> dict:
    path = Path(path)
    archive_sha = sha256_file(path) if path.is_file() else None
    if expected_sha256 and archive_sha != expected_sha256:
        return {"ok": False, "archive_sha256": archive_sha, "errors": ["archive SHA-256 mismatch"]}
    if path.is_dir():
        report = verify_private_package(path)
        return {"ok": report.ok, "archive_sha256": archive_sha, "forbidden_files": report.forbidden_files, "errors": report.errors}
    if not zipfile.is_zipfile(path):
        return {"ok": False, "archive_sha256": archive_sha, "errors": ["path is neither a directory nor a ZIP archive"]}
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                return {"ok": False, "archive_sha256": archive_sha, "errors": [f"ZIP integrity failure at {bad}"]}
            zf.extractall(td)
        roots = [item for item in Path(td).iterdir() if item.is_dir()]
        root = roots[0] if len(roots) == 1 and (roots[0] / "manifest.json").exists() else Path(td)
        report = verify_private_package(root)
        return {"ok": report.ok, "archive_sha256": archive_sha, "forbidden_files": report.forbidden_files, "errors": report.errors}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify an Engineering Visual Memory private package")
    ap.add_argument("path", type=Path)
    ap.add_argument("--expected-sha256")
    args = ap.parse_args(argv)
    report = verify(args.path, args.expected_sha256)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
