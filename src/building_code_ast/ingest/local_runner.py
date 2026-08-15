"""Publication-neutral mechanics for private local ingestion scripts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable


def prepare_output_dir(
    output_dir: Path,
    *,
    force: bool,
    generated_name_pattern: str,
) -> None:
    """Prepare an output directory without deleting unrecognized content."""

    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
        return

    children = tuple(output_dir.iterdir())
    if not children:
        return
    if not force:
        raise FileExistsError(
            f"output directory is not empty: {output_dir}; pass --force to replace it"
        )

    unexpected = [
        child.name
        for child in children
        if not child.is_file()
        or (
            child.name != "manifest.json"
            and re.fullmatch(generated_name_pattern, child.name) is None
        )
    ]
    if unexpected:
        raise FileExistsError(
            "output directory contains unexpected entries and will not be deleted: "
            + ", ".join(sorted(unexpected))
        )
    for child in children:
        child.unlink()


def source_digest(path: Path) -> tuple[str, int]:
    """Return the SHA-256 digest and byte size of a local source file."""

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def write_json(path: Path, payload: object) -> None:
    """Write deterministic UTF-8 JSON used by private ingestion outputs."""

    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_manifest(
    output_dir: Path,
    payload: dict[str, object],
    generated_paths: Iterable[Path],
) -> tuple[Path, ...]:
    """Write the common manifest location and return it before generated outputs."""

    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, payload)
    return (manifest_path, *generated_paths)


def warn_private_output(publication: str) -> None:
    """Emit the shared private-output boundary warning."""

    print(
        f"Warning: generated files may contain copyrighted {publication} text. "
        "Keep the output private and outside public Git.",
        file=sys.stderr,
    )
