from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from PIL import Image

from tools.visual_memory.core import (
    context_text,
    multiscale_view_boxes,
    visual_cache_key,
    visual_object_from_mapping,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_runtime(runtime: Path):
    sys.path.insert(0, str(runtime))
    import clip_runner as cr
    return cr


def image_tensor(cr, image: Image.Image):
    transform = cr.Compose([
        cr.Resize(224, interpolation=cr.InterpolationMode.BICUBIC),
        cr.CenterCrop(224),
        lambda im: im.convert("RGB"),
        cr.ToTensor(),
        cr.Normalize(cr.IMAGE_MEAN, cr.IMAGE_STD),
    ])
    return transform(image).unsqueeze(0)


def load_staging_objects(path: Path):
    base = path.parent
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        image_path = Path(raw.pop("image_path"))
        if not image_path.is_absolute():
            image_path = base / image_path
        rows.append((visual_object_from_mapping(raw), raw, image_path))
    return rows


def _view_names(include_fine: bool) -> list[str]:
    return [box.name for box in multiscale_view_boxes(100, 100, include_fine=include_fine)]


def build(staging: Path, output: Path, runtime: Path, *, cache_dir: Path | None = None) -> dict:
    import torch

    cr = load_runtime(runtime)
    model = cr.load_model(runtime / "ViT-B-32.pt", verify=True)
    tokenizer = cr.SimpleTokenizer(runtime / "bpe_simple_vocab_16e6.txt.gz")
    records = load_staging_objects(staging)
    output.mkdir(parents=True, exist_ok=True)
    cache_dir = cache_dir or output.parent / f".{output.name}.cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    objects_out: list[dict] = []
    view_vectors: list[np.ndarray] = []
    view_owners: list[int] = []
    view_names: list[dict] = []
    context_vectors: list[np.ndarray] = []
    cache_hits = 0
    computed = 0

    for index, (obj, raw, image_path) in enumerate(records):
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        include_fine = bool(raw.get("include_fine", False))
        render_sha = sha256_file(image_path)
        packed = context_text(obj, max_words=60)
        cache_key = visual_cache_key(
            render_sha256=render_sha,
            model_sha256=cr.MODEL_EXPECTED_SHA256,
            include_fine=include_fine,
            context=packed,
        )
        cache_path = cache_dir / f"{cache_key}.npz"
        names = _view_names(include_fine)

        if cache_path.exists():
            cached = np.load(cache_path)
            vectors = np.asarray(cached["views"], dtype="float32")
            context = np.asarray(cached["context"], dtype="float32")
            if vectors.shape != (len(names), 512) or context.shape != (512,):
                raise ValueError(f"invalid visual-memory cache entry: {cache_path}")
            cache_hits += 1
        else:
            with Image.open(image_path) as source:
                source = source.convert("RGB")
                boxes = multiscale_view_boxes(source.width, source.height, include_fine=include_fine)
                batch = [
                    image_tensor(cr, source.crop((box.x0, box.y0, box.x1, box.y1)))
                    for box in boxes
                ]
                tensor = torch.cat(batch, dim=0)
                with torch.inference_mode():
                    vectors = cr.normalize_features(model.encode_image(tensor)).detach().cpu().numpy().astype("float32")

            with torch.inference_mode():
                encoded = tokenizer.tokenize([packed or obj.label or obj.occurrence_id])
                context = cr.normalize_features(model.encode_text(encoded)).detach().cpu().numpy().astype("float32")[0]
            np.savez_compressed(cache_path, views=vectors, context=context)
            computed += 1

        for name, vector in zip(names, vectors):
            view_vectors.append(vector)
            view_owners.append(index)
            view_names.append({"object_index": index, "view": name})
        context_vectors.append(context)

        clean = dict(raw)
        clean.pop("include_fine", None)
        clean.setdefault("corpus_id", obj.corpus_id)
        clean.setdefault("kind", obj.kind)
        clean.setdefault("occurrence_id", obj.occurrence_id)
        clean.setdefault("logical_visual_id", obj.logical_visual_id)
        clean.setdefault("label", obj.label)
        clean.setdefault("page", obj.page)
        clean.setdefault("source_sha256", obj.source_sha256)
        clean.setdefault("caption_text_quality", obj.caption_text_quality)
        clean["render_sha256"] = render_sha
        objects_out.append(clean)

    (output / "objects.jsonl").write_text(
        "".join(json.dumps(obj, sort_keys=True) + "\n" for obj in objects_out), encoding="utf-8"
    )
    (output / "view_names.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in view_names), encoding="utf-8"
    )
    np.save(output / "view_embeddings.npy", np.asarray(view_vectors, dtype="float32"))
    np.save(output / "view_owner.npy", np.asarray(view_owners, dtype="int32"))
    np.save(output / "text_embeddings.npy", np.asarray(context_vectors, dtype="float32"))
    manifest = {
        "schema": "engineering-visual-memory/0.4.0",
        "object_count": len(objects_out),
        "view_count": len(view_names),
        "embedding_dim": 512,
        "clip_model": cr.MODEL_NAME,
        "clip_model_sha256": cr.MODEL_EXPECTED_SHA256,
        "source_images_included": False,
        "source_pdfs_included": False,
        "cache_contract": "engineering-visual-memory-cache/0.4.0",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "objects": len(objects_out),
        "views": len(view_names),
        "cache_hits": cache_hits,
        "computed": computed,
        "cache_dir": str(cache_dir),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build a source-free visual-memory embedding index from private staged images"
    )
    ap.add_argument("--staging-objects", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--runtime", required=True, type=Path)
    ap.add_argument("--cache-dir", type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(build(
        args.staging_objects,
        args.output,
        args.runtime,
        cache_dir=args.cache_dir,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
