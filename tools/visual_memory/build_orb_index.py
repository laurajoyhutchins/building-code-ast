from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def build(staging_objects: Path, output: Path) -> None:
    base = staging_objects.parent
    descriptors: list[np.ndarray] = []
    owners: list[int] = []
    orb = cv2.ORB_create(nfeatures=900, scaleFactor=1.2, nlevels=8, fastThreshold=12)
    for index, line in enumerate(staging_objects.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        image_path = Path(row["image_path"])
        if not image_path.is_absolute():
            image_path = base / image_path
        image = cv2.imread(str(image_path), 0)
        if image is None:
            raise ValueError(f"unable to read {image_path}")
        if image.shape[1] > 650:
            scale = 650 / image.shape[1]
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        _, found = orb.detectAndCompute(image, None)
        if found is None:
            continue
        descriptors.extend(found)
        owners.extend([index] * len(found))
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "orb_descriptors.npy", np.asarray(descriptors, dtype="uint8"))
    np.save(output / "orb_owners.npy", np.asarray(owners, dtype="int32"))
    (output / "orb_manifest.json").write_text(json.dumps({
        "schema": "engineering-visual-memory-orb/0.4.0",
        "descriptor_rows": len(descriptors),
        "source_images_included": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build ORB source-reidentification descriptors from private staged page images")
    ap.add_argument("--staging-objects", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args(argv)
    build(args.staging_objects, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
